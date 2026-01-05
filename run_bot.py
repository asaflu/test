#!/usr/bin/env python3
"""
Startup script for the Trading Bot
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main
import asyncio


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    Trading Bot - @ultrawavetrader Copy Trader                  ║
║                                                                               ║
║  This bot monitors @ultrawavetrader on X.com and automatically copies trades  ║
║  to your IBKR account at 10% of the original size.                           ║
║                                                                               ║
║  Features:                                                                    ║
║  • Real-time tweet monitoring (no API key needed)                            ║
║  • Hebrew text parsing for trade signals                                     ║
║  • Automatic position sizing (10% of original)                               ║
║  • Partial sell support (רבע, חצי, etc.)                                     ║
║  • IBKR TWS integration                                                      ║
║  • Dry-run mode for testing                                                  ║
║                                                                               ║
║  Press Ctrl+C to stop                                                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nBot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)
