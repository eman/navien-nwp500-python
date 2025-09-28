#!/usr/bin/env python3
"""
Temperature Calibration Demo

This example demonstrates the temperature calibration feature that adjusts
temperature readings by +20°F to match the values shown on the app and 
water heater display.

The user observed that raw temperature values from the API were 20°F lower
than what appeared on the actual device display and mobile app.
"""

import asyncio
import logging
from navien_nwp500 import (
    NaviLinkConfig,
    NaviLinkClient, 
    calibrate_temperature_from_raw,
    calibrate_temperature_to_raw,
    TEMPERATURE_CALIBRATION_OFFSET,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demonstrate_temperature_calibration():
    """Demonstrate temperature calibration with real device data."""
    
    print("🌡️  NAVIEN TEMPERATURE CALIBRATION DEMO")
    print("=" * 50)
    print(f"📊 Calibration Offset: +{TEMPERATURE_CALIBRATION_OFFSET}°F")
    print(f"🎯 Purpose: Match app/display temperatures with API values\n")
    
    # Load configuration
    try:
        config = NaviLinkConfig.from_environment()
        print("✅ Configuration loaded from environment variables")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("💡 Make sure to set NAVILINK_EMAIL and NAVILINK_PASSWORD")
        return
    
    # Create client
    client = NaviLinkClient(config=config)
    
    try:
        # Authenticate
        print("\n🔐 Authenticating...")
        await client.authenticate()
        print("✅ Authentication successful")
        
        # Get devices
        print("\n📱 Getting devices...")
        devices = await client.get_devices()
        
        if not devices:
            print("❌ No devices found")
            return
            
        device = devices[0]
        print(f"✅ Found device: {device.mac_address}")
        
        # Get current status
        print(f"\n📊 Getting current temperature status...")
        status = await device.get_status()
        
        print(f"\n🌡️  TEMPERATURE READINGS (Calibrated for Display):")
        print(f"   Current Temperature: {status.dhw_temperature}°F")
        print(f"   Temperature Setting: {status.dhw_temperature_setting}°F") 
        print(f"   Target Temperature:  {status.dhw_target_temperature_setting}°F")
        
        # Show raw vs calibrated values
        print(f"\n🔍 RAW API VALUES (Before Calibration):")
        # Simulate what the raw values would be
        raw_current = calibrate_temperature_to_raw(status.dhw_temperature)
        raw_setting = calibrate_temperature_to_raw(status.dhw_temperature_setting)
        raw_target = calibrate_temperature_to_raw(status.dhw_target_temperature_setting)
        
        print(f"   Raw Current Temperature: {raw_current}°F")
        print(f"   Raw Temperature Setting: {raw_setting}°F")
        print(f"   Raw Target Temperature:  {raw_target}°F")
        
        print(f"\n📈 CALIBRATION CONVERSION EXAMPLES:")
        test_raw_values = [70, 100, 121, 131]
        for raw_val in test_raw_values:
            display_val = calibrate_temperature_from_raw(raw_val)
            print(f"   Raw {raw_val}°F → Display {display_val}°F")
        
        # Demonstrate temperature setting
        print(f"\n🎛️  TEMPERATURE SETTING DEMO:")
        current_setting = status.dhw_temperature_setting
        print(f"   Current setting: {current_setting}°F (as shown on app/display)")
        
        # Example: Set temperature to a new value  
        new_display_temp = 145  # What user wants to see on display
        new_raw_temp = calibrate_temperature_to_raw(new_display_temp)
        
        print(f"   Example: To set display temperature to {new_display_temp}°F:")
        print(f"            → Library sends {new_raw_temp}°F to device")
        print(f"            → Device receives {new_raw_temp}°F") 
        print(f"            → App/display shows {new_display_temp}°F")
        
        print(f"\n💡 KEY BENEFITS:")
        print(f"   ✅ Temperature values now match app and physical display")
        print(f"   ✅ No manual conversion needed in user code")
        print(f"   ✅ Transparent calibration - just use normal temperature values")
        print(f"   ✅ Maintains compatibility with device protocol")
        
        print(f"\n📋 TEMPERATURE RANGES:")
        print(f"   Device raw range: 70-131°F")
        print(f"   Display range:    90-151°F (after +{TEMPERATURE_CALIBRATION_OFFSET}°F calibration)")
        print(f"   Safe range:       90-140°F (recommended for water heaters)")
        
        # Show other status information
        print(f"\n🔧 OTHER DEVICE STATUS:")
        print(f"   Operation Mode:    {status.operation_mode}")
        print(f"   Power Consumption: {status.current_inst_power}W")
        print(f"   Tank Charge:       {status.dhw_charge_per}%")
        print(f"   Error Code:        {status.error_code}")
        
    except Exception as e:
        logger.error(f"Demo error: {e}")
        print(f"❌ Demo error: {e}")
        
    finally:
        await client.close()

async def demonstrate_calibration_functions():
    """Show the calibration functions in action."""
    
    print(f"\n🧮 CALIBRATION FUNCTIONS DEMO")
    print("=" * 40)
    
    # Show conversion functions
    print(f"Available functions:")
    print(f"  • calibrate_temperature_from_raw(raw_temp)")
    print(f"  • calibrate_temperature_to_raw(display_temp)")
    print(f"  • TEMPERATURE_CALIBRATION_OFFSET = {TEMPERATURE_CALIBRATION_OFFSET}")
    
    print(f"\nExample usage in your code:")
    print(f"""
    from navien_nwp500 import calibrate_temperature_from_raw, calibrate_temperature_to_raw
    
    # Convert raw device temperature to display temperature
    raw_temp = 121  # From device API
    display_temp = calibrate_temperature_from_raw(raw_temp)
    print(f"Device reports {{raw_temp}}°F → Display shows {{display_temp}}°F")
    
    # Convert display temperature to raw for device commands
    user_wants = 141  # User sets this temperature
    send_to_device = calibrate_temperature_to_raw(user_wants)
    print(f"User sets {{user_wants}}°F → Send {{send_to_device}}°F to device")
    """)

if __name__ == "__main__":
    print("🚀 Starting Temperature Calibration Demo...")
    
    # Run the calibration functions demo first
    asyncio.run(demonstrate_calibration_functions())
    
    # Then try to connect to actual device if credentials are available
    print(f"\n" + "="*60)
    asyncio.run(demonstrate_temperature_calibration())