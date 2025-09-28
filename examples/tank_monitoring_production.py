#!/usr/bin/env python3
"""
Production-ready NaviLink Tank Monitor.

This is the main production example for monitoring DHW (Domestic Hot Water) charge levels
and heat pump operation modes. Designed for long-term data collection and analysis.

Features:
- Unified configuration via .env file or environment variables
- Robust error handling and connection recovery
- CSV data logging with configurable intervals
- Comprehensive monitoring statistics
- Production-ready logging and signal handling

Configuration:
    1. Copy .env.template to .env and fill in your credentials
    2. Adjust monitoring settings in .env:
       NAVILINK_POLLING_INTERVAL=300  # 5 minutes (recommended)

Usage:
    # Standard monitoring (5-minute intervals)
    python examples/tank_monitoring_production.py

    # Custom intervals and duration
    python examples/tank_monitoring_production.py --interval 60 --duration 120

    # Debug mode
    python examples/tank_monitoring_production.py --debug
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from navien_nwp500 import NaviLinkClient, NaviLinkConfig, ReconnectConfig
from navien_nwp500.exceptions import DeviceError, DeviceOfflineError, NaviLinkError
from navien_nwp500.models import DeviceStatus

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("tank_monitoring_production.log"),
    ],
)
logger = logging.getLogger(__name__)


class TankMonitor:
    """Production-ready tank monitoring with comprehensive data collection."""

    def __init__(
        self,
        config: NaviLinkConfig,
        output_file: str = "tank_data_production.csv",
        polling_interval: int = 300,
        duration_minutes: Optional[int] = None,
    ):
        """
        Initialize tank monitor.

        Args:
            config: NaviLink configuration
            output_file: CSV file to save data
            polling_interval: Seconds between status checks (default: 300 = 5 minutes)
            duration_minutes: Total monitoring duration in minutes (None = indefinite)
        """
        self.config = config
        self.output_file = output_file
        self.polling_interval = polling_interval
        self.duration_minutes = duration_minutes
        self.start_time = None
        self.stats = {
            "updates_received": 0,
            "connection_errors": 0,
            "device_offline_count": 0,
            "last_update": None,
            "last_error": None,
        }
        self.running = False

        # Setup CSV headers
        self.csv_headers = [
            "timestamp",
            "dhw_charge_per",
            "dhw_temperature",
            "dhw_temperature_setting",
            "operation_mode",
            "current_inst_power",
            "comp_use",
            "heat_upper_use",
            "heat_lower_use",
            "eva_fan_use",
            "error_code",
            "wifi_rssi",
            "operation_busy",
        ]

    async def setup(self):
        """Setup monitoring session."""
        logger.info("🚀 Initializing Production Tank Monitor")
        logger.info(
            f"⏱️ Polling interval: {self.polling_interval} seconds ({self.polling_interval/60:.1f} minutes)"
        )
        if self.duration_minutes:
            logger.info(f"⏰ Duration: {self.duration_minutes} minutes")
        else:
            logger.info("♾️ Duration: indefinite (until interrupted)")

        # Initialize CSV file
        self._initialize_csv()
        logger.info(f"📊 CSV logging initialized: {self.output_file}")

        # Create client and authenticate
        self.client = NaviLinkClient(config=self.config)

        try:
            logger.info("🔐 Authenticating...")
            await self.client.authenticate(self.config.email, self.config.password)
            logger.info("✅ Authentication successful")

            # Get devices
            logger.info("📱 Getting device list...")
            devices = await self.client.get_devices()
            if not devices:
                raise DeviceError("No devices found in account")

            logger.info(f"✅ Found {len(devices)} device(s)")

            # Use first device (typically only one water heater)
            self.device = devices[0]
            logger.info(
                f"🏠 Using device: {self.device.name} (MAC: {self.device.mac_address})"
            )

            return True

        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            raise

    def _initialize_csv(self):
        """Initialize CSV file with headers."""
        try:
            with open(self.output_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(self.csv_headers)
        except Exception as e:
            logger.error(f"Failed to initialize CSV file: {e}")
            raise

    async def _log_data_point(self, status: DeviceStatus):
        """Log a data point to CSV."""
        try:
            timestamp = datetime.now().isoformat()

            # Extract key data points for production monitoring
            data_row = [
                timestamp,
                status.dhw_charge_per,
                status.dhw_temperature,
                status.dhw_temperature_setting,
                status.operation_mode,
                status.current_inst_power,
                status.comp_use,
                status.heat_upper_use,
                status.heat_lower_use,
                status.eva_fan_use,
                status.error_code,
                status.wifi_rssi,
                status.operation_busy,
            ]

            with open(self.output_file, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(data_row)

            self.stats["updates_received"] += 1
            self.stats["last_update"] = timestamp

            # Log key metrics
            logger.info(
                f"📊 Tank: {status.dhw_charge_per}% | Temp: {status.dhw_temperature}°F | "
                f"Mode: {status.operation_mode} | Power: {status.current_inst_power}W"
            )

            # Alert on interesting conditions
            if status.error_code != 0:
                logger.warning(f"⚠️ Error code detected: {status.error_code}")

            if status.dhw_charge_per < 20:
                logger.warning(f"🔋 Low DHW charge: {status.dhw_charge_per}%")

            if status.current_inst_power > 4000:
                logger.warning(
                    f"⚡ High power consumption: {status.current_inst_power}W (electric backup?)"
                )

        except Exception as e:
            logger.error(f"Failed to log data point: {e}")

    async def run_monitoring(self):
        """Run the monitoring loop."""
        self.running = True
        self.start_time = datetime.now()

        logger.info("🚀 Starting monitoring loop...")
        logger.info(
            f"⏱️ Polling interval: {self.polling_interval} seconds ({self.polling_interval/60:.1f} minutes)"
        )
        if self.duration_minutes:
            end_time = self.start_time + timedelta(minutes=self.duration_minutes)
            logger.info(f"⏰ Will run until: {end_time}")
        else:
            logger.info("♾️ Duration: indefinite (until interrupted)")

        try:
            while self.running:
                try:
                    # Check if duration exceeded
                    if self.duration_minutes:
                        elapsed = datetime.now() - self.start_time
                        if elapsed.total_seconds() / 60 >= self.duration_minutes:
                            logger.info("⏰ Duration limit reached, stopping...")
                            break

                    # Get device status (connect automatically if needed)
                    logger.debug("📡 Getting device status...")
                    status = await self.device.get_status(use_cache=False)

                    if status:
                        await self._log_data_point(status)

                        # Log current status
                        logger.info(
                            f"📊 Tank: {status.dhw_charge_per}% | Temp: {status.dhw_temperature}°F | Mode: {status.operation_mode} | Power: {status.current_inst_power}W"
                        )
                    else:
                        logger.warning("⚠️ No status data received")

                    # Wait for next polling interval with cancellation-aware sleep
                    try:
                        logger.debug(
                            f"💤 Sleeping for {self.polling_interval} seconds..."
                        )
                        await asyncio.sleep(self.polling_interval)
                    except asyncio.CancelledError:
                        logger.info("🛑 Sleep interrupted by cancellation")
                        break

                except DeviceOfflineError:
                    self.stats["device_offline_count"] += 1
                    logger.warning("📴 Device is offline, will retry next interval")
                    try:
                        await asyncio.sleep(self.polling_interval)
                    except asyncio.CancelledError:
                        logger.info("🛑 Sleep interrupted by cancellation")
                        break

                except Exception as e:
                    self.stats["connection_errors"] += 1
                    self.stats["last_error"] = str(e)
                    logger.error(f"❌ Error during monitoring: {e}")
                    logger.info("🔄 Will retry next interval...")
                    try:
                        await asyncio.sleep(self.polling_interval)
                    except asyncio.CancelledError:
                        logger.info("🛑 Sleep interrupted by cancellation")
                        break

        except asyncio.CancelledError:
            logger.info("🛑 Monitoring cancelled")
            raise  # Re-raise to properly handle cancellation
        finally:
            self.running = False

    def _log_session_summary(self):
        """Log session summary statistics."""
        if self.start_time:
            runtime = datetime.now() - self.start_time
            logger.info("🏁 Final Session Summary:")
            logger.info(f"   Total Runtime: {runtime}")
            logger.info(f"   Status Updates Received: {self.stats['updates_received']}")
            logger.info(f"   Connection Errors: {self.stats['connection_errors']}")
            logger.info(
                f"   Device Offline Count: {self.stats['device_offline_count']}"
            )
            logger.info(f"   Data saved to: {self.output_file}")

            if self.stats["updates_received"] > 0:
                logger.info(
                    f"   Average Collection Rate: {self.stats['updates_received'] / (runtime.total_seconds() / self.polling_interval):.1%}"
                )

    async def cleanup(self):
        """Cleanup resources with aggressive timeouts."""
        logger.info("🧹 Cleaning up resources...")

        # Disconnect device first with timeout
        if hasattr(self, "device") and self.device:
            try:
                logger.info("📴 Disconnecting device...")
                await asyncio.wait_for(self.device.disconnect(), timeout=3.0)
                logger.info("✅ Device disconnected")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Device disconnect timed out")
            except Exception as e:
                logger.warning(f"⚠️ Error disconnecting device: {e}")

        # Close client session with timeout
        if hasattr(self, "client") and self.client:
            try:
                logger.info("🔒 Closing client session...")
                await asyncio.wait_for(self.client.close(), timeout=3.0)
                logger.info("✅ Client session closed")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Client close timed out")
            except Exception as e:
                logger.warning(f"⚠️ Error closing client: {e}")

        self._log_session_summary()
        logger.info("✅ Cleanup completed")


async def main():
    parser = argparse.ArgumentParser(description="Production NaviLink Tank Monitor")
    parser.add_argument("--email", help="NaviLink account email (overrides env)")
    parser.add_argument("--password", help="NaviLink account password (overrides env)")
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Polling interval in seconds (default: from env or 300)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Duration in minutes (default: indefinite)",
    )
    parser.add_argument(
        "--output",
        default="tank_data_production.csv",
        help="Output CSV file (default: tank_data_production.csv)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    monitor = None
    monitoring_task = None

    # Create shutdown event for proper asyncio integration
    shutdown_event = asyncio.Event()
    shutdown_count = 0

    # Set up signal handling - simplified approach
    def signal_handler(signum=None, frame=None):
        nonlocal shutdown_count
        shutdown_count += 1

        if shutdown_count == 1:
            logger.info("🛑 Shutdown signal received, stopping gracefully...")
            shutdown_event.set()
            # Stop monitor immediately
            if monitor:
                monitor.running = False

        elif shutdown_count == 2:
            logger.info("🛑 Second signal - forcing immediate shutdown...")
            # Cancel monitoring task directly
            if monitoring_task and not monitoring_task.done():
                monitoring_task.cancel()
            # Force exit after brief delay
            asyncio.get_event_loop().call_later(1.0, lambda: os._exit(1))

        else:
            logger.info("🛑 Force exit now!")
            os._exit(1)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Create configuration
        if args.email and args.password:
            config = NaviLinkConfig(email=args.email, password=args.password)
        else:
            config = NaviLinkConfig.from_environment()

        if not config.email or not config.password:
            logger.error("❌ No credentials provided")
            logger.error(
                "Please set NAVILINK_EMAIL and NAVILINK_PASSWORD in .env or use --email/--password"
            )
            return False

        # Determine polling interval
        polling_interval = args.interval
        if polling_interval is None:
            polling_interval = int(os.getenv("NAVILINK_POLLING_INTERVAL", 300))

        # Create and run monitor
        monitor = TankMonitor(
            config=config,
            output_file=args.output,
            polling_interval=polling_interval,
            duration_minutes=args.duration,
        )

        try:
            await monitor.setup()

            # Create monitoring task
            monitoring_task = asyncio.create_task(monitor.run_monitoring())
            shutdown_task = asyncio.create_task(shutdown_event.wait())

            # Wait for either monitoring to complete or shutdown signal
            done, pending = await asyncio.wait(
                [monitoring_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel remaining tasks
            for task in pending:
                if not task.cancelled():
                    task.cancel()

            # Check if shutdown was requested
            if shutdown_task in done:
                logger.info("🛑 Shutdown requested, cancelling monitoring...")
                if not monitoring_task.cancelled():
                    monitoring_task.cancel()

            # Wait briefly for cancellation to complete
            try:
                await asyncio.wait_for(
                    asyncio.gather(*pending, return_exceptions=True), timeout=2.0
                )
            except asyncio.TimeoutError:
                logger.warning("⚠️ Some tasks didn't cancel in time")

            logger.info("🏁 Monitoring completed")
            return True

        except Exception as e:
            logger.error(f"❌ Monitoring session failed: {e}")
            return False
        finally:
            # Always cleanup, but with shorter timeout
            if monitor:
                try:
                    await asyncio.wait_for(monitor.cleanup(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Cleanup timed out")
                except Exception as e:
                    logger.warning(f"⚠️ Cleanup error: {e}")

    except KeyboardInterrupt:
        logger.info("🛑 Monitoring stopped by user")
        return True
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
