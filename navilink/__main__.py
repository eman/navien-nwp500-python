"""
Entry point for running navilink as a module.

This allows users to run: python -m navilink --help
"""

import argparse
import asyncio
import logging
import sys
from navilink import NavilinkClient

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Navilink - AWS IoT MQTT WebSocket Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m navilink --version
  python -m navilink --test-import
        """
    )
    
    parser.add_argument(
        "--version", 
        action="store_true",
        help="Show version information"
    )
    
    parser.add_argument(
        "--test-import",
        action="store_true", 
        help="Test that the package can be imported successfully"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    if args.version:
        from navilink import __version__
        print(f"navilink {__version__}")
        return 0
    
    if args.test_import:
        try:
            from navilink import NavilinkClient, NavilinkError, AuthenticationError, ConnectionError
            print("✅ All imports successful!")
            print("Available classes:")
            print("  - NavilinkClient: Main MQTT client")
            print("  - NavilinkError: Base exception class")
            print("  - AuthenticationError: Authentication failures")
            print("  - ConnectionError: Connection failures")
            return 0
        except ImportError as e:
            print(f"❌ Import failed: {e}")
            return 1
    
    # If no specific action, show help
    parser.print_help()
    return 0

if __name__ == "__main__":
    sys.exit(main())