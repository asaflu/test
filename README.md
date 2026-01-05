# Trading Bot - @ultrawavetrader Copy Trader

Automated trading bot that monitors [@ultrawavetrader](https://x.com/ultrawavetrader) on X.com and automatically copies their option trades to your Interactive Brokers account at 10% of the original size.

## 🚀 Features

- **Real-time Twitter Monitoring**: Monitors tweets without requiring Twitter API keys (uses snscrape)
- **Hebrew Text Parsing**: Understands Hebrew trading language including position sizes (רבע, חצי, etc.)
- **Automatic Trade Execution**: Executes trades through IBKR TWS/Gateway
- **Smart Position Sizing**: Automatically trades at 10% of the original position size
- **Partial Sell Support**: Handles partial position exits (quarter, half, etc.)
- **Position Tracking**: Maintains accurate position records and calculates P&L
- **Risk Management**: Configurable maximum position sizes
- **Dry-Run Mode**: Test the bot without executing real trades
- **Comprehensive Logging**: Detailed logs with color-coded console output

## 📋 Prerequisites

1. **Python 3.8+**
2. **Interactive Brokers Account**
3. **TWS (Trader Workstation) or IB Gateway** installed and running
4. **snscrape** for Twitter monitoring (no API key needed)

## 🛠️ Installation

### 1. Clone the Repository

```bash
cd trading-bot
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install snscrape

```bash
# Install snscrape for Twitter monitoring
pip install snscrape
```

### 5. Configure Environment

Copy the example environment file and edit it:

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

Edit `.env` with your settings:

```bash
# Twitter Account to Monitor (no API key needed)
TWITTER_ACCOUNT=ultrawavetrader

# IBKR Configuration
IBKR_HOST=127.0.0.1
IBKR_PORT=7497  # See port guide below
IBKR_CLIENT_ID=1

# Trading Configuration
POSITION_SIZE_MULTIPLIER=0.10  # 10% of original size
ENABLE_TRADING=false  # Set to true when ready for live trading

# Risk Management
MAX_POSITION_SIZE=10000  # Maximum position size in USD

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/trading_bot.log
```

#### IBKR Port Configuration

- `7497` - TWS Paper Trading (recommended for testing)
- `7496` - TWS Live Trading
- `4002` - IB Gateway Paper Trading
- `4001` - IB Gateway Live Trading

## 🎯 Setup IBKR TWS/Gateway

### 1. Enable API Connections

1. Open TWS or IB Gateway
2. Go to **File → Global Configuration → API → Settings**
3. Check **"Enable ActiveX and Socket Clients"**
4. Set **Socket port** to match your `.env` configuration (default: 7497 for paper trading)
5. Check **"Allow connections from localhost only"** (for security)
6. Uncheck **"Read-Only API"** (to allow trading)
7. Click **OK** and restart TWS/Gateway

### 2. Paper Trading Setup (Recommended for Testing)

1. Log into TWS with your paper trading account
2. Verify you have options trading permissions
3. Fund your paper account with virtual money ($100,000+ recommended)

### 3. Verify Connection

```bash
# Test IBKR connection
python -c "from ib_insync import *; ib = IB(); ib.connect('127.0.0.1', 7497, clientId=1); print('Connected:', ib.isConnected()); ib.disconnect()"
```

## 🚀 Running the Bot

### 1. Start TWS/Gateway

Make sure TWS or IB Gateway is running and API connections are enabled.

### 2. Run in Dry-Run Mode (Recommended First)

Start with `ENABLE_TRADING=false` in your `.env` file:

```bash
python run_bot.py
```

The bot will:
- Monitor @ultrawavetrader tweets
- Parse and log trading signals
- Show what trades it WOULD execute
- **NOT execute actual trades**

### 3. Enable Live Trading

When ready, update `.env`:

```bash
ENABLE_TRADING=true
```

Then run:

```bash
python run_bot.py
```

⚠️ **Warning**: This will execute real trades in your IBKR account!

## 📊 How It Works

### Tweet Detection

The bot monitors @ultrawavetrader tweets and recognizes:

**Buy Signals** (Hebrew keywords):
- קניתי (I bought)
- קנייה (Purchase)
- לונג (Long)
- פתחתי (I opened)

**Sell Signals** (Hebrew keywords):
- מכירה (Sale)
- מכרתי (I sold)
- סגירה (Closing)
- סגרתי (I closed)

**Position Sizes** (Hebrew):
- רבע (Quarter - 25%)
- שליש (Third - 33%)
- חצי (Half - 50%)
- שני שלישים (Two thirds - 66%)
- שלושה רבעים (Three quarters - 75%)
- מלא/הכל (Full/Everything - 100%)

### Example Tweets

**Buy Example:**
```
קניתי SPY 450C 12/31 10 חוזים במחיר $4.50
(I bought SPY 450C 12/31 10 contracts at $4.50)
```

Bot will:
- Detect BUY signal
- Parse: SPY 450 CALL expiring 12/31
- Calculate: 10 contracts × 10% = 1 contract
- Execute: BUY 1 x SPY 450C 12/31 @ market price

**Sell Example:**
```
מכרתי רבע מ-SPY
(I sold a quarter of SPY)
```

Bot will:
- Detect SELL signal
- Find your SPY position
- Calculate: 25% of your position
- Execute: SELL that amount @ market price

## 📁 Project Structure

```
trading-bot/
├── src/
│   ├── __init__.py
│   ├── main.py              # Main orchestrator
│   ├── twitter_monitor.py   # Twitter monitoring (snscrape)
│   ├── hebrew_parser.py     # Hebrew text parsing
│   ├── ibkr_client.py       # IBKR TWS API client
│   ├── trade_executor.py    # Trade execution logic
│   └── position_manager.py  # Position tracking
├── logs/                     # Log files
├── data/                     # Position data
├── config.yaml              # Trading configuration
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
├── run_bot.py              # Startup script
└── README.md               # This file
```

## 🔧 Configuration

### config.yaml

Edit `config.yaml` to customize:

- Hebrew keywords for buy/sell signals
- Position size keywords
- Option parsing patterns
- Execution settings
- Monitoring intervals

### .env

Environment variables:
- `TWITTER_ACCOUNT`: Twitter handle to monitor
- `IBKR_HOST/PORT`: IBKR connection settings
- `POSITION_SIZE_MULTIPLIER`: Trade size (0.10 = 10%)
- `ENABLE_TRADING`: Enable/disable actual trading
- `MAX_POSITION_SIZE`: Maximum position value in USD
- `LOG_LEVEL`: Logging verbosity (DEBUG/INFO/WARNING/ERROR)

## 📝 Logging

Logs are written to:
- **Console**: Color-coded output
- **File**: `logs/trading_bot.log`

Log levels:
- **DEBUG**: Detailed information for troubleshooting
- **INFO**: General informational messages (default)
- **WARNING**: Warning messages
- **ERROR**: Error messages

## 🛡️ Risk Management

### Built-in Safety Features

1. **Dry-Run Mode**: Test without real trades
2. **Position Size Limits**: Maximum position size enforced
3. **Paper Trading**: Use TWS paper account for testing
4. **Confidence Scoring**: Only execute high-confidence signals
5. **Age Filtering**: Only process recent tweets (< 5 minutes old)
6. **Position Tracking**: Accurate tracking prevents over-trading

### Recommended Safety Practices

1. ✅ Start with paper trading
2. ✅ Use dry-run mode first
3. ✅ Set conservative `MAX_POSITION_SIZE`
4. ✅ Monitor the bot actively at first
5. ✅ Review logs regularly
6. ✅ Keep `POSITION_SIZE_MULTIPLIER` small (0.05-0.10)
7. ⚠️ Never run multiple instances simultaneously
8. ⚠️ Ensure sufficient buying power in your account

## 🧪 Testing

### Test Individual Components

**Test Twitter Monitor:**
```bash
python -m src.twitter_monitor
```

**Test Hebrew Parser:**
```bash
python -m src.hebrew_parser
```

**Test IBKR Client:**
```bash
python -m src.ibkr_client
```

**Test Trade Executor:**
```bash
python -m src.trade_executor
```

### Integration Testing

1. Start with paper trading account
2. Set `ENABLE_TRADING=false`
3. Run the bot and monitor logs
4. Verify signal detection and parsing
5. Enable trading with small position sizes
6. Execute a few test trades
7. Verify positions and P&L

## 🐛 Troubleshooting

### Bot Can't Connect to IBKR

- ✅ Verify TWS/Gateway is running
- ✅ Check API settings are enabled
- ✅ Verify port number in `.env` matches TWS settings
- ✅ Try restarting TWS/Gateway

### No Tweets Detected

- ✅ Check your internet connection
- ✅ Verify Twitter account name is correct
- ✅ Check if snscrape is working: `snscrape twitter-user ultrawavetrader`
- ✅ Twitter may have rate-limited scraping (wait and retry)

### Trade Signals Not Parsed

- ✅ Check tweet format matches expected patterns
- ✅ Enable DEBUG logging: `LOG_LEVEL=DEBUG`
- ✅ Review logs for parsing details
- ✅ Update Hebrew keywords in `config.yaml` if needed

### Orders Not Executing

- ✅ Verify `ENABLE_TRADING=true` in `.env`
- ✅ Check you have trading permissions for options
- ✅ Verify sufficient buying power
- ✅ Check option contract exists and is liquid
- ✅ Review TWS order status window

### Position Tracking Issues

- ✅ Check `data/positions.json` for accuracy
- ✅ Manually verify positions in TWS
- ✅ Delete `data/positions.json` to reset (back up first!)

## 📚 Dependencies

Main libraries used:
- **ib_insync** - Interactive Brokers API
- **snscrape** - Twitter scraping (no API key)
- **pyyaml** - Configuration management
- **python-dotenv** - Environment variables
- **colorlog** - Colored logging
- **pandas** - Data handling

## ⚠️ Disclaimer

**THIS SOFTWARE IS PROVIDED FOR EDUCATIONAL PURPOSES ONLY.**

- Trading involves risk and can result in loss of capital
- This bot is provided "as is" without warranty of any kind
- The author is not responsible for any financial losses
- Always test thoroughly with paper trading first
- Never trade with money you can't afford to lose
- Consult with a financial advisor before trading

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review logs for error details

## 🔄 Updates

The bot monitors @ultrawavetrader's tweet patterns. If the trading format changes, you may need to:

1. Update Hebrew keywords in `config.yaml`
2. Modify parsing patterns in `hebrew_parser.py`
3. Test with recent tweets

## 📈 Future Enhancements

Potential improvements:
- [ ] Web dashboard for monitoring
- [ ] Telegram/Discord notifications
- [ ] Multiple account support
- [ ] Advanced risk management rules
- [ ] Machine learning for signal confidence
- [ ] Backtesting capabilities
- [ ] Performance analytics dashboard

---

**Happy Trading! 📊📈**

Remember: Start with paper trading, use dry-run mode, and always manage your risk!
