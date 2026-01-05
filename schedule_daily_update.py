#!/usr/bin/env python3
"""
Daily SCTR Update Scheduler
Runs the SCTR data collection at a specified time each day
"""

import schedule
import time
import subprocess
import logging
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_sctr_update():
    """Run the SCTR update script"""
    logger.info("Starting scheduled SCTR update")

    try:
        result = subprocess.run(
            ['python3', 'run_sctr_update.py'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            logger.info("SCTR update completed successfully")
        else:
            logger.error(f"SCTR update failed with code {result.returncode}")
            logger.error(f"Output: {result.stdout}")
            logger.error(f"Error: {result.stderr}")

    except Exception as e:
        logger.error(f"Error running SCTR update: {e}")


def main():
    """Main scheduler loop"""
    # Schedule the update
    # Default: Run at 6:00 PM EST daily (after market close)
    schedule_time = "18:00"

    logger.info(f"Scheduling SCTR updates for {schedule_time} daily")
    schedule.every().day.at(schedule_time).do(run_sctr_update)

    # Optionally run immediately on startup
    # run_sctr_update()

    logger.info("Scheduler started. Press Ctrl+C to stop.")

    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    main()
