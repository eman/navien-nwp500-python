#!/usr/bin/env python3
"""
Basic usage example for the Navilink library.

This example demonstrates how to:
1. Connect to AWS IoT using credentials
2. Subscribe to MQTT topics
3. Publish messages
4. Handle received messages asynchronously
"""

import asyncio
import json
import logging
import os
from navilink import NavilinkClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def temperature_handler(topic: str, payload: bytes):
    """Handle temperature sensor messages."""
    try:
        data = json.loads(payload.decode())
        temperature = data.get('temperature', 'N/A')
        timestamp = data.get('timestamp', 'N/A')
        print(f"🌡️  Temperature: {temperature}°C at {timestamp}")
    except json.JSONDecodeError:
        print(f"📦 Raw message on {topic}: {payload.decode()}")


async def status_handler(topic: str, payload: bytes):
    """Handle device status messages."""
    try:
        data = json.loads(payload.decode())
        device_id = data.get('device_id', 'unknown')
        status = data.get('status', 'unknown')
        print(f"📡 Device {device_id} status: {status}")
    except json.JSONDecodeError:
        print(f"📦 Raw status message: {payload.decode()}")


async def main():
    """Main example function."""
    # Configuration - replace with your actual values
    endpoint = os.getenv("AWS_IOT_ENDPOINT", "your-endpoint.iot.us-east-1.amazonaws.com")
    region = os.getenv("AWS_REGION", "us-east-1")
    client_id = os.getenv("CLIENT_ID", "navilink-example")
    
    # AWS credentials - consider using environment variables or IAM roles
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "your-access-key-id")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "your-secret-access-key")
    session_token = os.getenv("AWS_SESSION_TOKEN")  # Optional for temporary credentials
    
    print(f"🚀 Starting Navilink example...")
    print(f"📍 Endpoint: {endpoint}")
    print(f"🌍 Region: {region}")
    print(f"🆔 Client ID: {client_id}")
    
    # Create client
    client = NavilinkClient(
        endpoint=endpoint,
        region=region,
        client_id=client_id
    )
    
    try:
        # Connect to AWS IoT
        print("🔌 Connecting to AWS IoT...")
        await client.connect_with_credentials(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token
        )
        print("✅ Connected successfully!")
        
        # Subscribe to different topics with specific handlers
        print("📡 Subscribing to topics...")
        await client.subscribe("sensors/temperature", callback=temperature_handler)
        await client.subscribe("devices/+/status", callback=status_handler)
        await client.subscribe("navilink/test")  # No specific handler - uses default
        
        # Publish some test messages
        print("📤 Publishing test messages...")
        
        # Temperature sensor data
        temp_data = {
            "device_id": "temp_sensor_01",
            "temperature": 23.5,
            "humidity": 45.2,
            "timestamp": "2024-01-01T12:00:00Z"
        }
        await client.publish("sensors/temperature", json.dumps(temp_data).encode())
        
        # Device status
        status_data = {
            "device_id": "sensor_01",
            "status": "online",
            "battery": 85,
            "timestamp": "2024-01-01T12:00:00Z"
        }
        await client.publish("devices/sensor_01/status", json.dumps(status_data).encode())
        
        # Simple test message
        await client.publish("navilink/test", b"Hello from Navilink!")
        
        print("📬 Listening for messages for 30 seconds...")
        print("💡 You can publish messages to the subscribed topics from AWS IoT console")
        
        # Listen for messages
        await asyncio.sleep(30)
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise
    
    finally:
        print("🔌 Disconnecting...")
        await client.disconnect()
        print("👋 Example completed!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        exit(1)