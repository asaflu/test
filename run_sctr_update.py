#!/usr/bin/env python3
"""
SCTR Update Runner
Simple script to run the SCTR data collection and Google Sheets update
"""

import sys
import logging
from datetime import datetime
from sctr_manager import SCTRManager
import os
from dotenv import load_dotenv


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'sctr_update_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main execution"""
    logger.info("="*80)
    logger.info("SCTR Data Update Started")
    logger.info("="*80)

    # Load environment variables
    load_dotenv()

    spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')
    if not spreadsheet_id:
        logger.error("GOOGLE_SHEETS_ID not set in environment")
        logger.error("Please create a .env file with GOOGLE_SHEETS_ID=your_spreadsheet_id")
        return 1

    try:
        # Create and run manager
        manager = SCTRManager(spreadsheet_id)
        success = manager.run()

        if success:
            logger.info("SCTR update completed successfully")
            return 0
        else:
            logger.error("SCTR update failed")
            return 1

    except KeyboardInterrupt:
        logger.warning("Update interrupted by user")
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

    finally:
        logger.info("="*80)
        logger.info("SCTR Data Update Finished")
        logger.info("="*80)


if __name__ == "__main__":
    sys.exit(main())
