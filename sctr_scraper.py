"""
SCTR Data Scraper
Scrapes StockCharts Technical Rank (SCTR) data for all categories
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from datetime import datetime
from typing import Dict, List


class SCTRScraper:
    """Scraper for SCTR data from stockcharts.com"""

    SCTR_URL = "https://stockcharts.com/freecharts/sctr.html"

    # Categories based on the dropdown menu
    CATEGORIES = {
        "Large Cap": "large",
        "Mid Cap": "mid",
        "Small Cap": "small",
        "ETF": "etf",
        "Industries": "industry",
        "Sectors": "sector"
    }

    def __init__(self, headless: bool = True):
        """Initialize the scraper with Chrome webdriver"""
        self.headless = headless
        self.driver = None

    def setup_driver(self):
        """Set up Chrome webdriver with appropriate options"""
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)

    def close_driver(self):
        """Close the webdriver"""
        if self.driver:
            self.driver.quit()

    def wait_for_table_load(self, timeout: int = 30):
        """Wait for the SCTR table to load"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, "sctr-table"))
            )
            time.sleep(2)  # Additional wait for JavaScript to fully render
            return True
        except Exception as e:
            print(f"Error waiting for table: {e}")
            return False

    def select_category(self, category_value: str):
        """Select a category from the dropdown menu"""
        try:
            # Find the category dropdown
            select_element = self.driver.find_element(By.ID, "sctrGroup")
            select = Select(select_element)
            select.select_by_value(category_value)

            # Wait for the table to reload
            time.sleep(3)
            self.wait_for_table_load()
            return True
        except Exception as e:
            print(f"Error selecting category {category_value}: {e}")
            return False

    def get_all_rows(self) -> List[Dict]:
        """Get all SCTR data rows from the current page"""
        rows_data = []

        try:
            # Try different possible table selectors
            table = None
            possible_selectors = [
                (By.CLASS_NAME, "sctr-table"),
                (By.TAG_NAME, "table"),
                (By.ID, "sctrTable"),
                (By.CSS_SELECTOR, "table.table")
            ]

            for by, selector in possible_selectors:
                try:
                    table = self.driver.find_element(by, selector)
                    if table:
                        break
                except:
                    continue

            if not table:
                print("Could not find SCTR table")
                return rows_data

            # Get all rows
            rows = table.find_elements(By.TAG_NAME, "tr")

            # Get headers
            headers = []
            header_row = rows[0]
            header_cells = header_row.find_elements(By.TAG_NAME, "th")
            if not header_cells:
                header_cells = header_row.find_elements(By.TAG_NAME, "td")

            for cell in header_cells:
                headers.append(cell.text.strip())

            # Get data rows
            for row in rows[1:]:
                cells = row.find_elements(By.TAG_NAME, "td")
                if not cells:
                    continue

                row_data = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        row_data[headers[i]] = cell.text.strip()
                    else:
                        row_data[f"Column_{i}"] = cell.text.strip()

                if row_data:
                    rows_data.append(row_data)

            print(f"Extracted {len(rows_data)} rows")

        except Exception as e:
            print(f"Error extracting table data: {e}")

        return rows_data

    def check_for_pagination(self) -> bool:
        """Check if there are more pages and navigate if needed"""
        try:
            # Look for "Show More", "Load More", or pagination buttons
            possible_buttons = [
                (By.LINK_TEXT, "Show More"),
                (By.LINK_TEXT, "Load More"),
                (By.CLASS_NAME, "show-more"),
                (By.CLASS_NAME, "load-more"),
                (By.CSS_SELECTOR, "button.more"),
                (By.XPATH, "//button[contains(text(), 'Show')]"),
                (By.XPATH, "//a[contains(text(), 'Show')]")
            ]

            for by, selector in possible_buttons:
                try:
                    button = self.driver.find_element(by, selector)
                    if button and button.is_displayed():
                        button.click()
                        time.sleep(2)
                        return True
                except:
                    continue

            return False

        except Exception as e:
            print(f"Error checking pagination: {e}")
            return False

    def scrape_category(self, category_name: str, category_value: str) -> pd.DataFrame:
        """Scrape all SCTR data for a specific category"""
        print(f"\n{'='*60}")
        print(f"Scraping category: {category_name}")
        print(f"{'='*60}")

        all_data = []

        # Select the category
        if not self.select_category(category_value):
            print(f"Failed to select category: {category_name}")
            return pd.DataFrame()

        # Get initial data
        rows = self.get_all_rows()
        all_data.extend(rows)

        # Check for pagination and load all data
        max_attempts = 50  # Prevent infinite loops
        attempt = 0

        while attempt < max_attempts:
            has_more = self.check_for_pagination()
            if not has_more:
                break

            time.sleep(2)
            new_rows = self.get_all_rows()

            # Check if we got new data
            if len(new_rows) <= len(all_data):
                break

            all_data = new_rows
            attempt += 1
            print(f"Loaded page {attempt + 1}, total rows: {len(all_data)}")

        # Create DataFrame
        df = pd.DataFrame(all_data)

        if not df.empty:
            df['Category'] = category_name
            df['Scrape_Date'] = datetime.now().strftime('%Y-%m-%d')
            df['Scrape_Timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print(f"Total rows scraped for {category_name}: {len(df)}")
        return df

    def scrape_all_categories(self) -> Dict[str, pd.DataFrame]:
        """Scrape SCTR data for all categories"""
        print(f"Starting SCTR data scraping at {datetime.now()}")

        self.setup_driver()

        try:
            # Navigate to the SCTR page
            print(f"Navigating to {self.SCTR_URL}")
            self.driver.get(self.SCTR_URL)

            # Wait for initial page load
            self.wait_for_table_load()

            results = {}

            # Scrape each category
            for category_name, category_value in self.CATEGORIES.items():
                try:
                    df = self.scrape_category(category_name, category_value)
                    if not df.empty:
                        results[category_name] = df
                    else:
                        print(f"Warning: No data scraped for {category_name}")
                except Exception as e:
                    print(f"Error scraping {category_name}: {e}")
                    continue

            print(f"\n{'='*60}")
            print("Scraping completed!")
            print(f"Categories scraped: {len(results)}")
            for cat, df in results.items():
                print(f"  {cat}: {len(df)} rows")
            print(f"{'='*60}\n")

            return results

        finally:
            self.close_driver()


def main():
    """Main function to test the scraper"""
    scraper = SCTRScraper(headless=True)
    results = scraper.scrape_all_categories()

    # Save results to CSV files for testing
    for category, df in results.items():
        filename = f"sctr_{category.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False)
        print(f"Saved {category} data to {filename}")


if __name__ == "__main__":
    main()
