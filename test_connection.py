#!/usr/bin/env python3
"""
Test Google Sheets connection
Simple script to verify credentials and sheet access
"""

import os
from dotenv import load_dotenv
from google_sheets_client import GoogleSheetsClient

def main():
    print("="*60)
    print("Testing Google Sheets Connection")
    print("="*60)

    # Load environment
    load_dotenv()
    spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')

    if not spreadsheet_id:
        print("❌ ERROR: GOOGLE_SHEETS_ID not found in .env")
        return False

    print(f"✓ Spreadsheet ID: {spreadsheet_id}")

    try:
        print("\n🔐 Authenticating with Google...")
        print("   (A browser window may open for authentication)")

        client = GoogleSheetsClient(spreadsheet_id)

        print("✓ Authentication successful!")

        print("\n📋 Reading existing sheets...")
        sheets = client.get_sheet_names()

        if sheets:
            print(f"✓ Found {len(sheets)} existing sheets:")
            for sheet in sheets:
                print(f"   - {sheet}")
        else:
            print("   No existing sheets (this is normal for a new spreadsheet)")

        print("\n🧪 Testing write access...")
        test_sheet = "Connection_Test"

        # Create test sheet
        client.create_sheet(test_sheet)

        # Write test data
        test_data = [
            ["Test", "Status", "Timestamp"],
            ["Connection", "✓ Success", "2026-01-05"]
        ]
        client.write_data(test_sheet, test_data)
        client.format_header(test_sheet)

        print(f"✓ Successfully created and wrote to '{test_sheet}' sheet")

        print("\n" + "="*60)
        print("✅ All tests passed! You're ready to run the full update.")
        print("="*60)
        print("\nNext steps:")
        print("  python3 run_sctr_update.py")

        return True

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        print("\nMake sure credentials.json exists in the current directory")
        return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
