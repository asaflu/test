"""
IBKR Client - Connects to Interactive Brokers TWS and executes trades
Uses ib_insync library for async communication
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from ib_insync import IB, Stock, Option, MarketOrder, Order, Contract, PortfolioItem
import asyncio

logger = logging.getLogger(__name__)


class IBKRClient:
    """
    Interactive Brokers TWS client for trade execution
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 7497, client_id: int = 1):
        """
        Initialize IBKR client

        Args:
            host: TWS/Gateway host (default: 127.0.0.1)
            port: TWS/Gateway port (7497=TWS paper, 7496=TWS live, 4002=Gateway paper, 4001=Gateway live)
            client_id: Client ID for connection
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()
        self.connected = False

        logger.info(f"Initialized IBKR client (host={host}, port={port}, client_id={client_id})")

    async def connect(self) -> bool:
        """
        Connect to TWS/Gateway

        Returns:
            True if connected successfully
        """
        try:
            await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
            self.connected = True
            logger.info(f"Connected to IBKR TWS at {self.host}:{self.port}")

            # Get account info
            accounts = self.ib.managedAccounts()
            logger.info(f"Connected accounts: {accounts}")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from TWS/Gateway"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR TWS")

    def create_option_contract(self, ticker: str, strike: float, option_type: str,
                                expiry: str) -> Optional[Contract]:
        """
        Create an option contract

        Args:
            ticker: Stock ticker (e.g., 'SPY')
            strike: Strike price (e.g., 450.0)
            option_type: 'CALL' or 'PUT'
            expiry: Expiry date in format MM/DD or MM/DD/YY or MM/DD/YYYY

        Returns:
            Option contract or None if invalid
        """
        try:
            # Parse expiry date
            expiry_date = self._parse_expiry(expiry)
            if not expiry_date:
                logger.error(f"Invalid expiry format: {expiry}")
                return None

            # Create option contract
            option = Option(
                symbol=ticker,
                lastTradeDateOrContractMonth=expiry_date,
                strike=strike,
                right=option_type[0],  # 'C' or 'P'
                exchange='SMART',
                currency='USD'
            )

            logger.info(f"Created option contract: {option}")
            return option

        except Exception as e:
            logger.error(f"Error creating option contract: {e}")
            return None

    def _parse_expiry(self, expiry: str) -> Optional[str]:
        """
        Parse expiry date string to YYYYMMDD format

        Args:
            expiry: Date string like "12/31", "12/31/24", or "12/31/2024"

        Returns:
            Date in YYYYMMDD format or None
        """
        try:
            current_year = datetime.now().year

            # Parse different formats
            if expiry.count('/') == 1:
                # Format: MM/DD
                month, day = expiry.split('/')
                year = current_year
                # If the date has passed this year, assume next year
                test_date = datetime(year, int(month), int(day))
                if test_date < datetime.now():
                    year += 1

            elif expiry.count('/') == 2:
                # Format: MM/DD/YY or MM/DD/YYYY
                month, day, year = expiry.split('/')
                year = int(year)
                if year < 100:
                    # 2-digit year
                    year += 2000

            else:
                return None

            # Format as YYYYMMDD
            date_str = f"{year}{int(month):02d}{int(day):02d}"
            logger.debug(f"Parsed expiry '{expiry}' to '{date_str}'")
            return date_str

        except Exception as e:
            logger.error(f"Error parsing expiry date '{expiry}': {e}")
            return None

    async def get_contract_details(self, contract: Contract) -> Optional[Contract]:
        """
        Qualify and get details for a contract

        Args:
            contract: Contract to qualify

        Returns:
            Qualified contract or None
        """
        try:
            qualified_contracts = await self.ib.qualifyContractsAsync(contract)

            if not qualified_contracts:
                logger.error(f"No contracts found for {contract}")
                return None

            if len(qualified_contracts) > 1:
                logger.warning(f"Multiple contracts found, using first: {qualified_contracts[0]}")

            qualified = qualified_contracts[0]
            logger.info(f"Qualified contract: {qualified}")
            return qualified

        except Exception as e:
            logger.error(f"Error qualifying contract: {e}")
            return None

    async def get_market_price(self, contract: Contract) -> Optional[float]:
        """
        Get current market price for a contract

        Args:
            contract: Contract to get price for

        Returns:
            Current market price or None
        """
        try:
            # Request market data
            ticker = self.ib.reqTickers(contract)[0]

            # Wait a moment for data to arrive
            await asyncio.sleep(1)

            # Get bid/ask midpoint or last price
            if ticker.bid and ticker.ask:
                price = (ticker.bid + ticker.ask) / 2
            elif ticker.last:
                price = ticker.last
            elif ticker.close:
                price = ticker.close
            else:
                logger.warning(f"No price data available for {contract}")
                return None

            logger.info(f"Market price for {contract.symbol}: ${price:.2f}")
            return price

        except Exception as e:
            logger.error(f"Error getting market price: {e}")
            return None

    async def place_market_order(self, contract: Contract, quantity: int,
                                  action: str = 'BUY') -> Optional[Order]:
        """
        Place a market order

        Args:
            contract: Contract to trade
            quantity: Number of contracts
            action: 'BUY' or 'SELL'

        Returns:
            Order object or None if failed
        """
        try:
            if not self.connected:
                logger.error("Not connected to IBKR")
                return None

            # Create market order
            order = MarketOrder(action, quantity)

            # Place order
            trade = self.ib.placeOrder(contract, order)

            logger.info(f"Placed {action} market order: {quantity} x {contract.symbol}")
            logger.info(f"Order ID: {trade.order.orderId}")

            # Wait for order to be submitted
            await asyncio.sleep(2)

            # Check order status
            if trade.orderStatus.status in ['Submitted', 'Filled', 'PreSubmitted']:
                logger.info(f"Order status: {trade.orderStatus.status}")
                return trade.order
            else:
                logger.error(f"Order failed with status: {trade.orderStatus.status}")
                return None

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    async def get_positions(self) -> List[PortfolioItem]:
        """
        Get current positions

        Returns:
            List of portfolio items
        """
        try:
            if not self.connected:
                logger.error("Not connected to IBKR")
                return []

            positions = self.ib.portfolio()
            logger.info(f"Current positions: {len(positions)}")

            for pos in positions:
                logger.debug(f"Position: {pos.contract.symbol} - {pos.position} @ ${pos.averageCost:.2f}")

            return positions

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    async def get_position_for_contract(self, contract: Contract) -> Optional[PortfolioItem]:
        """
        Get position for a specific contract

        Args:
            contract: Contract to find position for

        Returns:
            PortfolioItem or None
        """
        try:
            positions = await self.get_positions()

            for pos in positions:
                if self._contracts_match(pos.contract, contract):
                    logger.info(f"Found position: {pos.position} x {pos.contract.symbol}")
                    return pos

            logger.info(f"No position found for {contract.symbol}")
            return None

        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None

    def _contracts_match(self, c1: Contract, c2: Contract) -> bool:
        """Check if two contracts are the same"""
        if hasattr(c1, 'symbol') and hasattr(c2, 'symbol'):
            if c1.symbol != c2.symbol:
                return False

        if hasattr(c1, 'strike') and hasattr(c2, 'strike'):
            if abs(c1.strike - c2.strike) > 0.01:
                return False

        if hasattr(c1, 'right') and hasattr(c2, 'right'):
            if c1.right != c2.right:
                return False

        if hasattr(c1, 'lastTradeDateOrContractMonth') and hasattr(c2, 'lastTradeDateOrContractMonth'):
            if c1.lastTradeDateOrContractMonth != c2.lastTradeDateOrContractMonth:
                return False

        return True

    async def get_account_summary(self) -> Dict:
        """
        Get account summary

        Returns:
            Dict with account information
        """
        try:
            if not self.connected:
                logger.error("Not connected to IBKR")
                return {}

            summary = {}
            account_values = self.ib.accountValues()

            for value in account_values:
                summary[value.tag] = value.value

            logger.info(f"Account summary retrieved: {len(summary)} items")
            return summary

        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {}


# Test function
async def test_ibkr_client():
    """Test the IBKR client"""

    client = IBKRClient(host='127.0.0.1', port=7497)

    # Connect
    connected = await client.connect()
    if not connected:
        print("Failed to connect to IBKR")
        return

    # Get account summary
    summary = await client.get_account_summary()
    print(f"\nAccount Summary:")
    for key, value in list(summary.items())[:10]:
        print(f"  {key}: {value}")

    # Get positions
    positions = await client.get_positions()
    print(f"\nCurrent Positions: {len(positions)}")
    for pos in positions:
        print(f"  {pos.contract.symbol}: {pos.position} @ ${pos.averageCost:.2f}")

    # Test creating an option contract
    contract = client.create_option_contract('SPY', 450.0, 'CALL', '12/31/2024')
    if contract:
        qualified = await client.get_contract_details(contract)
        if qualified:
            price = await client.get_market_price(qualified)
            print(f"\nSPY 450C price: ${price:.2f}")

    # Disconnect
    client.disconnect()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(test_ibkr_client())
