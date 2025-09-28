#!/usr/bin/env python3
"""
Home Assistant Compatible Interface Demonstration

This example shows how to use the new NavienClient interface that's designed
for seamless Home Assistant integration, while demonstrating that the original
production NaviLinkClient continues to work unchanged.

The NavienClient provides:
- Simplified API matching Home Assistant expectations
- All required fields from LIBRARY_RECOMMENDATIONS.md
- Critical dhw_charge_percent field (missing from original recommendations)
- Proper error message formatting for Home Assistant
- Full async context manager support

Configuration:
    Copy .env.template to .env and fill in your credentials

Usage:
    python examples/ha_compat_demo.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Import both interfaces to show compatibility
from navien_nwp500 import NavienClient  # New Home Assistant compatible interface
from navien_nwp500 import (  # Original production interface
    NaviLinkClient,
    NaviLinkConfig,
)
from navien_nwp500.exceptions import NaviLinkError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def demo_original_interface():
    """Demonstrate that the original NaviLinkClient interface still works."""
    logger.info("🔧 Testing Original NaviLinkClient Interface (unchanged)")

    try:
        # Load configuration from environment
        config = NaviLinkConfig.from_environment()

        if not config.email or not config.password:
            logger.warning(
                "⚠️ No credentials configured - skipping original interface demo"
            )
            return

        # Use the original production interface
        async with NaviLinkClient(config=config) as client:
            await client.authenticate(config.email, config.password)
            logger.info("✅ Original interface: Authentication successful")

            devices = await client.get_devices()
            logger.info(f"✅ Original interface: Found {len(devices)} device(s)")

            if devices:
                device = devices[0]
                status = await device.get_status()
                if status:
                    logger.info(
                        f"✅ Original interface: DHW Charge: {status.dhw_charge_per}%"
                    )
                    logger.info(
                        f"✅ Original interface: Temperature: {status.dhw_temperature}°F"
                    )
                    logger.info(
                        f"✅ Original interface: Power: {status.current_inst_power}W"
                    )

    except NaviLinkError as e:
        logger.error(f"❌ Original interface error: {e}")
    except Exception as e:
        logger.error(f"❌ Original interface unexpected error: {e}")


async def demo_home_assistant_interface():
    """Demonstrate the new Home Assistant compatible interface."""
    logger.info("\n🏠 Testing Home Assistant Compatible NavienClient Interface")

    try:
        # Load configuration for demo
        config = NaviLinkConfig.from_environment()

        if not config.email or not config.password:
            logger.warning("⚠️ No credentials configured - skipping HA interface demo")
            return

        # Use the new Home Assistant compatible interface
        async with NavienClient(config.email, config.password) as client:
            # Step 1: Authentication
            logger.info("🔐 Authenticating with Home Assistant interface...")
            success = await client.authenticate()
            if success:
                logger.info("✅ HA interface: Authentication successful")

            # Step 2: Get device data in Home Assistant format
            logger.info("📊 Getting device data in Home Assistant format...")
            device_data = await client.get_device_data()

            # Display key Home Assistant fields
            logger.info("📋 Home Assistant Compatible Data:")
            logger.info(f"   Water Temperature: {device_data['water_temperature']}°F")
            logger.info(f"   Set Temperature: {device_data['set_temperature']}°F")
            logger.info(f"   Power Consumption: {device_data['power_consumption']}W")
            logger.info(f"   Operation Mode: {device_data['operating_mode']}")
            logger.info(f"   Compressor Status: {device_data['compressor_status']}")
            logger.info(f"   Heater Status: {device_data['heating_element_status']}")

            # CRITICAL: DHW Charge Percent (missing from original recommendations)
            logger.info(f"   🔋 DHW Charge Level: {device_data['dhw_charge_percent']}%")
            
            # Energy Capacity Data (new fields)
            logger.info(f"   ⚡ Total Energy Capacity: {device_data['total_energy_capacity']}")
            logger.info(f"   ⚡ Available Energy Capacity: {device_data['available_energy_capacity']}")
            
            # Calculate energy utilization
            total_capacity = device_data['total_energy_capacity']
            available_capacity = device_data['available_energy_capacity']
            used_capacity = total_capacity - available_capacity
            utilization_percent = (used_capacity / total_capacity) * 100 if total_capacity > 0 else 0
            logger.info(f"   📊 Energy Utilization: {utilization_percent:.1f}%")

            # Additional useful fields
            if device_data.get("error_code"):
                logger.warning(f"   ⚠️ Error Code: {device_data['error_code']}")
            else:
                logger.info("   ✅ No errors detected")

            logger.info(
                f"   📶 WiFi Signal: {device_data.get('wifi_signal_strength', 'N/A')} dBm"
            )

            # Show raw data structure for Home Assistant developers
            logger.info(
                f"\n📄 Complete Home Assistant Data Structure ({len(device_data)} fields):"
            )
            formatted_data = json.dumps(device_data, indent=2, default=str)
            logger.info(formatted_data)

            # Step 3: Demonstrate MQTT streaming capabilities (NEW!)
            logger.info("\n🔴 MQTT Real-time Monitoring Available (NEW!):")
            logger.info("   - start_monitoring(callback, interval) # MQTT streaming")
            logger.info("   - stop_monitoring() # Stop real-time updates")
            logger.info("   - Automatic data conversion to HA format")

            # Demonstrate streaming if enabled
            enable_streaming_demo = True  # Set to True to test streaming
            if enable_streaming_demo:
                logger.info("📡 Starting 30-second MQTT streaming demo...")

                update_count = 0

                async def stream_callback(ha_data):
                    nonlocal update_count
                    update_count += 1
                    logger.info(f"📊 Stream Update #{update_count}:")
                    logger.info(
                        f"   Tank: {ha_data['dhw_charge_percent']}% | Temp: {ha_data['water_temperature']}°F | Power: {ha_data['power_consumption']}W"
                    )

                try:
                    # Start MQTT streaming with 10-second updates
                    await client.start_monitoring(
                        callback=stream_callback, polling_interval=10, use_mqtt=True
                    )

                    # Let it run for 30 seconds
                    await asyncio.sleep(30)

                    # Stop monitoring
                    await client.stop_monitoring()
                    logger.info(
                        f"✅ MQTT streaming demo completed ({update_count} updates received)"
                    )

                except Exception as e:
                    logger.warning(
                        f"⚠️ MQTT streaming demo failed (may fallback to REST): {e}"
                    )
            else:
                logger.info(
                    "   (Streaming demo disabled - set enable_streaming_demo=True)"
                )

            # Step 4: Demonstrate control capabilities (commented out for safety)
            logger.info("\n🎛️ Control Capabilities Available:")
            logger.info("   - set_temperature(125.0) # Set target temperature")
            logger.info("   - set_operation_mode('heat_pump') # Heat pump only")
            logger.info("   - set_operation_mode('hybrid') # Heat pump + electric")
            logger.info("   - set_operation_mode('electric') # Electric only")
            logger.info("   - set_operation_mode('energy_saver') # Energy saver mode")
            logger.info("   - set_operation_mode('high_demand') # High demand mode")

            # Demonstrate temperature setting (with user confirmation)
            current_temp = device_data["set_temperature"]
            logger.info(f"\n🌡️ Current target temperature: {current_temp}°F")

            # Only demonstrate control if explicitly enabled
            enable_control_demo = False  # Set to True to test actual control
            if enable_control_demo:
                logger.info("🎯 Demonstrating temperature control...")
                try:
                    # Set temperature to current + 1 degree (minimal change)
                    new_temp = current_temp + 1
                    if 100 <= new_temp <= 140:  # Safety check
                        success = await client.set_temperature(new_temp)
                        if success:
                            logger.info(f"✅ Temperature set to {new_temp}°F")

                            # Reset to original temperature
                            await asyncio.sleep(2)
                            success = await client.set_temperature(current_temp)
                            if success:
                                logger.info(f"🔄 Temperature reset to {current_temp}°F")
                    else:
                        logger.warning(f"⚠️ Temperature {new_temp}°F outside safe range")

                except Exception as e:
                    logger.error(f"❌ Control demo failed: {e}")
            else:
                logger.info(
                    "   (Control demo disabled - set enable_control_demo=True to test)"
                )

    except Exception as e:
        logger.error(f"❌ HA interface error: {e}")
        # Note: Exception messages contain "authentication" keyword for HA compatibility


async def demo_field_compatibility():
    """Demonstrate field mapping compatibility with Home Assistant recommendations."""
    logger.info("\n🔄 Field Mapping Compatibility Check")

    config = NaviLinkConfig.from_environment()
    if not config.email or not config.password:
        logger.warning("⚠️ No credentials configured - skipping compatibility demo")
        return

    try:
        async with NavienClient(config.email, config.password) as client:
            await client.authenticate()
            device_data = await client.get_device_data()

            logger.info("📋 Checking LIBRARY_RECOMMENDATIONS.md field requirements:")

            # Temperature fields (from recommendations)
            temp_fields = {
                "water_temperature": "Current water temperature",
                "set_temperature": "Target temperature",
                "target_temp": "Target temperature (alias)",
                "tank_temp": "Tank temperature",
                "inlet_temperature": "Cold water inlet temperature",
                "outlet_temperature": "Hot water outlet temperature",
                "ambient_temperature": "Ambient air temperature",
            }

            for field, description in temp_fields.items():
                if field in device_data:
                    logger.info(
                        f"   ✅ {field}: {device_data[field]}°F ({description})"
                    )
                else:
                    logger.error(f"   ❌ MISSING: {field}")

            # Power fields (from recommendations)
            power_fields = {
                "power_consumption": "Current power usage",
                "current_power": "Current power (alias)",
                "power": "Power (alias)",
            }

            for field, description in power_fields.items():
                if field in device_data:
                    logger.info(f"   ✅ {field}: {device_data[field]}W ({description})")
                else:
                    logger.error(f"   ❌ MISSING: {field}")
            
            # Energy Capacity fields (new)
            energy_fields = {
                "total_energy_capacity": "Total thermal energy capacity",
                "available_energy_capacity": "Available thermal energy capacity",
            }
            
            for field, description in energy_fields.items():
                if field in device_data:
                    logger.info(f"   ✅ {field}: {device_data[field]} ({description})")
                else:
                    logger.error(f"   ❌ MISSING: {field}")

            # Status fields (from recommendations)
            status_fields = {
                "operating_mode": "Current operation mode",
                "mode": "Operation mode (alias)",
                "operation_mode": "Operation mode (alias)",
                "error_code": "Error code if any",
                "error": "Error (alias)",
                "fault_code": "Fault code (alias)",
                "compressor_status": "Compressor state",
                "compressor": "Compressor (alias)",
                "heating_element_status": "Backup heater state",
                "heater": "Heater (alias)",
            }

            for field, description in status_fields.items():
                if field in device_data:
                    value = device_data[field]
                    logger.info(f"   ✅ {field}: {value} ({description})")
                else:
                    logger.error(f"   ❌ MISSING: {field}")

            # CRITICAL: DHW charge percent (missing from original recommendations)
            critical_fields = {
                "dhw_charge_percent": "DHW tank charge percentage (CRITICAL)",
                "tank_charge_percent": "Tank charge percent (alias)",
                "charge_level": "Charge level (alias)",
            }

            logger.info("\n🔋 Critical Fields (missing from original recommendations):")
            for field, description in critical_fields.items():
                if field in device_data:
                    logger.info(f"   ✅ {field}: {device_data[field]}% ({description})")
                else:
                    logger.error(f"   ❌ MISSING CRITICAL FIELD: {field}")

            # Summary
            total_fields = (
                len(temp_fields)
                + len(power_fields)
                + len(status_fields)
                + len(critical_fields)
            )
            present_fields = sum(
                1
                for field in {
                    **temp_fields,
                    **power_fields,
                    **status_fields,
                    **critical_fields,
                }
                if field in device_data
            )

            logger.info(
                f"\n📊 Compatibility Summary: {present_fields}/{total_fields} required fields present"
            )
            if present_fields == total_fields:
                logger.info(
                    "✅ FULL COMPATIBILITY: All Home Assistant fields available"
                )
            else:
                logger.warning(
                    f"⚠️ PARTIAL COMPATIBILITY: {total_fields - present_fields} fields missing"
                )

    except Exception as e:
        logger.error(f"❌ Compatibility check failed: {e}")


async def main():
    """Main demonstration function."""
    logger.info("🚀 NaviLink Library Home Assistant Compatibility Demonstration")
    logger.info("=" * 80)

    logger.info("This demo shows:")
    logger.info("1. Original NaviLinkClient interface continues to work unchanged")
    logger.info("2. New NavienClient provides Home Assistant compatible interface")
    logger.info(
        "3. MQTT real-time streaming with automatic HA format conversion (NEW!)"
    )
    logger.info(
        "4. All required fields including critical dhw_charge_percent are available"
    )
    logger.info("5. Command-line examples continue to function normally")
    logger.info("\n" + "=" * 80)

    # Demonstrate both interfaces work
    await demo_original_interface()
    await demo_home_assistant_interface()
    await demo_field_compatibility()

    logger.info("\n" + "=" * 80)
    logger.info("🎉 Demo completed successfully!")
    logger.info("\nFor Home Assistant Integration:")
    logger.info("- Use: from navien_nwp500 import NavienClient")
    logger.info("- Interface matches LIBRARY_RECOMMENDATIONS.md requirements")
    logger.info("- Includes critical dhw_charge_percent field")
    logger.info("- Proper async support with context managers")
    logger.info("\nFor Direct Library Use:")
    logger.info("- Use: from navien_nwp500 import NaviLinkClient")
    logger.info("- Full features unchanged")
    logger.info("- Advanced MQTT capabilities available")
    logger.info("- Enterprise configuration support")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        sys.exit(1)
