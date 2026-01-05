"""
SCTR Manager
Main orchestrator for scraping SCTR data and updating Google Sheets
"""

import os
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
from dotenv import load_dotenv

from sctr_scraper import SCTRScraper
from google_sheets_client import GoogleSheetsClient


class SCTRManager:
    """Manages SCTR data scraping and Google Sheets updates"""

    def __init__(self, spreadsheet_id: str):
        """
        Initialize SCTR Manager

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
        """
        self.spreadsheet_id = spreadsheet_id
        self.scraper = SCTRScraper(headless=True)
        self.sheets_client = GoogleSheetsClient(spreadsheet_id)
        self.today = datetime.now().strftime('%Y-%m-%d')

    def scrape_all_data(self) -> Dict[str, pd.DataFrame]:
        """Scrape SCTR data for all categories"""
        print(f"\n{'='*80}")
        print(f"Starting SCTR data collection for {self.today}")
        print(f"{'='*80}\n")

        return self.scraper.scrape_all_categories()

    def calculate_aggregates(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate aggregate statistics for a category

        Args:
            df: DataFrame with SCTR data

        Returns:
            Dictionary with aggregate statistics
        """
        aggregates = {
            'Total Stocks': len(df),
            'Date': self.today
        }

        # Try to extract numeric SCTR values for statistics
        if 'SCTR' in df.columns:
            try:
                sctr_values = pd.to_numeric(df['SCTR'], errors='coerce')
                aggregates['Average SCTR'] = f"{sctr_values.mean():.2f}"
                aggregates['Median SCTR'] = f"{sctr_values.median():.2f}"
                aggregates['Min SCTR'] = f"{sctr_values.min():.2f}"
                aggregates['Max SCTR'] = f"{sctr_values.max():.2f}"

                # Count stocks by SCTR ranges
                aggregates['SCTR > 80'] = len(sctr_values[sctr_values > 80])
                aggregates['SCTR 60-80'] = len(sctr_values[(sctr_values >= 60) & (sctr_values <= 80)])
                aggregates['SCTR 40-60'] = len(sctr_values[(sctr_values >= 40) & (sctr_values < 60)])
                aggregates['SCTR < 40'] = len(sctr_values[sctr_values < 40])

            except Exception as e:
                print(f"Error calculating SCTR statistics: {e}")

        return aggregates

    def prepare_sheet_data_with_daily_change(self, df: pd.DataFrame,
                                             category_name: str,
                                             previous_data: Dict = None) -> List[List[Any]]:
        """
        Prepare data for Google Sheets with daily change calculations

        Args:
            df: Current DataFrame with SCTR data
            category_name: Name of the category
            previous_data: Previous day's data for comparison (if available)

        Returns:
            2D list ready for Google Sheets
        """
        rows = []

        # Add category header
        rows.append([f"=== {category_name} - {self.today} ==="])
        rows.append([])  # Empty row

        # Add aggregate statistics
        aggregates = self.calculate_aggregates(df)
        rows.append(["AGGREGATE STATISTICS"])
        for key, value in aggregates.items():
            rows.append([key, value])

        rows.append([])  # Empty row separator
        rows.append([])  # Another empty row

        # Add column headers
        headers = df.columns.tolist()

        # Add "Daily Change" columns if we have previous data
        if previous_data is not None:
            headers.extend(['Daily Change', 'Change %'])

        rows.append(headers)

        # Add data rows with daily change calculations
        for idx, row in df.iterrows():
            row_data = row.tolist()

            # Calculate daily change if previous data exists
            if previous_data is not None:
                # Try to find matching ticker in previous data
                ticker = row.get('Symbol') or row.get('Ticker') or row.get('Name')
                if ticker and ticker in previous_data:
                    try:
                        current_sctr = float(row.get('SCTR', 0))
                        prev_sctr = float(previous_data[ticker].get('SCTR', 0))
                        change = current_sctr - prev_sctr
                        change_pct = (change / prev_sctr * 100) if prev_sctr > 0 else 0

                        row_data.append(f"{change:+.2f}")
                        row_data.append(f"{change_pct:+.2f}%")
                    except:
                        row_data.extend(['N/A', 'N/A'])
                else:
                    row_data.extend(['NEW', 'NEW'])

            rows.append(row_data)

            # Add empty row between tickers for daily change tracking
            rows.append([])

        return rows

    def create_combined_sheet(self, all_data: Dict[str, pd.DataFrame],
                             previous_data: Dict = None) -> List[List[Any]]:
        """
        Create a combined sheet with all categories

        Args:
            all_data: Dictionary of category name -> DataFrame
            previous_data: Previous day's data for comparison

        Returns:
            2D list ready for Google Sheets
        """
        rows = []

        # Add title and date
        rows.append([f"SCTR Daily Report - {self.today}"])
        rows.append([f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"])
        rows.append([])
        rows.append(['='*100])
        rows.append([])

        # Add each category
        for category_name, df in all_data.items():
            prev_cat_data = previous_data.get(category_name) if previous_data else None
            category_rows = self.prepare_sheet_data_with_daily_change(
                df, category_name, prev_cat_data
            )
            rows.extend(category_rows)

            # Add separator between categories
            rows.append([])
            rows.append(['='*100])
            rows.append([])

        return rows

    def update_google_sheets(self, all_data: Dict[str, pd.DataFrame]):
        """
        Update Google Sheets with scraped data

        Args:
            all_data: Dictionary of category name -> DataFrame
        """
        print(f"\n{'='*80}")
        print("Updating Google Sheets")
        print(f"{'='*80}\n")

        # Get existing sheets to check for previous data
        existing_sheets = self.sheets_client.get_sheet_names()
        print(f"Existing sheets: {existing_sheets}")

        # Read previous day's data if available
        previous_data = {}
        if "SCTR_Combined" in existing_sheets:
            try:
                # Here you would implement logic to parse previous data
                # For now, we'll skip this and just create new sheets
                pass
            except Exception as e:
                print(f"Could not read previous data: {e}")

        # Create or update individual category sheets
        for category_name, df in all_data.items():
            sheet_name = f"SCTR_{category_name.replace(' ', '_')}"

            # Create sheet if it doesn't exist
            if sheet_name not in existing_sheets:
                self.sheets_client.create_sheet(sheet_name)

            # Prepare data with daily change tracking
            sheet_data = self.prepare_sheet_data_with_daily_change(
                df, category_name, previous_data.get(category_name)
            )

            # Write data to sheet
            self.sheets_client.write_data(sheet_name, sheet_data, clear_first=True)
            self.sheets_client.format_header(sheet_name)

            print(f"✓ Updated sheet: {sheet_name}")

        # Create combined sheet with all categories
        combined_sheet_name = "SCTR_Combined"
        if combined_sheet_name not in existing_sheets:
            self.sheets_client.create_sheet(combined_sheet_name)

        combined_data = self.create_combined_sheet(all_data, previous_data)
        self.sheets_client.write_data(combined_sheet_name, combined_data, clear_first=True)

        print(f"✓ Updated combined sheet: {combined_sheet_name}")

        # Create or update summary sheet
        self.create_summary_sheet(all_data)

        print(f"\n{'='*80}")
        print("Google Sheets update completed!")
        print(f"{'='*80}\n")

    def create_summary_sheet(self, all_data: Dict[str, pd.DataFrame]):
        """Create a summary sheet with high-level statistics"""
        sheet_name = "SCTR_Summary"

        existing_sheets = self.sheets_client.get_sheet_names()
        if sheet_name not in existing_sheets:
            self.sheets_client.create_sheet(sheet_name)

        rows = []
        rows.append([f"SCTR Summary - {self.today}"])
        rows.append([])

        # Summary table
        rows.append(['Category', 'Total Stocks', 'Avg SCTR', 'SCTR > 80', 'SCTR 60-80', 'SCTR 40-60', 'SCTR < 40'])

        for category_name, df in all_data.items():
            aggregates = self.calculate_aggregates(df)

            row = [
                category_name,
                aggregates.get('Total Stocks', 0),
                aggregates.get('Average SCTR', 'N/A'),
                aggregates.get('SCTR > 80', 0),
                aggregates.get('SCTR 60-80', 0),
                aggregates.get('SCTR 40-60', 0),
                aggregates.get('SCTR < 40', 0)
            ]
            rows.append(row)

        self.sheets_client.write_data(sheet_name, rows, clear_first=True)
        self.sheets_client.format_header(sheet_name)

        print(f"✓ Updated summary sheet: {sheet_name}")

    def run(self):
        """Main execution method"""
        try:
            # Step 1: Scrape all data
            all_data = self.scrape_all_data()

            if not all_data:
                print("ERROR: No data was scraped. Please check the scraper configuration.")
                return False

            # Step 2: Update Google Sheets
            self.update_google_sheets(all_data)

            print("\n✓ SCTR data collection and update completed successfully!")
            return True

        except Exception as e:
            print(f"\n✗ Error during execution: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point"""
    # Load environment variables
    load_dotenv()

    spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')
    if not spreadsheet_id:
        print("ERROR: GOOGLE_SHEETS_ID not set in environment")
        print("Please create a .env file with GOOGLE_SHEETS_ID=your_spreadsheet_id")
        return

    # Create and run manager
    manager = SCTRManager(spreadsheet_id)
    manager.run()


if __name__ == "__main__":
    main()
