#!/usr/bin/env python3
"""
Quick Control Test

Test the new control functionality with a real device.
"""

import asyncio
import logging

from navien_nwp500 import NaviLinkClient, NaviLinkConfig
from navien_nwp500.exceptions import NaviLinkError


async def test_control():
    """Test device control functionality."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        config = NaviLinkConfig.from_environment()

        if not config.email or not config.password:
            print("❌ Please configure credentials in .env file")
            return

        print("🔐 Authenticating...")
        client = NaviLinkClient(config=config)
        await client.authenticate(config.email, config.password)
        print("✅ Authentication successful")

        print("📱 Getting devices...")
        devices = await client.get_devices()
        if not devices:
            print("❌ No devices found")
            return

        device = devices[0]
        print(f"🏠 Using device: {device.name} (MAC: {device.mac_address})")

        # Check connectivity
        connectivity = await device.get_connectivity_status()
        if not connectivity.get("device_connected"):
            print("⚠️ WARNING: Device appears offline")
        else:
            print("✅ Device is online")

        # Get current status
        print("\n📊 Current Status:")
        try:
            status = await device.get_status()
            print(f"   DHW Charge: {status.dhw_charge_per}%")
            print(f"   Temperature: {status.dhw_temperature}°F")
            print(f"   Target Temp: {status.dhw_temperature_setting}°F")
            print(f"   Operation Mode: {status.operation_mode}")
            print(f"   Power: {status.current_inst_power}W")
        except Exception as e:
            print(f"   ❌ Status error: {e}")

        # Test control methods (be careful!)
        print("\n🎛️ Testing Control Methods:")

        # Test DHW mode validation (should work without sending)
        try:
            print("   Testing DHW mode validation...")
            # This should raise an error for invalid mode
            try:
                await device.set_dhw_mode(99)  # Invalid mode
                print("   ❌ Validation failed - should have rejected mode 99")
            except ValueError as e:
                print(f"   ✅ Validation working: {e}")
        except Exception as e:
            print(f"   ⚠️ Validation test error: {e}")

        # Test temperature validation (should work without sending)
        try:
            print("   Testing temperature validation...")
            try:
                await device.set_temperature(200)  # Out of range
                print("   ❌ Validation failed - should have rejected 200°F")
            except ValueError as e:
                print(f"   ✅ Validation working: {e}")
        except Exception as e:
            print(f"   ⚠️ Temperature validation test error: {e}")

        print("\n✅ Control functionality tests complete")
        print("💡 Use device_control_demo.py for interactive control testing")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if "client" in locals():
            await client.close()


if __name__ == "__main__":
    asyncio.run(test_control())
