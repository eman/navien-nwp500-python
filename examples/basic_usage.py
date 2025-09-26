#!/usr/bin/env python3
"""
Basic usage example for NaviLink library.
"""

import asyncio
import logging
import os
from navilink import NaviLinkClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Demonstrate basic NaviLink usage."""
    
    # Get credentials from environment variables
    email = os.getenv("NAVILINK_EMAIL")
    password = os.getenv("NAVILINK_PASSWORD")
    
    if not email or not password:
        print("Please set NAVILINK_EMAIL and NAVILINK_PASSWORD environment variables")
        return
    
    # Initialize client
    async with NaviLinkClient() as client:
        try:
            # Authenticate
            logger.info("Authenticating...")
            user_info = await client.authenticate(email, password)
            logger.info(f"Authenticated as {user_info.email}")
            
            # Get devices
            logger.info("Getting device list...")
            devices = await client.get_devices()
            logger.info(f"Found {len(devices)} devices")
            
            for device in devices:
                logger.info(f"Device: {device.name} (MAC: {device.mac_address})")
                
                # Get device info
                try:
                    device_info = await device.get_info()
                    logger.info(f"  Device Type: {device_info.device_type}")
                    logger.info(f"  Controller: {device_info.controller_serial_number}")
                except Exception as e:
                    logger.warning(f"  Failed to get device info: {e}")
                
                # Get device status
                try:
                    logger.info("  Getting device status...")
                    status = await device.get_status()
                    logger.info(f"  DHW Temperature: {status.dhw_temperature}°")
                    logger.info(f"  DHW Setting: {status.dhw_temperature_setting}°")
                    logger.info(f"  WiFi RSSI: {status.wifi_rssi}")
                    logger.info(f"  Error Code: {status.error_code}")
                except Exception as e:
                    logger.warning(f"  Failed to get device status: {e}")
                
                # Get reservations
                try:
                    reservations = await device.get_reservations()
                    logger.info(f"  Reservations: {len(reservations)}")
                except Exception as e:
                    logger.warning(f"  Failed to get reservations: {e}")
            
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())