"""
Hebrew Parser - Extracts trading signals from Hebrew tweets
Understands @ultrawavetrader's trading language
"""

import re
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime
import yaml

logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    """Represents a parsed trading signal"""
    action: str  # 'BUY' or 'SELL'
    ticker: Optional[str] = None
    strike: Optional[float] = None
    option_type: Optional[str] = None  # 'CALL' or 'PUT'
    expiry: Optional[str] = None
    position_fraction: float = 1.0  # What fraction to trade (0.25 for quarter, etc.)
    quantity: Optional[int] = None
    price: Optional[float] = None
    raw_text: str = ""
    confidence: float = 0.0  # 0-1 confidence score

    def __repr__(self):
        if self.action == 'BUY':
            return (f"TradeSignal(BUY {self.ticker} {self.strike}{self.option_type[0]} "
                    f"exp:{self.expiry} qty:{self.quantity} @ {self.price})")
        else:
            return (f"TradeSignal(SELL {self.position_fraction*100}% of {self.ticker or 'position'})")


class HebrewParser:
    """
    Parses Hebrew tweets to extract trading signals
    """

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize parser with configuration"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.buy_keywords = self.config['hebrew_keywords']['buy_signals']
        self.sell_keywords = self.config['hebrew_keywords']['sell_signals']
        self.position_fractions = self.config['hebrew_keywords']['position_fractions']

        logger.info("Initialized Hebrew parser")

    def extract_position_fraction(self, text: str) -> float:
        """
        Extract position fraction from Hebrew text

        Args:
            text: Hebrew text containing position size

        Returns:
            Fraction (0.25 for רבע/quarter, 0.5 for חצי/half, etc.)
        """
        text_lower = text.lower()

        # Check for exact keyword matches
        for keyword, fraction in self.position_fractions.items():
            if keyword in text_lower:
                logger.debug(f"Found position fraction: {keyword} = {fraction}")
                return fraction

        # Check for percentage patterns
        percent_match = re.search(r'(\d+)%', text)
        if percent_match:
            percent = float(percent_match.group(1))
            fraction = percent / 100.0
            logger.debug(f"Found percentage: {percent}% = {fraction}")
            return fraction

        # Default to full position
        return 1.0

    def extract_ticker(self, text: str) -> Optional[str]:
        """
        Extract stock ticker from text
        Looks for uppercase letter sequences like SPY, QQQ, TSLA, etc.

        Args:
            text: Text containing potential ticker

        Returns:
            Ticker symbol or None
        """
        # Match uppercase tickers (2-5 letters)
        ticker_match = re.search(r'\b([A-Z]{1,5})\b', text)
        if ticker_match:
            ticker = ticker_match.group(1)
            # Filter out common non-ticker words
            if ticker not in ['I', 'A', 'C', 'P', 'AM', 'PM']:
                logger.debug(f"Found ticker: {ticker}")
                return ticker

        return None

    def extract_option_details(self, text: str) -> Dict:
        """
        Extract option contract details from text

        Patterns supported:
        - SPY 450C 12/31
        - SPY 450 CALL 12/31/24
        - TSLA 200P 1/15
        - QQQ 380 PUT 12/29

        Args:
            text: Text containing option details

        Returns:
            Dict with ticker, strike, option_type, expiry
        """
        details = {
            'ticker': None,
            'strike': None,
            'option_type': None,
            'expiry': None
        }

        # Pattern 1: SPY 450C 12/31
        pattern1 = r'([A-Z]{1,5})\s+(\d+(?:\.\d+)?)\s*([CP])\s+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)'
        match = re.search(pattern1, text, re.IGNORECASE)

        if match:
            details['ticker'] = match.group(1).upper()
            details['strike'] = float(match.group(2))
            option_letter = match.group(3).upper()
            details['option_type'] = 'CALL' if option_letter == 'C' else 'PUT'
            details['expiry'] = match.group(4)
            logger.debug(f"Extracted option details (pattern 1): {details}")
            return details

        # Pattern 2: SPY 450 CALL 12/31
        pattern2 = r'([A-Z]{1,5})\s+(\d+(?:\.\d+)?)\s+(CALL|PUT|קול|פוט)\s+(\d{1,2}/\d{1,2}(?:/\d{2,4})?)'
        match = re.search(pattern2, text, re.IGNORECASE)

        if match:
            details['ticker'] = match.group(1).upper()
            details['strike'] = float(match.group(2))
            option_word = match.group(3).upper()
            if option_word in ['CALL', 'קול']:
                details['option_type'] = 'CALL'
            else:
                details['option_type'] = 'PUT'
            details['expiry'] = match.group(4)
            logger.debug(f"Extracted option details (pattern 2): {details}")
            return details

        # Pattern 3: Just ticker and strike (without explicit call/put)
        pattern3 = r'([A-Z]{1,5})\s+(\d+(?:\.\d+)?)'
        match = re.search(pattern3, text)

        if match:
            details['ticker'] = match.group(1).upper()
            details['strike'] = float(match.group(2))
            # Try to infer call/put from context
            if 'קול' in text.lower() or 'call' in text.lower():
                details['option_type'] = 'CALL'
            elif 'פוט' in text.lower() or 'put' in text.lower():
                details['option_type'] = 'PUT'
            logger.debug(f"Extracted partial option details: {details}")
            return details

        return details

    def extract_quantity(self, text: str) -> Optional[int]:
        """
        Extract quantity from text

        Args:
            text: Text containing quantity

        Returns:
            Quantity as integer or None
        """
        # Look for patterns like "10 חוזים", "5 contracts", "x10", etc.
        patterns = [
            r'(\d+)\s*(?:חוזים|חוזה|contracts?)',
            r'[xX](\d+)',
            r'כמות[:\s]*(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                qty = int(match.group(1))
                logger.debug(f"Found quantity: {qty}")
                return qty

        return None

    def extract_price(self, text: str) -> Optional[float]:
        """
        Extract price from text

        Args:
            text: Text containing price

        Returns:
            Price as float or None
        """
        # Look for patterns like "$4.50", "4.5$", "במחיר 4.50", etc.
        patterns = [
            r'\$(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*\$',
            r'(?:במחיר|מחיר|price)[:\s]*(\d+(?:\.\d+)?)',
            r'@\s*(\d+(?:\.\d+)?)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                price = float(match.group(1))
                logger.debug(f"Found price: ${price}")
                return price

        return None

    def is_buy_signal(self, text: str) -> bool:
        """Check if text contains buy signal keywords"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.buy_keywords)

    def is_sell_signal(self, text: str) -> bool:
        """Check if text contains sell signal keywords"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.sell_keywords)

    def parse_tweet(self, text: str) -> Optional[TradeSignal]:
        """
        Parse a tweet and extract trading signal

        Args:
            text: Tweet text in Hebrew/English

        Returns:
            TradeSignal object or None if no signal found
        """
        logger.info(f"Parsing tweet: {text}")

        # Determine if this is a buy or sell signal
        is_buy = self.is_buy_signal(text)
        is_sell = self.is_sell_signal(text)

        if not is_buy and not is_sell:
            logger.info("No buy/sell signal found in tweet")
            return None

        signal = TradeSignal(raw_text=text)

        if is_buy:
            signal.action = 'BUY'

            # Extract option details
            option_details = self.extract_option_details(text)
            signal.ticker = option_details['ticker']
            signal.strike = option_details['strike']
            signal.option_type = option_details['option_type']
            signal.expiry = option_details['expiry']

            # Extract quantity and price
            signal.quantity = self.extract_quantity(text)
            signal.price = self.extract_price(text)

            # Calculate confidence based on how much info we extracted
            confidence = 0.5  # Base confidence
            if signal.ticker:
                confidence += 0.1
            if signal.strike:
                confidence += 0.1
            if signal.option_type:
                confidence += 0.1
            if signal.expiry:
                confidence += 0.1
            if signal.quantity:
                confidence += 0.05
            if signal.price:
                confidence += 0.05

            signal.confidence = min(confidence, 1.0)

            # Require at least ticker and strike for a valid buy signal
            if not signal.ticker or not signal.strike:
                logger.warning("Buy signal missing critical information (ticker or strike)")
                return None

        elif is_sell:
            signal.action = 'SELL'

            # Extract position fraction
            signal.position_fraction = self.extract_position_fraction(text)

            # Try to extract ticker (might be selling specific position)
            signal.ticker = self.extract_ticker(text)

            # Calculate confidence
            signal.confidence = 0.8 if signal.ticker else 0.6

        logger.info(f"Parsed signal: {signal}")
        return signal


# Test function
def test_parser():
    """Test the Hebrew parser with sample tweets"""

    parser = HebrewParser()

    test_tweets = [
        "קניתי SPY 450C 12/31 10 חוזים במחיר $4.50",
        "מכרתי רבע מהפוזיציה של SPY",
        "סגרתי חצי מה-QQQ 380P 1/15",
        "קנייה: TSLA 200C 12/29 x5",
        "מכירה 25% SPY",
        "פתחתי לונג AAPL 180 CALL 1/20",
    ]

    for tweet in test_tweets:
        print(f"\n{'='*60}")
        print(f"Tweet: {tweet}")
        signal = parser.parse_tweet(tweet)
        if signal:
            print(f"Signal: {signal}")
            print(f"Confidence: {signal.confidence}")
        else:
            print("No signal detected")
        print(f"{'='*60}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    test_parser()
