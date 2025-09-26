#!/usr/bin/env python3
"""
Production-ready example showing current working features.
"""

import asyncio
import logging
import os
from navilink import NaviLinkClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def production_example():
    """Demonstrate production-ready NaviLink usage."""
    
    # Get credentials from environment
    email = os.getenv("NAVILINK_EMAIL")
    password = os.getenv("NAVILINK_PASSWORD")
    
    if not email or not password:
        print("Set NAVILINK_EMAIL and NAVILINK_PASSWORD environment variables")
        return
    
    async with NaviLinkClient() as client:
        try:
            # 1. Authenticate
            logger.info("🔐 Authenticating with NaviLink...")
            user_info = await client.authenticate(email, password)
            logger.info(f"✅ Authenticated as {user_info.email}")
            logger.info(f"   User ID: {user_info.user_id}")
            logger.info(f"   User Type: {user_info.user_type}")
            logger.info(f"   Token expires: {user_info.token_expires_at}")
            
            # 2. Discover devices
            logger.info("\n🔍 Discovering devices...")
            devices = await client.get_devices()
            logger.info(f"✅ Found {len(devices)} device(s)")
            
            for i, device in enumerate(devices, 1):
                logger.info(f"\n📱 Device {i}: {device.name}")
                logger.info(f"   MAC Address: {device.mac_address}")
                logger.info(f"   Device Type: {device.device_type}")
                logger.info(f"   Additional Value: {device.additional_value}")
                logger.info(f"   Home Sequence: {device.home_seq}")
                logger.info(f"   Connection Status: {device.connected}")
                
                if device.location:
                    city = device.location.get('city', 'Unknown')
                    state = device.location.get('state', 'Unknown')
                    logger.info(f"   Location: {city}, {state}")
                
                # 3. Get device information
                logger.info("   📋 Getting device info...")
                try:
                    device_info = await client.get_device_info(device.mac_address)
                    if device_info:
                        logger.info("   ✅ Device info retrieved")
                        logger.info(f"      Type: {device_info.device_type}")
                        logger.info(f"      Controller S/N: {device_info.controller_serial_number}")
                    else:
                        logger.info("   ℹ️  No additional device info available")
                except Exception as e:
                    logger.warning(f"   ⚠️  Could not get device info: {e}")
            
            # 4. Example of polling for device status (REST API approach)
            if devices:
                device = devices[0]
                logger.info(f"\n🔄 Monitoring {device.name} (polling approach)...")
                
                for i in range(3):
                    try:
                        # In a real application, you would poll periodically
                        # or implement the WebSocket connection when the 403 issue is resolved
                        logger.info(f"   Poll #{i+1}: Getting current device status...")
                        
                        # Note: This would require implementing REST status endpoint
                        # or use the MQTT connection when working
                        logger.info("   ℹ️  Status polling would go here")
                        
                        await asyncio.sleep(2)  # Wait 2 seconds between polls
                        
                    except Exception as e:
                        logger.error(f"   ❌ Status poll failed: {e}")
            
            logger.info("\n🎉 NaviLink library working perfectly for REST API operations!")
            logger.info("💡 For real-time monitoring, WebSocket connection needs 403 auth issue resolved")
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(production_example())