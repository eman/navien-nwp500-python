#!/usr/bin/env python3
"""
NaviLink Device Control Demonstration

This example demonstrates the control capabilities of the NaviLink library,
showing how to change DHW modes, set temperatures, and manage the water heater.

Based on HAR analysis, the following control commands are supported:
- DHW Mode Control (command: 33554437)
- Temperature Setting (command: 33554438 - estimated)

Configuration:
    Copy .env.template to .env and configure your credentials

Usage:
    python examples/device_control_demo.py
    
Safety Note:
    This demo includes ACTUAL device control. Use with caution on production systems.
    Consider testing on a development system first.
"""

import asyncio
import logging
import sys
from datetime import datetime

from navilink import NaviLinkClient, NaviLinkConfig
from navilink.exceptions import NaviLinkError, DeviceError


# DHW Mode constants for clarity
DHW_MODES = {
    2: "Heat Pump Only (Eco)",
    3: "Hybrid (HP + Electric)", 
    4: "Electric Only",
    5: "Energy Saver",
    6: "High Demand"
}


class DeviceControlDemo:
    """Demonstrates NaviLink device control capabilities."""
    
    def __init__(self, config: NaviLinkConfig):
        self.config = config
        self.client = None
        self.device = None
        
    async def __aenter__(self):
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
        
    async def initialize(self):
        """Initialize client and device."""
        print("🔐 Authenticating with NaviLink...")
        self.client = NaviLinkClient(config=self.config)
        await self.client.authenticate(self.config.email, self.config.password)
        print("✅ Authentication successful")
        
        print("📱 Getting devices...")
        devices = await self.client.get_devices()
        if not devices:
            raise DeviceError("No devices found")
            
        self.device = devices[0]
        print(f"🏠 Using device: {self.device.name} (MAC: {self.device.mac_address})")
        
        # Check connectivity
        connectivity = await self.device.get_connectivity_status()
        if not connectivity.get('device_connected'):
            print("⚠️ WARNING: Device appears offline. Control may not work.")
        else:
            print("✅ Device is online and ready for control")
            
    async def get_current_status(self):
        """Get and display current device status."""
        print("\n📊 Current Device Status:")
        try:
            status = await self.device.get_status()
            
            print(f"   Tank Charge: {status.dhw_charge_per}%")
            print(f"   Current Temperature: {status.dhw_temperature}°F")
            print(f"   Target Temperature: {status.dhw_temperature_setting}°F")
            print(f"   Operation Mode: {status.operation_mode}")
            print(f"   Power Consumption: {status.current_inst_power}W")
            print(f"   Error Code: {status.error_code}")
            
            # Determine current state
            if status.current_inst_power <= 10:
                state = "Standby"
            elif status.current_inst_power < 500:
                state = "Heat Pump Active"
            elif status.current_inst_power > 3000:
                state = "Electric Heating Active"
            else:
                state = "Active (Unknown Mode)"
                
            print(f"   Current State: {state}")
            
            return status
            
        except Exception as e:
            print(f"❌ Failed to get status: {e}")
            return None
            
    async def demonstrate_dhw_mode_control(self):
        """Demonstrate DHW mode changes."""
        print("\n🎛️ DHW Mode Control Demonstration")
        print("=" * 50)
        
        # Get current status first
        original_status = await self.get_current_status()
        if not original_status:
            return
            
        original_mode = original_status.operation_mode
        print(f"\n📋 Current DHW Mode: {original_mode}")
        
        # Show available modes
        print("\n🔧 Available DHW Modes:")
        for mode, description in DHW_MODES.items():
            print(f"   {mode}: {description}")
            
        # Interactive mode selection
        print("\n" + "⚠️ CAUTION: This will change your water heater settings! ⚠️".center(60))
        
        while True:
            try:
                response = input("\nEnter new DHW mode (2-6) or 'skip' to skip: ").strip().lower()
                
                if response == 'skip':
                    print("⏭️ Skipping DHW mode control demo")
                    return
                    
                new_mode = int(response)
                if new_mode not in DHW_MODES:
                    print("❌ Invalid mode. Please enter 2-6.")
                    continue
                    
                break
                
            except ValueError:
                print("❌ Please enter a valid number or 'skip'")
                continue
                
        # Confirm the change
        print(f"\n🔄 Changing DHW mode from {original_mode} to {new_mode} ({DHW_MODES[new_mode]})")
        confirm = input("Type 'yes' to confirm: ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Mode change cancelled")
            return
            
        try:
            # Send the control command
            print(f"📤 Sending DHW mode control command...")
            result = await self.device.set_dhw_mode(new_mode)
            
            print(f"✅ DHW mode change command sent successfully!")
            print(f"📋 Response: {result}")
            
            # Wait a moment for the change to take effect
            print("⏳ Waiting 10 seconds for mode change to take effect...")
            await asyncio.sleep(10)
            
            # Check new status
            new_status = await self.get_current_status()
            if new_status and new_status.operation_mode == new_mode:
                print(f"✅ Mode change confirmed! New mode: {new_mode}")
            else:
                print(f"⚠️ Mode change may not have taken effect yet. Current mode: {new_status.operation_mode if new_status else 'Unknown'}")
                
        except Exception as e:
            print(f"❌ DHW mode change failed: {e}")
            
    async def demonstrate_temperature_control(self):
        """Demonstrate temperature setting."""
        print("\n🌡️ Temperature Control Demonstration")
        print("=" * 50)
        
        # Get current status
        original_status = await self.get_current_status()
        if not original_status:
            return
            
        original_temp = original_status.dhw_temperature_setting
        print(f"\n📋 Current Target Temperature: {original_temp}°F")
        print("📋 Valid Range: 70-131°F")
        
        print("\n" + "⚠️ CAUTION: This will change your water heater temperature! ⚠️".center(60))
        
        while True:
            try:
                response = input(f"\nEnter new temperature (70-131°F) or 'skip' to skip: ").strip().lower()
                
                if response == 'skip':
                    print("⏭️ Skipping temperature control demo")
                    return
                    
                new_temp = int(response)
                if not 70 <= new_temp <= 131:
                    print("❌ Temperature must be between 70-131°F")
                    continue
                    
                break
                
            except ValueError:
                print("❌ Please enter a valid temperature or 'skip'")
                continue
                
        # Confirm the change
        print(f"\n🔄 Changing temperature from {original_temp}°F to {new_temp}°F")
        confirm = input("Type 'yes' to confirm: ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Temperature change cancelled")
            return
            
        try:
            # Send the control command
            print(f"📤 Sending temperature control command...")
            result = await self.device.set_temperature(new_temp)
            
            print(f"✅ Temperature change command sent successfully!")
            print(f"📋 Response: {result}")
            
            # Wait for change to take effect
            print("⏳ Waiting 10 seconds for temperature change to take effect...")
            await asyncio.sleep(10)
            
            # Check new status
            new_status = await self.get_current_status()
            if new_status and new_status.dhw_temperature_setting == new_temp:
                print(f"✅ Temperature change confirmed! New target: {new_temp}°F")
            else:
                print(f"⚠️ Temperature change may not have taken effect yet. Current target: {new_status.dhw_temperature_setting if new_status else 'Unknown'}°F")
                
        except Exception as e:
            print(f"❌ Temperature change failed: {e}")
            
    async def demonstrate_convenience_methods(self):
        """Demonstrate turn_on/turn_off convenience methods."""
        print("\n🔌 Convenience Control Methods")
        print("=" * 50)
        
        print("These methods provide easy on/off control:")
        print("• turn_on(): Sets device to Hybrid mode (efficient)")
        print("• turn_off(): Sets device to Energy Saver mode")
        
        choice = input("\nDemonstrate turn_on() method? (yes/no): ").strip().lower()
        if choice == 'yes':
            try:
                print("🔄 Calling turn_on()...")
                result = await self.device.turn_on()
                print(f"✅ Turn on successful: {result}")
            except Exception as e:
                print(f"❌ Turn on failed: {e}")
                
        choice = input("\nDemonstrate turn_off() method? (yes/no): ").strip().lower()
        if choice == 'yes':
            try:
                print("🔄 Calling turn_off()...")
                result = await self.device.turn_off()
                print(f"✅ Turn off successful: {result}")
            except Exception as e:
                print(f"❌ Turn off failed: {e}")
                
    async def run_demo(self):
        """Run the complete control demonstration."""
        print("🎯 NaviLink Device Control Demonstration")
        print("=" * 60)
        print("This demo shows how to control your NaviLink water heater.")
        print("All control commands are based on real protocol analysis.")
        print("")
        
        # Initial status check
        await self.get_current_status()
        
        # Run control demonstrations
        await self.demonstrate_dhw_mode_control()
        await self.demonstrate_temperature_control()
        await self.demonstrate_convenience_methods()
        
        # Final status check
        print("\n📊 Final Status Check:")
        await self.get_current_status()
        
        print("\n✅ Device Control Demonstration Complete!")
        print("💡 For production monitoring, see tank_monitoring_production.py")
        
    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            await self.client.close()


async def main():
    """Main demonstration function."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Load configuration
        config = NaviLinkConfig.from_environment()
        
        # Validate configuration
        if not config.email or not config.password:
            print("❌ Configuration Error: Email and password required")
            print("💡 Please copy .env.template to .env and configure credentials")
            sys.exit(1)
            
        # Run demonstration
        async with DeviceControlDemo(config) as demo:
            await demo.run_demo()
            
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())