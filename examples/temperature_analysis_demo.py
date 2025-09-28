#!/usr/bin/env python3
"""
Temperature Analysis Demo

Demonstrates the two different temperature calibrations in the NaviLink library:

1. DHW Temperature Calibration: +20°F offset for hot water temperatures
2. Ambient Temperature Conversion: Celsius to Fahrenheit conversion

This example shows how the library handles temperature readings from different
sensors that use different units and calibrations.
"""

import asyncio
import logging
from navien_nwp500 import (
    NaviLinkConfig,
    NaviLinkClient,
    calibrate_temperature_from_raw,
    calibrate_temperature_to_raw,
    convert_ambient_temperature,
    convert_celsius_to_fahrenheit,
    TEMPERATURE_CALIBRATION_OFFSET,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demonstrate_temperature_conversions():
    """Show the different temperature conversion functions."""
    
    print("🌡️  NAVIEN TEMPERATURE ANALYSIS DEMO")
    print("=" * 60)
    
    print(f"\n📊 TWO TYPES OF TEMPERATURE CALIBRATION:")
    
    # DHW Temperature Calibration (+20°F offset)
    print(f"\n1️⃣  DHW Temperature Calibration (+{TEMPERATURE_CALIBRATION_OFFSET}°F)")
    print(f"   Purpose: Match app/display values")
    print(f"   Applied to: dhw_temperature, dhw_temperature_setting")
    
    dhw_examples = [(121, 141), (117, 137), (100, 120)]
    print(f"   Examples:")
    for raw, display in dhw_examples:
        converted = calibrate_temperature_from_raw(raw)
        print(f"     Raw {raw}°F → Display {converted}°F")
    
    # Ambient Temperature Conversion (Celsius → Fahrenheit)  
    print(f"\n2️⃣  Ambient Temperature Conversion (°C → °F)")
    print(f"   Purpose: Convert Celsius readings to Fahrenheit")
    print(f"   Applied to: ambient_temperature")
    print(f"   ✅ VALIDATED: Device 21.4°C = 70.5°F ≈ Room thermometer 69.7°F")
    
    ambient_examples = [(21.4, 69.7), (20, 68), (25, 77)]
    print(f"   Examples:")
    for celsius, expected_f in ambient_examples:
        converted = convert_ambient_temperature(celsius)
        print(f"     Raw {celsius}°C → Converted {converted:.1f}°F")
        if celsius == 21.4:
            print(f"       (User thermometer: {expected_f}°F - difference: {abs(converted - expected_f):.1f}°F)")

async def demonstrate_with_real_device():
    """Demonstrate temperature analysis with actual device data."""
    
    print(f"\n" + "=" * 60)
    print(f"🔌 REAL DEVICE TEMPERATURE ANALYSIS")
    print("=" * 60)
    
    try:
        # Load configuration
        config = NaviLinkConfig.from_environment()
        print("✅ Configuration loaded from environment variables")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("💡 Set NAVILINK_EMAIL and NAVILINK_PASSWORD to test with real device")
        return
    
    client = NaviLinkClient(config=config)
    
    try:
        # Authenticate and get device
        print("\n🔐 Authenticating...")
        await client.authenticate()
        
        devices = await client.get_devices()
        if not devices:
            print("❌ No devices found")
            return
            
        device = devices[0]
        print(f"✅ Connected to device: {device.mac_address}")
        
        # Get current status
        print(f"\n📊 Current Temperature Readings:")
        status = await device.get_status()
        
        # DHW Temperatures (calibrated)
        print(f"\n🔥 Hot Water Temperatures (Calibrated +{TEMPERATURE_CALIBRATION_OFFSET}°F):")
        print(f"   Current Temperature:     {status.dhw_temperature}°F")
        print(f"   Temperature Setting:     {status.dhw_temperature_setting}°F")
        print(f"   Target Setting:          {status.dhw_target_temperature_setting}°F")
        
        # Show what the raw values would be
        raw_current = calibrate_temperature_to_raw(status.dhw_temperature)
        raw_setting = calibrate_temperature_to_raw(status.dhw_temperature_setting)
        print(f"\n   Raw API values (before calibration):")
        print(f"     Current: {raw_current}°F, Setting: {raw_setting}°F")
        
        # Ambient Temperature (converted from Celsius)
        print(f"\n🌡️  Ambient Temperature (Converted from °C):")
        print(f"   Room Temperature:        {status.ambient_temperature}°F")
        
        # Show the conversion process
        # Note: We need to reverse-calculate the Celsius value for demonstration
        # In reality, the raw value is directly converted in the parsing
        celsius_estimate = (status.ambient_temperature - 32) * 5/9
        print(f"   Estimated raw value:     {celsius_estimate:.1f}°C")
        print(f"   Converted to Fahrenheit: {status.ambient_temperature}°F")
        
        # Other temperature sensors (0.1°F units)
        print(f"\n❄️  Heat Pump System Temperatures (0.1°F units):")
        print(f"   Cold Water Inlet:        {status.tank_upper_temperature / 10.0:.1f}°F")
        print(f"   Heat Pump Ambient:       {status.tank_lower_temperature / 10.0:.1f}°F") 
        print(f"   Discharge Temperature:   {status.discharge_temperature / 10.0:.1f}°F")
        
        print(f"\n🔍 Temperature Analysis Summary:")
        print(f"   • DHW temperatures show calibrated values matching app/display")
        print(f"   • Ambient temperature converted from Celsius to Fahrenheit")
        print(f"   • Heat pump sensors use 0.1°F units (divide by 10)")
        print(f"   • All conversions happen automatically in the library")
        
    except Exception as e:
        logger.error(f"Device communication error: {e}")
        print(f"❌ Error: {e}")
        
    finally:
        await client.close()

def show_api_usage():
    """Show how to use the temperature conversion functions directly."""
    
    print(f"\n" + "=" * 60)
    print(f"🧮 DIRECT API USAGE EXAMPLES")
    print("=" * 60)
    
    print(f"\n# DHW Temperature Calibration Functions:")
    print(f"from navien_nwp500 import calibrate_temperature_from_raw, calibrate_temperature_to_raw")
    print(f"")
    print(f"# Convert raw API value to display temperature")
    print(f"display_temp = calibrate_temperature_from_raw(121)  # Returns 141")
    print(f"")
    print(f"# Convert display temperature to raw API value")
    print(f"raw_temp = calibrate_temperature_to_raw(141)  # Returns 121")
    
    print(f"\n# Ambient Temperature Conversion Functions:")
    print(f"from navien_nwp500 import convert_ambient_temperature, convert_celsius_to_fahrenheit")
    print(f"")
    print(f"# Convert device Celsius reading to Fahrenheit")
    print(f"fahrenheit = convert_ambient_temperature(21.4)  # Returns 70.5")
    print(f"")
    print(f"# General Celsius to Fahrenheit conversion")
    print(f"fahrenheit = convert_celsius_to_fahrenheit(25.0)  # Returns 77.0")
    
    print(f"\n💡 Key Points:")
    print(f"   • DHW calibration: +20°F offset for hot water temperatures")
    print(f"   • Ambient conversion: Celsius → Fahrenheit for room temperature")
    print(f"   • Both conversions happen automatically when reading device status")
    print(f"   • Use calibration functions for custom applications")

if __name__ == "__main__":
    print("🚀 Starting Temperature Analysis Demo...")
    
    # Show the conversion functions
    demonstrate_temperature_conversions()
    
    # Show API usage examples
    show_api_usage()
    
    # Try to connect to real device if credentials are available
    asyncio.run(demonstrate_with_real_device())