# SCTR Google Sheets Integration

Automated system to scrape StockCharts Technical Rank (SCTR) data from [StockCharts.com](https://stockcharts.com/freecharts/sctr.html) and sync it to Google Sheets on a daily basis.

## Features

- 📊 **Complete Data Coverage**: Scrapes ALL SCTR data (not limited to 500 records)
- 🎯 **Multiple Categories**: Supports Large Cap, Mid Cap, Small Cap, ETF, Industries, and Sectors
- 📈 **Daily Change Tracking**: Automatically calculates daily changes in SCTR values
- 📑 **Multiple Sheet Views**:
  - Individual sheets per category
  - Combined view with all categories
  - Summary sheet with aggregate statistics
- ⏰ **Automated Updates**: Optional scheduler for daily automatic updates
- 🔄 **Google Sheets Integration**: Direct sync to your Google Spreadsheet

## Google Sheet Structure

The system creates the following sheets in your Google Spreadsheet:

1. **SCTR_Large_Cap**: All large cap stocks with SCTR data
2. **SCTR_Mid_Cap**: All mid cap stocks with SCTR data
3. **SCTR_Small_Cap**: All small cap stocks with SCTR data
4. **SCTR_ETF**: All ETFs with SCTR data
5. **SCTR_Industries**: Industry SCTR data
6. **SCTR_Sectors**: Sector SCTR data
7. **SCTR_Combined**: All categories combined in one sheet
8. **SCTR_Summary**: High-level statistics and aggregates

### Sheet Format

Each category sheet includes:
- **Header Section**: Category name and date
- **Aggregate Statistics**:
  - Total stocks
  - Average SCTR
  - SCTR distribution (>80, 60-80, 40-60, <40)
- **Data Section**:
  - All stock data from the website
  - Daily change columns (if previous data exists)
  - Empty row between each ticker for manual calculations

## Prerequisites

- Python 3.8 or higher
- Google Cloud project with Sheets API enabled
- Chrome browser (for Selenium WebDriver)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Google Sheets API

#### Option A: Service Account (Recommended for automation)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"
4. Create a service account:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Fill in the details and click "Create"
5. Download the credentials:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create New Key"
   - Select "JSON" and download
6. Save the downloaded file as `credentials.json` in the project root
7. Share your Google Sheet with the service account email:
   - Open your Google Sheet
   - Click "Share"
   - Add the service account email (found in credentials.json)
   - Grant "Editor" permissions

#### Option B: OAuth2 (For personal use)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Google Sheets API (same as above)
3. Create OAuth2 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth Client ID"
   - Choose "Desktop app"
   - Download the credentials
4. Save as `credentials.json` in the project root
5. On first run, a browser window will open for authentication

### 4. Configure Environment Variables

Create a `.env` file in the project root (or copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and set your Google Sheets ID:

```
GOOGLE_SHEETS_ID=1jiQlVCopTSIoyG1fAB2mR2JHhzy_H-ZqUb_HdJPyJ_o
```

To find your Sheets ID, look at your Google Sheets URL:
```
https://docs.google.com/spreadsheets/d/[SHEETS_ID]/edit
```

## Usage

### Manual Update

Run a single update:

```bash
python run_sctr_update.py
```

This will:
1. Scrape all SCTR data from all categories
2. Calculate aggregates and statistics
3. Update your Google Sheet with the latest data
4. Create logs in `sctr_update_YYYYMMDD.log`

### Scheduled Daily Updates

Run the scheduler for automatic daily updates:

```bash
python schedule_daily_update.py
```

By default, updates run at 6:00 PM EST daily (after market close). You can modify the schedule time in `schedule_daily_update.py`:

```python
schedule_time = "18:00"  # Change to your preferred time (24-hour format)
```

### Running as a Background Service

#### Linux/Mac (using screen or tmux):

```bash
# Using screen
screen -S sctr-scheduler
python schedule_daily_update.py
# Press Ctrl+A, then D to detach

# Using tmux
tmux new -s sctr-scheduler
python schedule_daily_update.py
# Press Ctrl+B, then D to detach
```

#### Using systemd (Linux):

Create a service file `/etc/systemd/system/sctr-scheduler.service`:

```ini
[Unit]
Description=SCTR Daily Scheduler
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 /path/to/project/schedule_daily_update.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable sctr-scheduler
sudo systemctl start sctr-scheduler
sudo systemctl status sctr-scheduler
```

## Project Structure

```
.
├── sctr_scraper.py              # Web scraper for SCTR data
├── google_sheets_client.py      # Google Sheets API client
├── sctr_manager.py              # Main orchestrator
├── run_sctr_update.py           # Manual update script
├── schedule_daily_update.py     # Daily scheduler
├── requirements.txt             # Python dependencies
├── .env                         # Environment configuration
├── .env.example                 # Example environment file
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

## How It Works

1. **Scraping**:
   - Uses Selenium WebDriver to navigate to StockCharts.com
   - Iterates through all category dropdown options
   - Handles pagination to get ALL data (not just first 500)
   - Extracts data from HTML tables

2. **Data Processing**:
   - Converts scraped data to pandas DataFrames
   - Calculates aggregate statistics
   - Computes daily changes (if previous data exists)
   - Formats data for Google Sheets

3. **Google Sheets Update**:
   - Creates/updates individual category sheets
   - Creates combined view with all categories
   - Adds aggregate statistics to each sheet
   - Formats headers (bold, frozen, colored)
   - Inserts empty rows between tickers for manual calculations

## Troubleshooting

### "403 Forbidden" or "Access Denied" errors

- Make sure you've shared your Google Sheet with the service account email
- Verify the Google Sheets API is enabled in your Google Cloud project
- Check that `credentials.json` is in the project root

### Selenium/WebDriver errors

- Make sure Chrome browser is installed
- The `webdriver-manager` package should automatically download the correct ChromeDriver
- If issues persist, try installing ChromeDriver manually

### "No data scraped" errors

- The StockCharts.com website structure may have changed
- Check if the website is accessible from your location
- Try running with `headless=False` in `sctr_scraper.py` to see what's happening:
  ```python
  self.scraper = SCTRScraper(headless=False)
  ```

### Rate limiting or blocking

- The scraper includes delays to avoid being blocked
- If you get blocked, try increasing the sleep times in `sctr_scraper.py`
- Consider using a proxy or VPN if needed

## Customization

### Changing Categories

Edit the `CATEGORIES` dictionary in `sctr_scraper.py`:

```python
CATEGORIES = {
    "Large Cap": "large",
    "Mid Cap": "mid",
    # Add or remove categories as needed
}
```

### Modifying Aggregate Statistics

Edit the `calculate_aggregates` method in `sctr_manager.py` to add custom calculations.

### Adjusting Sheet Formatting

Modify the `prepare_sheet_data_with_daily_change` and `format_header` methods to customize the appearance.

## Data Privacy & Security

- Never commit `credentials.json` or `.env` files to version control
- Keep your Google Cloud credentials secure
- Regularly rotate API keys and credentials
- Only grant minimum necessary permissions to service accounts

## License

This project is provided as-is for personal use.

## Support

For issues related to:
- **StockCharts.com**: Contact StockCharts support
- **Google Sheets API**: See [Google Sheets API documentation](https://developers.google.com/sheets/api)
- **This project**: Open an issue in the repository

## Disclaimer

This tool is for personal use and data analysis only. Make sure to comply with StockCharts.com's terms of service and robots.txt. The authors are not responsible for any misuse of this software or violations of third-party terms of service.
