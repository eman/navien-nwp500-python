#!/usr/bin/env python3
"""
Basic usage example for NaviLink library.

This example demonstrates basic authentication, device discovery, and status retrieval.
Perfect for getting started with the library.

Configuration:
    1. Copy .env.template to .env and fill in your credentials (recommended)
    2. Or set environment variables:
       export NAVILINK_EMAIL="user@example.com"
       export NAVILINK_PASSWORD="password"
    3. Or use command line arguments (see --help)

Usage:
    # Using .env file (recommended)
    python examples/basic_usage.py

    # Using command line
    python examples/basic_usage.py --email user@example.com --password yourpassword
"""

import asyncio
import logging
import argparse
import sys
from pathlib import Path

from navien_nwp500 import NaviLinkClient, NaviLinkConfig
from navien_nwp500.exceptions import NaviLinkError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main function demonstrating basic NaviLink usage."""
    parser = argparse.ArgumentParser(
        description="NaviLink Basic Usage Example"
    )
    parser.add_argument("--email", help="NaviLink account email")
    parser.add_argument("--password", help="NaviLink account password")
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Create configuration from environment (including .env file) or command line
        if args.email and args.password:
            config = NaviLinkConfig(email=args.email, password=args.password)
            logger.info("Using credentials from command line")
        else:
            config = NaviLinkConfig.from_environment()
            if config.email and config.password:
                logger.info("Using credentials from environment/.env file")
            else:
                logger.error("❌ No credentials provided")
                logger.error("Please either:")
                logger.error(
                    "  1. Copy .env.template to .env and fill in your credentials"
                )
                logger.error(
                    "  2. Set NAVILINK_EMAIL and NAVILINK_PASSWORD environment variables"
                )
                logger.error(
                    "  3. Use --email and --password command line arguments"
                )
                return False

        # Validate configuration
        config.validate()

        # Create client and authenticate
        async with NaviLinkClient(config=config) as client:
            logger.info("🔐 Authenticating...")
            await client.authenticate(config.email, config.password)
            logger.info("✅ Authentication successful")

            # Get devices
            logger.info("📱 Getting device list...")
            devices = await client.get_devices()
            logger.info(f"✅ Found {len(devices)} device(s)")

            # Display device information
            for i, device in enumerate(devices):
                logger.info(f"\n📊 Device {i+1}:")
                logger.info(f"   Name: {device.name}")
                logger.info(f"   Model: {device.model}")
                logger.info(f"   MAC Address: {device.mac_address}")
                logger.info(f"   Type: {device.device_type}")

                # Get device status via REST API
                try:
                    logger.info("📊 Getting device status...")
                    status = await device.get_status()
                    if status:
                        logger.info("✅ Device status retrieved successfully")
                        logger.info(f"   DHW Charge: {status.dhw_charge_per}%")
                        logger.info(
                            f"   DHW Temperature: {status.dhw_temperature}°F"
                        )
                        logger.info(
                            f"   Target Temperature: {status.dhw_temperature_setting}°F"
                        )
                        logger.info(
                            f"   Operation Mode: {status.operation_mode}"
                        )
                        logger.info(
                            f"   Power Consumption: {status.current_inst_power}W"
                        )
                        logger.info(f"   Error Code: {status.error_code}")

                        # Interpret operation mode
                        if status.operation_mode == 0:
                            mode_desc = "Standby/Off"
                        elif status.operation_mode == 32:
                            mode_desc = "Heat Pump Active"
                        elif status.operation_mode in [33, 34]:
                            mode_desc = "Electric Backup"
                        else:
                            mode_desc = f"Unknown Mode {status.operation_mode}"

                        logger.info(f"   System Status: {mode_desc}")

                        # Power efficiency note
                        if status.current_inst_power > 4000:
                            logger.warning(
                                "⚠️ High power usage - electric backup heating active"
                            )
                        elif status.current_inst_power > 400:
                            logger.info("♻️ Heat pump operating efficiently")
                        else:
                            logger.info("🔹 System in standby mode")
                    else:
                        logger.warning("⚠️ No status data available")

                except Exception as e:
                    logger.error(f"❌ Failed to get device status: {e}")

                # Check device connectivity
                try:
                    logger.info("🌐 Checking device connectivity...")
                    connectivity = await device.get_connectivity_status()
                    if connectivity:
                        connected = connectivity.get("device_connected", 0)
                        logger.info(
                            f"   Device Connected: {'✅ Yes' if connected else '❌ No'}"
                        )
                        if not connected:
                            logger.warning(
                                "   ⚠️ Device offline - MQTT monitoring not available"
                            )
                    else:
                        logger.warning("   ⚠️ Connectivity status unavailable")

                except Exception as e:
                    logger.warning(f"⚠️ Could not check connectivity: {e}")

            logger.info("\n🎉 Basic usage example completed successfully!")
            return True

    except NaviLinkError as e:
        logger.error(f"❌ NaviLink error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
