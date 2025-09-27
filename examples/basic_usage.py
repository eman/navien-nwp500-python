#!/usr/bin/env python3
"""
Basic usage example for NaviLink library.

This example demonstrates basic authentication, device discovery, and status retrieval.
Perfect for getting started with the library.

Usage:
    # Using environment variables (recommended)
    export NAVILINK_EMAIL="user@example.com"
    export NAVILINK_PASSWORD="password"
    python examples/basic_usage.py
    
    # Using credentials file (development)
    cp examples/credentials_template.py examples/credentials.py
    # Edit credentials.py with your actual credentials
    python examples/basic_usage.py
"""

import asyncio
import logging
import os
from pathlib import Path

from navilink import NaviLinkClient, NaviLinkConfig
from navilink.exceptions import NaviLinkError

# Try to import development credentials
try:
    from credentials import EMAIL, PASSWORD
    HAS_CREDENTIALS_FILE = True
except ImportError:
    EMAIL = PASSWORD = None
    HAS_CREDENTIALS_FILE = False

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_credentials():
    """Get credentials from environment variables or credentials file."""
    # Try environment variables first (production)
    email = os.getenv("NAVILINK_EMAIL")
    password = os.getenv("NAVILINK_PASSWORD")
    
    if email and password:
        logger.info("Using credentials from environment variables")
        return email, password
    
    # Fall back to credentials file (development)
    if HAS_CREDENTIALS_FILE and EMAIL and PASSWORD:
        if EMAIL != "your_email@example.com":  # Check if template was modified
            logger.info("Using credentials from credentials.py file")
            return EMAIL, PASSWORD
    
    # No valid credentials found
    logger.error("No credentials found!")
    logger.error("Please either:")
    logger.error("  1. Set environment variables: export NAVILINK_EMAIL='...' NAVILINK_PASSWORD='...'")
    logger.error("  2. Copy credentials_template.py to credentials.py and edit it")
    return None, None

async def main():
    """Demonstrate basic NaviLink usage."""
    
    # Get credentials
    email, password = get_credentials()
    if not email or not password:
        return
    
    # Initialize client with configuration
    config = NaviLinkConfig.from_environment()
    
    async with NaviLinkClient(config=config) as client:
        try:
            # Authenticate
            logger.info("🔐 Authenticating...")
            user_info = await client.authenticate(email, password)
            logger.info(f"✅ Authentication successful for {user_info.email}")
            
            # Get devices
            logger.info("📱 Getting device list...")
            devices = await client.get_devices()
            logger.info(f"🏠 Found {len(devices)} devices")
            
            if not devices:
                logger.warning("No devices found in your account")
                return
            
            # Work with first device (typically there's only one water heater)
            device = devices[0]
            logger.info(f"🏠 Using device: {device.name} (MAC: {device.mac_address})")
            
            # Get device info
            try:
                device_info = await device.get_info()
                logger.info(f"📋 Device Type: {device_info.device_type}")
                logger.info(f"📋 Controller: {device_info.controller_serial_number}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get device info: {e}")
            
            # Get device status via REST API
            try:
                logger.info("📊 Getting device status via REST...")
                status = await device.get_status()
                
                # Display key metrics
                logger.info("📊 Status received:")
                logger.info(f"   Tank Charge: {status.dhw_charge_per}%")
                logger.info(f"   Temperature: {status.dhw_temperature}°F")
                logger.info(f"   Target Temp: {status.dhw_temperature_setting}°F")
                logger.info(f"   Operation Mode: {status.operation_mode}")
                logger.info(f"   Power Consumption: {status.current_inst_power}W")
                logger.info(f"   WiFi Signal: {status.wifi_rssi} dBm")
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
                    logger.warning("⚠️ High power usage - electric backup heating active")
                elif status.current_inst_power > 400:
                    logger.info("♻️ Heat pump operating efficiently")
                else:
                    logger.info("🔹 System in standby mode")
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to get device status: {e}")
            
            # Get reservations/schedules
            try:
                reservations = await device.get_reservations()
                logger.info(f"📅 Reservations: {len(reservations)}")
                for i, res in enumerate(reservations[:3]):  # Show first 3
                    logger.info(f"   {i+1}. {res}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to get reservations: {e}")
            
        except NaviLinkError as e:
            logger.error(f"❌ NaviLink Error: {e}")
        except Exception as e:
            logger.error(f"💥 Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())