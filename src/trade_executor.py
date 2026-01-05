"""
Trade Executor - Executes trades based on parsed signals
Handles buy and sell orders with position management
"""

import logging
import os
from typing import Optional
from datetime import datetime

from src.hebrew_parser import TradeSignal
from src.ibkr_client import IBKRClient
from src.position_manager import PositionManager, Position

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    Executes trades based on signals from Twitter
    """

    def __init__(self,
                 ibkr_client: IBKRClient,
                 position_manager: PositionManager,
                 position_size_multiplier: float = 0.10,
                 enable_trading: bool = False,
                 max_position_size: float = 10000):
        """
        Initialize trade executor

        Args:
            ibkr_client: IBKR client for order execution
            position_manager: Position manager for tracking positions
            position_size_multiplier: Multiplier for position size (0.10 = 10%)
            enable_trading: If False, runs in dry-run mode
            max_position_size: Maximum position size in USD
        """
        self.ibkr = ibkr_client
        self.position_manager = position_manager
        self.position_size_multiplier = position_size_multiplier
        self.enable_trading = enable_trading
        self.max_position_size = max_position_size

        logger.info(f"Initialized trade executor (multiplier={position_size_multiplier}, "
                    f"trading={'ENABLED' if enable_trading else 'DRY-RUN'})")

    async def execute_signal(self, signal: TradeSignal, tweet_url: str = "") -> bool:
        """
        Execute a trading signal

        Args:
            signal: Parsed trade signal
            tweet_url: URL of the tweet (for logging)

        Returns:
            True if execution was successful
        """
        logger.info(f"{'='*80}")
        logger.info(f"Executing signal: {signal}")
        logger.info(f"Tweet: {tweet_url}")
        logger.info(f"Raw text: {signal.raw_text}")
        logger.info(f"{'='*80}")

        try:
            if signal.action == 'BUY':
                return await self._execute_buy(signal)
            elif signal.action == 'SELL':
                return await self._execute_sell(signal)
            else:
                logger.error(f"Unknown action: {signal.action}")
                return False

        except Exception as e:
            logger.error(f"Error executing signal: {e}", exc_info=True)
            return False

    async def _execute_buy(self, signal: TradeSignal) -> bool:
        """Execute a buy signal"""

        # Validate signal has required information
        if not all([signal.ticker, signal.strike, signal.option_type, signal.expiry]):
            logger.error("Buy signal missing required information")
            return False

        # Calculate quantity to buy (10% of mentioned quantity)
        original_quantity = signal.quantity if signal.quantity else 10
        quantity_to_buy = max(1, int(original_quantity * self.position_size_multiplier))

        logger.info(f"Original quantity: {original_quantity}, buying: {quantity_to_buy} "
                    f"({self.position_size_multiplier*100}%)")

        # Create option contract
        contract = self.ibkr.create_option_contract(
            signal.ticker,
            signal.strike,
            signal.option_type,
            signal.expiry
        )

        if not contract:
            logger.error("Failed to create option contract")
            return False

        # Qualify contract
        qualified_contract = await self.ibkr.get_contract_details(contract)
        if not qualified_contract:
            logger.error("Failed to qualify contract")
            return False

        # Get market price
        market_price = await self.ibkr.get_market_price(qualified_contract)
        if not market_price:
            logger.error("Failed to get market price")
            return False

        # Check position size limit
        position_value = quantity_to_buy * market_price * 100  # Options multiplier
        if position_value > self.max_position_size:
            logger.warning(f"Position value ${position_value:.2f} exceeds max ${self.max_position_size:.2f}")
            quantity_to_buy = int(self.max_position_size / (market_price * 100))
            logger.info(f"Adjusted quantity to {quantity_to_buy}")

            if quantity_to_buy < 1:
                logger.error("Adjusted quantity is less than 1, skipping trade")
                return False

        logger.info(f"Buying {quantity_to_buy} x {signal.ticker} {signal.strike}{signal.option_type[0]} "
                    f"at market price ~${market_price:.2f}")

        # Execute trade if enabled
        if self.enable_trading:
            order = await self.ibkr.place_market_order(qualified_contract, quantity_to_buy, 'BUY')

            if not order:
                logger.error("Failed to place buy order")
                return False

            logger.info(f"✓ Buy order placed successfully (Order ID: {order.orderId})")

            # Add to position manager
            self.position_manager.add_position(
                ticker=signal.ticker,
                strike=signal.strike,
                option_type=signal.option_type,
                expiry=signal.expiry,
                quantity=quantity_to_buy,
                entry_price=market_price
            )

            logger.info("✓ Position added to manager")

        else:
            logger.info("⚠ DRY-RUN MODE: Would buy but trading is disabled")
            logger.info(f"   Order: BUY {quantity_to_buy} x {signal.ticker} "
                        f"{signal.strike}{signal.option_type[0]} @ ~${market_price:.2f}")
            logger.info(f"   Value: ~${position_value:.2f}")

        return True

    async def _execute_sell(self, signal: TradeSignal) -> bool:
        """Execute a sell signal"""

        # Find position to sell
        if signal.ticker:
            # Ticker specified, find that specific position
            if signal.strike and signal.option_type and signal.expiry:
                # Full contract details provided
                position = self.position_manager.find_position(
                    signal.ticker,
                    signal.strike,
                    signal.option_type,
                    signal.expiry
                )
            else:
                # Only ticker provided, find most recent position
                position = self.position_manager.find_position_by_ticker(signal.ticker)
        else:
            # No ticker specified, sell from most recent position
            all_positions = self.position_manager.get_all_positions()
            if not all_positions:
                logger.error("No positions to sell")
                return False
            position = max(all_positions, key=lambda p: p.entry_time)

        if not position:
            logger.error(f"No position found to sell for {signal.ticker or 'any ticker'}")
            return False

        # Calculate quantity to sell
        quantity_to_sell = self.position_manager.reduce_position(position, signal.position_fraction)

        if quantity_to_sell <= 0:
            logger.error("No quantity to sell")
            return False

        logger.info(f"Selling {signal.position_fraction*100}% of position: {quantity_to_sell} contracts")
        logger.info(f"Position: {position}")

        # Create contract
        contract = self.ibkr.create_option_contract(
            position.ticker,
            position.strike,
            position.option_type,
            position.expiry
        )

        if not contract:
            logger.error("Failed to create option contract")
            # Restore position
            position.quantity += quantity_to_sell
            return False

        # Qualify contract
        qualified_contract = await self.ibkr.get_contract_details(contract)
        if not qualified_contract:
            logger.error("Failed to qualify contract")
            position.quantity += quantity_to_sell
            return False

        # Get market price
        market_price = await self.ibkr.get_market_price(qualified_contract)
        if not market_price:
            logger.warning("Failed to get market price, continuing anyway")
            market_price = 0.0

        # Calculate P&L if we have price
        if market_price > 0:
            entry_value = quantity_to_sell * position.entry_price * 100
            exit_value = quantity_to_sell * market_price * 100
            pnl = exit_value - entry_value
            pnl_percent = (pnl / entry_value) * 100 if entry_value > 0 else 0

            logger.info(f"P&L: ${pnl:.2f} ({pnl_percent:+.2f}%)")

        # Execute trade if enabled
        if self.enable_trading:
            order = await self.ibkr.place_market_order(qualified_contract, quantity_to_sell, 'SELL')

            if not order:
                logger.error("Failed to place sell order")
                # Restore position
                position.quantity += quantity_to_sell
                return False

            logger.info(f"✓ Sell order placed successfully (Order ID: {order.orderId})")
            logger.info("✓ Position updated in manager")

        else:
            logger.info("⚠ DRY-RUN MODE: Would sell but trading is disabled")
            logger.info(f"   Order: SELL {quantity_to_sell} x {position.ticker} "
                        f"{position.strike}{position.option_type[0]} @ ~${market_price:.2f}")
            if market_price > 0:
                logger.info(f"   P&L: ${pnl:.2f} ({pnl_percent:+.2f}%)")
            # Restore position since this is dry-run
            position.quantity += quantity_to_sell

        return True

    def print_positions_summary(self):
        """Print summary of current positions"""
        self.position_manager.print_summary()


# Test function
async def test_executor():
    """Test the trade executor"""
    from src.hebrew_parser import HebrewParser

    # Initialize components
    ibkr = IBKRClient(host='127.0.0.1', port=7497)
    position_manager = PositionManager('data/test_positions.json')
    executor = TradeExecutor(
        ibkr_client=ibkr,
        position_manager=position_manager,
        enable_trading=False  # Dry-run mode
    )

    # Connect to IBKR
    connected = await ibkr.connect()
    if not connected:
        print("Failed to connect to IBKR")
        return

    # Parse and execute test signals
    parser = HebrewParser()

    # Test buy signal
    buy_text = "קניתי SPY 450C 12/31/24 10 חוזים במחיר $4.50"
    buy_signal = parser.parse_tweet(buy_text)
    if buy_signal:
        await executor.execute_signal(buy_signal, "https://twitter.com/test/123")

    # Print positions
    executor.print_positions_summary()

    # Test sell signal
    sell_text = "מכרתי רבע מ-SPY"
    sell_signal = parser.parse_tweet(sell_text)
    if sell_signal:
        await executor.execute_signal(sell_signal, "https://twitter.com/test/124")

    # Print final positions
    executor.print_positions_summary()

    # Disconnect
    ibkr.disconnect()


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(test_executor())
