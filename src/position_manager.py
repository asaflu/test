"""
Position Manager - Tracks open positions and manages position sizing
"""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents an open trading position"""
    ticker: str
    strike: float
    option_type: str
    expiry: str
    quantity: int
    entry_price: float
    entry_time: datetime = field(default_factory=datetime.now)
    original_quantity: int = 0  # Track original quantity for partial sells

    def __post_init__(self):
        if self.original_quantity == 0:
            self.original_quantity = self.quantity

    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'ticker': self.ticker,
            'strike': self.strike,
            'option_type': self.option_type,
            'expiry': self.expiry,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time.isoformat(),
            'original_quantity': self.original_quantity
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create Position from dictionary"""
        data['entry_time'] = datetime.fromisoformat(data['entry_time'])
        return cls(**data)

    def __repr__(self):
        return (f"Position({self.ticker} {self.strike}{self.option_type[0]} "
                f"exp:{self.expiry} qty:{self.quantity}/{self.original_quantity} "
                f"@ ${self.entry_price:.2f})")


class PositionManager:
    """
    Manages trading positions and handles position sizing
    """

    def __init__(self, position_file: str = 'data/positions.json'):
        """
        Initialize position manager

        Args:
            position_file: File path to store positions
        """
        self.position_file = position_file
        self.positions: List[Position] = []

        # Create data directory if needed
        os.makedirs(os.path.dirname(position_file) if os.path.dirname(position_file) else '.', exist_ok=True)

        # Load existing positions
        self.load_positions()

        logger.info(f"Initialized position manager with {len(self.positions)} positions")

    def add_position(self, ticker: str, strike: float, option_type: str,
                     expiry: str, quantity: int, entry_price: float) -> Position:
        """
        Add a new position

        Args:
            ticker: Stock ticker
            strike: Strike price
            option_type: 'CALL' or 'PUT'
            expiry: Expiry date
            quantity: Number of contracts
            entry_price: Entry price per contract

        Returns:
            Created Position object
        """
        position = Position(
            ticker=ticker,
            strike=strike,
            option_type=option_type,
            expiry=expiry,
            quantity=quantity,
            entry_price=entry_price,
            entry_time=datetime.now()
        )

        # Check if we already have this position (same contract)
        existing = self.find_position(ticker, strike, option_type, expiry)
        if existing:
            # Add to existing position
            total_cost = (existing.entry_price * existing.quantity) + (entry_price * quantity)
            existing.quantity += quantity
            existing.original_quantity += quantity
            existing.entry_price = total_cost / existing.quantity
            logger.info(f"Added to existing position: {existing}")
            position = existing
        else:
            # New position
            self.positions.append(position)
            logger.info(f"Created new position: {position}")

        self.save_positions()
        return position

    def find_position(self, ticker: str, strike: float, option_type: str,
                      expiry: str) -> Optional[Position]:
        """
        Find a position by contract details

        Args:
            ticker: Stock ticker
            strike: Strike price
            option_type: 'CALL' or 'PUT'
            expiry: Expiry date

        Returns:
            Position or None
        """
        for pos in self.positions:
            if (pos.ticker == ticker and
                abs(pos.strike - strike) < 0.01 and
                pos.option_type == option_type and
                pos.expiry == expiry):
                return pos

        return None

    def find_position_by_ticker(self, ticker: str) -> Optional[Position]:
        """
        Find the most recent position for a ticker (for sell signals without full details)

        Args:
            ticker: Stock ticker

        Returns:
            Position or None
        """
        # Find all positions for this ticker
        ticker_positions = [p for p in self.positions if p.ticker == ticker and p.quantity > 0]

        if not ticker_positions:
            return None

        # Return the most recent one
        return max(ticker_positions, key=lambda p: p.entry_time)

    def reduce_position(self, position: Position, fraction: float) -> int:
        """
        Reduce a position by a fraction (for partial sells)

        Args:
            position: Position to reduce
            fraction: Fraction to sell (0.25 for quarter, 0.5 for half, etc.)

        Returns:
            Quantity sold
        """
        if position not in self.positions:
            logger.error(f"Position not found: {position}")
            return 0

        quantity_to_sell = int(position.quantity * fraction)

        if quantity_to_sell <= 0:
            logger.warning(f"Calculated quantity to sell is 0 (qty={position.quantity}, fraction={fraction})")
            return 0

        if quantity_to_sell > position.quantity:
            logger.warning(f"Trying to sell more than available, selling all")
            quantity_to_sell = position.quantity

        position.quantity -= quantity_to_sell
        logger.info(f"Reduced position by {fraction*100}%: sold {quantity_to_sell}, remaining {position.quantity}")

        # Remove position if fully closed
        if position.quantity <= 0:
            self.positions.remove(position)
            logger.info(f"Position fully closed: {position.ticker}")

        self.save_positions()
        return quantity_to_sell

    def close_position(self, position: Position) -> int:
        """
        Close a position completely

        Args:
            position: Position to close

        Returns:
            Quantity closed
        """
        if position not in self.positions:
            logger.error(f"Position not found: {position}")
            return 0

        quantity = position.quantity
        self.positions.remove(position)
        logger.info(f"Closed position: {position}")

        self.save_positions()
        return quantity

    def get_all_positions(self) -> List[Position]:
        """Get all open positions"""
        return [p for p in self.positions if p.quantity > 0]

    def get_position_value(self, position: Position, current_price: float) -> float:
        """
        Calculate current value of a position

        Args:
            position: Position to value
            current_price: Current market price

        Returns:
            Current value in USD
        """
        return position.quantity * current_price * 100  # Options are x100 multiplier

    def get_position_pnl(self, position: Position, current_price: float) -> float:
        """
        Calculate P&L for a position

        Args:
            position: Position to calculate P&L for
            current_price: Current market price

        Returns:
            P&L in USD
        """
        entry_value = position.quantity * position.entry_price * 100
        current_value = position.quantity * current_price * 100
        return current_value - entry_value

    def save_positions(self):
        """Save positions to file"""
        try:
            data = {
                'positions': [p.to_dict() for p in self.positions],
                'last_updated': datetime.now().isoformat()
            }

            with open(self.position_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self.positions)} positions to {self.position_file}")

        except Exception as e:
            logger.error(f"Error saving positions: {e}")

    def load_positions(self):
        """Load positions from file"""
        try:
            if not os.path.exists(self.position_file):
                logger.info("No existing positions file found")
                return

            with open(self.position_file, 'r') as f:
                data = json.load(f)

            self.positions = [Position.from_dict(p) for p in data['positions']]
            logger.info(f"Loaded {len(self.positions)} positions from {self.position_file}")

            # Log positions
            for pos in self.positions:
                logger.debug(f"Loaded: {pos}")

        except Exception as e:
            logger.error(f"Error loading positions: {e}")
            self.positions = []

    def print_summary(self):
        """Print summary of all positions"""
        print(f"\n{'='*80}")
        print(f"Position Summary - {len(self.positions)} open positions")
        print(f"{'='*80}")

        for i, pos in enumerate(self.positions, 1):
            print(f"{i}. {pos}")

        print(f"{'='*80}\n")


# Test function
def test_position_manager():
    """Test the position manager"""

    # Create manager
    manager = PositionManager('data/test_positions.json')

    # Add some positions
    pos1 = manager.add_position('SPY', 450.0, 'CALL', '12/31', 10, 4.50)
    pos2 = manager.add_position('QQQ', 380.0, 'PUT', '1/15', 5, 3.20)

    # Print summary
    manager.print_summary()

    # Find position
    found = manager.find_position('SPY', 450.0, 'CALL', '12/31')
    print(f"\nFound position: {found}")

    # Reduce position by quarter
    sold = manager.reduce_position(pos1, 0.25)
    print(f"\nSold {sold} contracts")

    # Print summary again
    manager.print_summary()

    # Close position
    closed = manager.close_position(pos2)
    print(f"\nClosed {closed} contracts")

    # Final summary
    manager.print_summary()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    test_position_manager()
