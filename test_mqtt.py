#!/usr/bin/env python3
"""
Test MQTT WebSocket connection for NaviLink service.
"""

import asyncio
import logging
import sys
from navilink import NaviLinkClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mqtt_connection(email: str, password: str):
    """Test MQTT WebSocket connection and device communication."""
    
    logger.info(f"Testing MQTT connection for {email}")
    
    try:
        async with NaviLinkClient() as client:
            # Authenticate
            logger.info("Authenticating...")
            user_info = await client.authenticate(email, password)
            logger.info("✅ Authentication successful!")
            
            # Get devices
            logger.info("Getting device list...")
            devices = await client.get_devices()
            
            if not devices:
                logger.error("No devices found")
                return False
            
            device = devices[0]
            logger.info(f"Testing with device: {device.name} (MAC: {device.mac_address})")
            
            # Test WebSocket connection
            logger.info("Connecting to device via MQTT...")
            try:
                await device.connect()
                logger.info("✅ MQTT connection established!")
                
                # Test getting device status
                logger.info("Getting device status via MQTT...")
                status = await device.get_status()
                
                logger.info("✅ Device status received!")
                logger.info(f"  DHW Temperature: {status.dhw_temperature}")
                logger.info(f"  DHW Setting: {status.dhw_temperature_setting}")
                logger.info(f"  Operation Mode: {status.operation_mode}")
                logger.info(f"  Error Code: {status.error_code}")
                logger.info(f"  WiFi RSSI: {status.wifi_rssi}")
                
                # Disconnect
                await device.disconnect()
                logger.info("✅ Successfully disconnected")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ MQTT connection failed: {e}")
                import traceback
                traceback.print_exc()
                return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    if len(sys.argv) != 3:
        print("Usage: python test_mqtt.py <email> <password>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    success = asyncio.run(test_mqtt_connection(email, password))
    
    if success:
        print("\n🎉 MQTT connection and device status working!")
    else:
        print("\n💥 MQTT test failed. Check the logs above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()