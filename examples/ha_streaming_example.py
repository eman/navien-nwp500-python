#!/usr/bin/env python3
"""
Home Assistant Compatible Real-Time Streaming Example

This example shows how to use the enhanced NavienClient with MQTT streaming
capabilities for real-time monitoring in Home Assistant integrations.

Features:
- Real-time MQTT streaming with automatic data conversion
- Home Assistant compatible data format
- Fallback to REST API polling if MQTT fails
- Simple callback interface for data updates

Configuration:
    Copy .env.template to .env and fill in your credentials

Usage:
    python examples/ha_streaming_example.py
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Any, Dict

from navien_nwp500 import NavienClient, NaviLinkConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class HomeAssistantWaterHeater:
    """
    Example Home Assistant integration class showing real-time monitoring.

    This demonstrates how you might structure a Home Assistant custom component
    using the enhanced NavienClient with MQTT streaming.
    """

    def __init__(self, email: str, password: str):
        """Initialize the water heater integration."""
        self.client = NavienClient(email, password)
        self.current_data: Dict[str, Any] = {}
        self.connected = False
        self.monitoring = False

    async def connect(self) -> bool:
        """Connect and authenticate."""
        try:
            logger.info("🔐 Connecting to NaviLink service...")
            success = await self.client.authenticate()
            if success:
                logger.info("✅ Connected successfully")
                self.connected = True
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False

    async def start_monitoring(self, update_interval: int = 60) -> bool:
        """
        Start real-time monitoring with MQTT streaming.

        Args:
            update_interval: Seconds between updates (default: 60)
        """
        if not self.connected:
            raise Exception("Must connect before starting monitoring")

        try:
            logger.info(
                f"📡 Starting MQTT monitoring (interval: {update_interval}s)..."
            )

            # Start MQTT streaming with callback
            await self.client.start_monitoring(
                callback=self._on_data_update,
                polling_interval=update_interval,
                use_mqtt=True,  # Use MQTT for real-time updates
            )

            self.monitoring = True
            logger.info("✅ Real-time monitoring started")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to start monitoring: {e}")
            logger.info("🔄 Falling back to REST API polling...")

            try:
                # Fallback to REST polling
                await self.client.start_monitoring(
                    callback=self._on_data_update,
                    polling_interval=update_interval,
                    use_mqtt=False,  # Fallback to REST polling
                )
                self.monitoring = True
                logger.info("✅ REST polling monitoring started")
                return True
            except Exception as fallback_error:
                logger.error(f"❌ REST fallback also failed: {fallback_error}")
                return False

    async def stop_monitoring(self):
        """Stop real-time monitoring."""
        if self.monitoring:
            await self.client.stop_monitoring()
            self.monitoring = False
            logger.info("🛑 Monitoring stopped")

    async def _on_data_update(self, ha_data: Dict[str, Any]):
        """
        Handle data updates from the water heater.

        This is where you would update Home Assistant entity states,
        trigger automations, etc.
        """
        self.current_data = ha_data

        # Log key metrics
        logger.info("📊 Water Heater Update:")
        logger.info(
            f"   🌡️ Temperature: {ha_data['water_temperature']}°F (target: {ha_data['set_temperature']}°F)"
        )
        logger.info(f"   🔋 Tank Charge: {ha_data['dhw_charge_percent']}%")
        logger.info(f"   ⚡ Power: {ha_data['power_consumption']}W")
        logger.info(f"   🔧 Mode: {ha_data['operating_mode']}")
        logger.info(f"   🔄 Compressor: {ha_data['compressor_status']}")

        # Check for alerts
        if ha_data["dhw_charge_percent"] < 20:
            logger.warning(f"🔋 LOW TANK CHARGE: {ha_data['dhw_charge_percent']}%")

        if ha_data.get("error_code"):
            logger.warning(f"⚠️ ERROR CODE: {ha_data['error_code']}")

        if ha_data["power_consumption"] > 4000:
            logger.warning(
                f"⚡ HIGH POWER: {ha_data['power_consumption']}W (backup heating?)"
            )

    @property
    def state(self) -> str:
        """Get current state for Home Assistant."""
        if not self.current_data:
            return "unknown"

        mode = self.current_data.get("operating_mode", "unknown")
        if mode == "heat_pump_active":
            return "heating"
        elif mode == "electric_backup":
            return "heating_backup"
        else:
            return "idle"

    @property
    def attributes(self) -> Dict[str, Any]:
        """Get attributes dict for Home Assistant."""
        return self.current_data

    async def set_temperature(self, temperature: float) -> bool:
        """Set target temperature."""
        try:
            result = await self.client.set_temperature(temperature)
            logger.info(f"🌡️ Temperature set to {temperature}°F")
            return result
        except Exception as e:
            logger.error(f"❌ Failed to set temperature: {e}")
            return False

    async def set_mode(self, mode: str) -> bool:
        """Set operation mode."""
        try:
            result = await self.client.set_operation_mode(mode)
            logger.info(f"🔧 Mode set to {mode}")
            return result
        except Exception as e:
            logger.error(f"❌ Failed to set mode: {e}")
            return False

    async def close(self):
        """Close connection and cleanup."""
        await self.stop_monitoring()
        await self.client.close()
        logger.info("👋 Connection closed")


async def main():
    """Example usage of the HA-compatible streaming interface."""
    logger.info("🏠 Home Assistant Real-Time Streaming Example")
    logger.info("=" * 60)

    # Load credentials
    try:
        config = NaviLinkConfig.from_environment()
        if not config.email or not config.password:
            logger.error("❌ No credentials found. Please create .env file with:")
            logger.error("   NAVILINK_EMAIL=your_email@example.com")
            logger.error("   NAVILINK_PASSWORD=your_password")
            return
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        return

    # Create the HA integration instance
    water_heater = HomeAssistantWaterHeater(config.email, config.password)

    try:
        # Connect
        if not await water_heater.connect():
            logger.error("❌ Failed to connect")
            return

        # Start real-time monitoring
        if not await water_heater.start_monitoring(
            update_interval=30
        ):  # 30-second updates
            logger.error("❌ Failed to start monitoring")
            return

        # Let it run for 2 minutes to show real-time updates
        logger.info("⏱️ Monitoring for 2 minutes (press Ctrl+C to stop early)...")
        await asyncio.sleep(120)

        # Example of using the Home Assistant-like interface
        logger.info("\n🏠 Home Assistant Interface Example:")
        logger.info(f"   State: {water_heater.state}")
        logger.info(f"   Attributes: {len(water_heater.attributes)} fields")

        # Example control (commented for safety)
        logger.info("\n🎛️ Control capabilities:")
        logger.info("   - await water_heater.set_temperature(125.0)")
        logger.info("   - await water_heater.set_mode('heat_pump')")

    except KeyboardInterrupt:
        logger.info("\n👋 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error during monitoring: {e}")
    finally:
        await water_heater.close()

    logger.info("✅ Example completed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Example failed: {e}")
        sys.exit(1)
