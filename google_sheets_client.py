"""
Google Sheets Client
Handles authentication and data updates for Google Sheets
"""

import os
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd


class GoogleSheetsClient:
    """Client for Google Sheets API operations"""

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    def __init__(self, spreadsheet_id: str, credentials_file: str = 'credentials.json'):
        """
        Initialize Google Sheets client

        Args:
            spreadsheet_id: The ID of the Google Spreadsheet
            credentials_file: Path to credentials JSON file
        """
        self.spreadsheet_id = spreadsheet_id
        self.credentials_file = credentials_file
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authenticate with Google Sheets API"""
        creds = None

        # Token file stores user's access and refresh tokens
        token_file = 'token.json'

        # Check if we have saved credentials
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, self.SCOPES)

        # If credentials don't exist or are invalid
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh the credentials
                creds.refresh(Request())
            else:
                # Check if using service account
                if os.path.exists(self.credentials_file):
                    try:
                        # Try service account first
                        creds = service_account.Credentials.from_service_account_file(
                            self.credentials_file, scopes=self.SCOPES
                        )
                    except Exception as e:
                        print(f"Service account auth failed: {e}")
                        # Fall back to OAuth2 flow
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, self.SCOPES
                        )
                        creds = flow.run_local_server(port=0)

                        # Save credentials for future use
                        with open(token_file, 'w') as token:
                            token.write(creds.to_json())
                else:
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}\n"
                        "Please download credentials from Google Cloud Console"
                    )

        self.service = build('sheets', 'v4', credentials=creds)

    def get_sheet_names(self) -> List[str]:
        """Get all sheet names in the spreadsheet"""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()

            return [sheet['properties']['title'] for sheet in spreadsheet['sheets']]

        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

    def create_sheet(self, sheet_name: str) -> bool:
        """Create a new sheet in the spreadsheet"""
        try:
            request_body = {
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=request_body
            ).execute()

            print(f"Created sheet: {sheet_name}")
            return True

        except HttpError as error:
            if 'already exists' in str(error):
                print(f"Sheet {sheet_name} already exists")
                return True
            print(f"An error occurred: {error}")
            return False

    def clear_sheet(self, sheet_name: str) -> bool:
        """Clear all data from a sheet"""
        try:
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:ZZ"
            ).execute()

            print(f"Cleared sheet: {sheet_name}")
            return True

        except HttpError as error:
            print(f"An error occurred: {error}")
            return False

    def write_data(self, sheet_name: str, data: List[List[Any]],
                   start_cell: str = 'A1', clear_first: bool = True) -> bool:
        """
        Write data to a sheet

        Args:
            sheet_name: Name of the sheet
            data: 2D list of data to write
            start_cell: Starting cell (e.g., 'A1')
            clear_first: Whether to clear the sheet first

        Returns:
            True if successful, False otherwise
        """
        try:
            if clear_first:
                self.clear_sheet(sheet_name)

            body = {
                'values': data
            }

            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!{start_cell}",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()

            print(f"Wrote {len(data)} rows to {sheet_name}")
            return True

        except HttpError as error:
            print(f"An error occurred: {error}")
            return False

    def write_dataframe(self, sheet_name: str, df: pd.DataFrame,
                       include_index: bool = False, clear_first: bool = True) -> bool:
        """
        Write a pandas DataFrame to a sheet

        Args:
            sheet_name: Name of the sheet
            df: DataFrame to write
            include_index: Whether to include the index as a column
            clear_first: Whether to clear the sheet first

        Returns:
            True if successful, False otherwise
        """
        # Convert DataFrame to list of lists
        if include_index:
            data = [df.index.tolist()] + df.reset_index().values.tolist()
        else:
            data = [df.columns.tolist()] + df.values.tolist()

        return self.write_data(sheet_name, data, clear_first=clear_first)

    def append_data(self, sheet_name: str, data: List[List[Any]]) -> bool:
        """
        Append data to the end of a sheet

        Args:
            sheet_name: Name of the sheet
            data: 2D list of data to append

        Returns:
            True if successful, False otherwise
        """
        try:
            body = {
                'values': data
            }

            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:A",
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

            print(f"Appended {len(data)} rows to {sheet_name}")
            return True

        except HttpError as error:
            print(f"An error occurred: {error}")
            return False

    def read_sheet(self, sheet_name: str, range_notation: str = None) -> List[List[Any]]:
        """
        Read data from a sheet

        Args:
            sheet_name: Name of the sheet
            range_notation: Optional range (e.g., 'A1:C10')

        Returns:
            2D list of data
        """
        try:
            if range_notation:
                range_name = f"{sheet_name}!{range_notation}"
            else:
                range_name = sheet_name

            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()

            return result.get('values', [])

        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

    def format_header(self, sheet_name: str) -> bool:
        """Format the header row (bold, frozen)"""
        try:
            # Get sheet ID
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()

            sheet_id = None
            for sheet in spreadsheet['sheets']:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break

            if sheet_id is None:
                print(f"Sheet {sheet_name} not found")
                return False

            requests = [
                # Make header row bold
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'textFormat': {
                                    'bold': True
                                },
                                'backgroundColor': {
                                    'red': 0.9,
                                    'green': 0.9,
                                    'blue': 0.9
                                }
                            }
                        },
                        'fields': 'userEnteredFormat(textFormat,backgroundColor)'
                    }
                },
                # Freeze header row
                {
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet_id,
                            'gridProperties': {
                                'frozenRowCount': 1
                            }
                        },
                        'fields': 'gridProperties.frozenRowCount'
                    }
                }
            ]

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()

            return True

        except HttpError as error:
            print(f"An error occurred: {error}")
            return False


def main():
    """Test the Google Sheets client"""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')
    if not spreadsheet_id:
        print("Please set GOOGLE_SHEETS_ID in .env file")
        return

    client = GoogleSheetsClient(spreadsheet_id)

    # Test: List sheets
    sheets = client.get_sheet_names()
    print(f"Existing sheets: {sheets}")

    # Test: Create a test sheet
    client.create_sheet("Test Sheet")

    # Test: Write some data
    test_data = [
        ["Symbol", "SCTR", "Price"],
        ["AAPL", "95.5", "$150.00"],
        ["GOOGL", "88.2", "$140.00"]
    ]
    client.write_data("Test Sheet", test_data)
    client.format_header("Test Sheet")


if __name__ == "__main__":
    main()
