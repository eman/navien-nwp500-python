# Navilink

A Python library for AWS IoT MQTT communication over WebSocket connections. Navilink provides an easy-to-use interface for authenticating with AWS IoT and asynchronously receiving MQTT messages.

## Features

- AWS IoT authentication using AWS credentials
- Asynchronous MQTT message handling over WebSocket
- Built-in error handling and logging
- Context manager support for automatic cleanup
- Customizable message callbacks per topic

## Installation

```bash
pip install navilink
```

## Quick Start

```python
import asyncio
from navilink import NavilinkClient

async def message_handler(topic: str, payload: bytes):
    """Handle received MQTT messages."""
    print(f"Received message on {topic}: {payload.decode()}")

async def main():
    # Initialize client
    client = NavilinkClient(
        endpoint="your-iot-endpoint.iot.us-east-1.amazonaws.com",
        region="us-east-1",
        client_id="my-client-id"
    )
    
    try:
        # Connect using AWS credentials
        await client.connect_with_credentials(
            aws_access_key_id="your-access-key",
            aws_secret_access_key="your-secret-key"
        )
        
        # Subscribe to a topic with custom handler
        await client.subscribe("my/topic", callback=message_handler)
        
        # Publish a message
        await client.publish("my/topic", b"Hello, AWS IoT!")
        
        # Keep the connection alive
        await asyncio.sleep(10)
        
    finally:
        await client.disconnect()

# Run the example
asyncio.run(main())
```

## Using Context Manager

```python
import asyncio
from navilink import NavilinkClient

async def main():
    async with NavilinkClient("your-endpoint.iot.us-east-1.amazonaws.com") as client:
        await client.connect_with_credentials(
            aws_access_key_id="your-access-key",
            aws_secret_access_key="your-secret-key"
        )
        
        await client.subscribe("sensors/temperature")
        await asyncio.sleep(30)  # Listen for messages

asyncio.run(main())
```

## Requirements

- Python 3.8+
- AWS IoT Core endpoint
- AWS credentials with IoT permissions

## Dependencies

- `awsiotsdk`: AWS IoT Device SDK for Python
- `boto3`: AWS SDK for Python
- `websockets`: WebSocket client/server implementation

## Development

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Format code:

```bash
black navilink/
```

## License

MIT License - see LICENSE file for details.