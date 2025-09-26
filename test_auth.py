#!/usr/bin/env python3
"""
Test authentication with NaviLink service.
Run this script with your credentials to test the library.
"""

import asyncio
import logging
import sys
from navilink import NaviLinkClient

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_authentication(email: str, password: str):
    """Test basic authentication and device listing."""
    
    logger.info(f"Testing authentication for {email}")
    
    try:
        async with NaviLinkClient() as client:
            # Test authentication
            logger.info("Attempting authentication...")
            user_info = await client.authenticate(email, password)
            
            logger.info("✅ Authentication successful!")
            logger.info(f"User ID: {user_info.user_id}")
            logger.info(f"Email: {user_info.email}")
            logger.info(f"User Type: {user_info.user_type}")
            logger.info(f"Group ID: {user_info.group_id}")
            logger.info(f"Has Session Token: {bool(user_info.session_token)}")
            
            # Test device listing
            logger.info("Getting device list...")
            devices = await client.get_devices()
            
            logger.info(f"✅ Found {len(devices)} devices")
            
            for i, device in enumerate(devices):
                logger.info(f"Device {i+1}:")
                logger.info(f"  Name: {device.name}")
                logger.info(f"  MAC Address: {device.mac_address}")
                logger.info(f"  Device Type: {device.device_type}")
                logger.info(f"  Controller ID: {device.controller_id}")
                logger.info(f"  Additional Value: {device.additional_value}")
                
                # Test getting device info
                try:
                    logger.info("  Getting device info...")
                    device_info = await client.get_device_info(device.mac_address)
                    if device_info:
                        logger.info(f"  ✅ Device info retrieved")
                        logger.info(f"    Device Type: {device_info.device_type}")
                        logger.info(f"    Controller S/N: {device_info.controller_serial_number}")
                    else:
                        logger.warning("  ❌ No device info returned")
                except Exception as e:
                    logger.error(f"  ❌ Failed to get device info: {e}")
                
                # Test TOU info
                try:
                    logger.info("  Getting TOU info...")
                    tou_info = await client.get_tou_info(
                        device.additional_value,
                        device.controller_id,
                        device.mac_address
                    )
                    logger.info(f"  ✅ TOU info retrieved")
                    logger.info(f"    Status: {tou_info.status}")
                except Exception as e:
                    logger.error(f"  ❌ Failed to get TOU info: {e}")
                
                logger.info("")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def main():
    """Main test function."""
    if len(sys.argv) != 3:
        print("Usage: python test_auth.py <email> <password>")
        print("Example: python test_auth.py user@example.com mypassword")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    success = asyncio.run(test_authentication(email, password))
    
    if success:
        print("\n🎉 All tests passed! The NaviLink library is working correctly.")
    else:
        print("\n💥 Tests failed. Check the logs above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()