"""
Trading Bot Main - Orchestrates Twitter monitoring and trade execution
Follows @ultrawavetrader and copies trades to IBKR
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import colorlog
import signal

from src.twitter_monitor import TwitterMonitor, Tweet
from src.hebrew_parser import HebrewParser
from src.ibkr_client import IBKRClient
from src.position_manager import PositionManager
from src.trade_executor import TradeExecutor

# Global flag for graceful shutdown
shutdown_flag = False


def setup_logging(log_level: str = 'INFO', log_file: str = 'logs/trading_bot.log'):
    """
    Setup colored logging to console and file

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
    """
    # Create logs directory
    os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else '.', exist_ok=True)

    # Create formatter
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Console handler with colors
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt=date_format,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reduce noise from some libraries
    logging.getLogger('ib_insync').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized")


def load_config():
    """
    Load configuration from environment variables

    Returns:
        Dict with configuration
    """
    load_dotenv()

    config = {
        # Twitter
        'twitter_account': os.getenv('TWITTER_ACCOUNT', 'ultrawavetrader'),

        # IBKR
        'ibkr_host': os.getenv('IBKR_HOST', '127.0.0.1'),
        'ibkr_port': int(os.getenv('IBKR_PORT', 7497)),
        'ibkr_client_id': int(os.getenv('IBKR_CLIENT_ID', 1)),

        # Trading
        'position_size_multiplier': float(os.getenv('POSITION_SIZE_MULTIPLIER', 0.10)),
        'enable_trading': os.getenv('ENABLE_TRADING', 'false').lower() == 'true',
        'max_position_size': float(os.getenv('MAX_POSITION_SIZE', 10000)),

        # Logging
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'log_file': os.getenv('LOG_FILE', 'logs/trading_bot.log'),
    }

    return config


async def handle_tweet(tweet: Tweet, parser: HebrewParser, executor: TradeExecutor):
    """
    Handle a new tweet - parse and execute if it's a trade signal

    Args:
        tweet: Tweet object
        parser: Hebrew parser
        executor: Trade executor
    """
    logger = logging.getLogger(__name__)

    logger.info(f"\n{'='*80}")
    logger.info(f"New tweet from @{tweet.url.split('/')[3]}")
    logger.info(f"Time: {tweet.created_at}")
    logger.info(f"URL: {tweet.url}")
    logger.info(f"Text: {tweet.text}")
    logger.info(f"{'='*80}")

    # Parse tweet
    signal = parser.parse_tweet(tweet.text)

    if not signal:
        logger.info("No trading signal detected in tweet")
        return

    logger.info(f"✓ Detected {signal.action} signal (confidence: {signal.confidence:.2f})")

    # Check confidence threshold
    if signal.confidence < 0.5:
        logger.warning(f"Signal confidence too low ({signal.confidence:.2f}), skipping")
        return

    # Execute signal
    try:
        success = await executor.execute_signal(signal, tweet.url)

        if success:
            logger.info("✓ Signal executed successfully")
        else:
            logger.error("✗ Failed to execute signal")

    except Exception as e:
        logger.error(f"Error executing signal: {e}", exc_info=True)


def signal_handler(sig, frame):
    """Handle interrupt signals for graceful shutdown"""
    global shutdown_flag
    logger = logging.getLogger(__name__)
    logger.info("\nShutdown signal received, stopping...")
    shutdown_flag = True


async def main():
    """Main function - runs the trading bot"""
    global shutdown_flag

    # Load configuration
    config = load_config()

    # Setup logging
    setup_logging(config['log_level'], config['log_file'])
    logger = logging.getLogger(__name__)

    logger.info("="*80)
    logger.info("Starting Trading Bot - @ultrawavetrader Copy Trader")
    logger.info("="*80)

    # Display configuration
    logger.info("Configuration:")
    logger.info(f"  Twitter Account: @{config['twitter_account']}")
    logger.info(f"  IBKR Connection: {config['ibkr_host']}:{config['ibkr_port']}")
    logger.info(f"  Position Size: {config['position_size_multiplier']*100}% of original")
    logger.info(f"  Max Position Size: ${config['max_position_size']}")
    logger.info(f"  Trading Mode: {'LIVE' if config['enable_trading'] else 'DRY-RUN'}")
    logger.info("="*80)

    if not config['enable_trading']:
        logger.warning("⚠ RUNNING IN DRY-RUN MODE - No actual trades will be executed")
        logger.warning("⚠ Set ENABLE_TRADING=true in .env to enable live trading")
        logger.info("="*80)

    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize components
    logger.info("Initializing components...")

    parser = HebrewParser('config.yaml')
    logger.info("✓ Hebrew parser initialized")

    position_manager = PositionManager('data/positions.json')
    logger.info(f"✓ Position manager initialized ({len(position_manager.get_all_positions())} open positions)")

    ibkr_client = IBKRClient(
        host=config['ibkr_host'],
        port=config['ibkr_port'],
        client_id=config['ibkr_client_id']
    )
    logger.info("✓ IBKR client initialized")

    # Connect to IBKR
    logger.info("Connecting to IBKR TWS...")
    connected = await ibkr_client.connect()

    if not connected:
        logger.error("Failed to connect to IBKR TWS")
        logger.error("Please ensure TWS or IB Gateway is running and accepting connections")
        sys.exit(1)

    logger.info("✓ Connected to IBKR TWS")

    # Get account summary
    summary = await ibkr_client.get_account_summary()
    if 'NetLiquidation' in summary:
        logger.info(f"  Account Value: ${float(summary['NetLiquidation']):,.2f}")
    if 'AvailableFunds' in summary:
        logger.info(f"  Available Funds: ${float(summary['AvailableFunds']):,.2f}")

    # Initialize trade executor
    executor = TradeExecutor(
        ibkr_client=ibkr_client,
        position_manager=position_manager,
        position_size_multiplier=config['position_size_multiplier'],
        enable_trading=config['enable_trading'],
        max_position_size=config['max_position_size']
    )
    logger.info("✓ Trade executor initialized")

    # Display current positions
    logger.info("\nCurrent Positions:")
    positions = position_manager.get_all_positions()
    if positions:
        for i, pos in enumerate(positions, 1):
            logger.info(f"  {i}. {pos}")
    else:
        logger.info("  No open positions")

    logger.info("\n" + "="*80)
    logger.info("Starting Twitter monitor...")
    logger.info(f"Monitoring @{config['twitter_account']} for trading signals")
    logger.info("="*80 + "\n")

    # Initialize Twitter monitor
    twitter_monitor = TwitterMonitor(
        username=config['twitter_account'],
        poll_interval=10,  # Check every 10 seconds
        max_tweet_age=300  # Only process tweets less than 5 minutes old
    )

    # Start monitoring with callback
    async def tweet_callback(tweet: Tweet):
        if not shutdown_flag:
            await handle_tweet(tweet, parser, executor)

    try:
        # This will run forever until interrupted
        await twitter_monitor.start_monitoring(tweet_callback)

    except KeyboardInterrupt:
        logger.info("\nKeyboard interrupt received")
    except Exception as e:
        logger.error(f"Error in main loop: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("\nShutting down...")
        twitter_monitor.stop_monitoring()
        ibkr_client.disconnect()
        logger.info("✓ Disconnected from IBKR")
        logger.info("Trading bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
