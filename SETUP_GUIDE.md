# Quick Setup Guide

This is a streamlined guide to get you up and running quickly.

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Up Google Cloud Credentials

### For Service Account (Recommended):

1. Visit: https://console.cloud.google.com/
2. Create a new project (or use existing)
3. Enable Google Sheets API:
   - APIs & Services → Library → Search "Google Sheets API" → Enable
4. Create Service Account:
   - APIs & Services → Credentials → Create Credentials → Service Account
   - Download the JSON key file
5. Save the JSON file as `credentials.json` in this directory
6. **IMPORTANT**: Share your Google Sheet with the service account email
   - Open: https://docs.google.com/spreadsheets/d/1jiQlVCopTSIoyG1fAB2mR2JHhzy_H-ZqUb_HdJPyJ_o/edit
   - Click "Share" button
   - Add the email from `credentials.json` (looks like: xxx@xxx.iam.gserviceaccount.com)
   - Give "Editor" permission
   - Click "Send"

### For OAuth2 (Alternative):

1. Visit: https://console.cloud.google.com/
2. Create OAuth credentials:
   - APIs & Services → Credentials → Create Credentials → OAuth Client ID
   - Application type: Desktop app
3. Download and save as `credentials.json`
4. On first run, authenticate in browser

## Step 3: Verify Configuration

The `.env` file is already configured with your Sheet ID:
```
GOOGLE_SHEETS_ID=1jiQlVCopTSIoyG1fAB2mR2JHhzy_H-ZqUb_HdJPyJ_o
```

## Step 4: Run Your First Update

```bash
python run_sctr_update.py
```

This will:
- Scrape all SCTR data from StockCharts.com (all categories)
- Update your Google Sheet
- Take about 5-10 minutes depending on data size

## Step 5: (Optional) Set Up Daily Automation

To run automatically every day:

```bash
python schedule_daily_update.py
```

Default schedule: 6:00 PM EST daily

To run in background:
```bash
# Using screen
screen -S sctr
python schedule_daily_update.py
# Press Ctrl+A then D to detach

# To reattach later
screen -r sctr
```

## What Gets Created in Your Google Sheet

After running, you'll see these new sheets:

1. **SCTR_Large_Cap** - All large cap stocks
2. **SCTR_Mid_Cap** - All mid cap stocks
3. **SCTR_Small_Cap** - All small cap stocks
4. **SCTR_ETF** - All ETFs
5. **SCTR_Industries** - Industry data
6. **SCTR_Sectors** - Sector data
7. **SCTR_Combined** - Everything in one sheet
8. **SCTR_Summary** - Statistics and aggregates

## Troubleshooting

### Error: "credentials.json not found"
- Make sure you downloaded the credentials file
- Save it as `credentials.json` in this directory

### Error: "Access denied" or "403 Forbidden"
- Did you share the Google Sheet with the service account email?
- Is the Google Sheets API enabled in Google Cloud Console?

### Error: "No data scraped"
- Check your internet connection
- StockCharts.com might be temporarily down
- Try running with visible browser (see README.md)

### Chrome/WebDriver errors
- Make sure Chrome is installed
- The webdriver-manager should auto-install ChromeDriver
- If not, install ChromeDriver manually

## Next Steps

- Check your Google Sheet to see the data
- Set up daily automation if desired
- Customize categories or statistics (see README.md)

## Files You Need

✅ **Already created for you:**
- `.env` - Configuration (Sheet ID already set)
- All Python scripts

🔴 **You need to create:**
- `credentials.json` - Download from Google Cloud Console

## Support

See the main [README.md](README.md) for detailed documentation and troubleshooting.
