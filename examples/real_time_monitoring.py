#!/usr/bin/env python3
"""
Real-time monitoring example for NaviLink library.
"""

import asyncio
import logging
import os
from navilink import NaviLinkClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def status_callback(status):
    """Handle status updates from device."""
    logger.info(f"Status Update:")
    logger.info(f"  DHW Temperature: {status.dhw_temperature}°")
    logger.info(f"  DHW Setting: {status.dhw_temperature_setting}°") 
    logger.info(f"  Tank Upper: {status.tank_upper_temperature}°")
    logger.info(f"  Tank Lower: {status.tank_lower_temperature}°")
    logger.info(f"  Operation Mode: {status.operation_mode}")
    logger.info(f"  DHW Use: {status.dhw_use}")
    logger.info(f"  WiFi RSSI: {status.wifi_rssi}")
    logger.info(f"  Error Code: {status.error_code}")
    logger.info("---")

async def main():
    """Demonstrate real-time monitoring."""
    
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
            
            # Get first device
            devices = await client.get_devices()
            if not devices:
                logger.error("No devices found")
                return
            
            device = devices[0]
            logger.info(f"Monitoring device: {device.name} (MAC: {device.mac_address})")
            
            # Connect to device for real-time communication
            await device.connect()
            logger.info("Connected to device")
            
            # Start monitoring with callback
            await device.start_monitoring(callback=status_callback)
            logger.info("Started monitoring - press Ctrl+C to stop")
            
            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Stopping monitoring...")
                
            # Stop monitoring
            await device.stop_monitoring()
            await device.disconnect()
            
        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())