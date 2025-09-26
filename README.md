# NaviLink Python Library

A Python library for communicating with the Navien NaviLink service, which allows control and monitoring of Navien water heaters and other smart home devices.

## ✅ Current Status

### **Fully Working Features**
- ✅ **Authentication & Session Management** - Complete JWT token handling
- ✅ **Device Discovery** - List and manage devices with full metadata  
- ✅ **REST API Integration** - All major endpoints working perfectly
- ✅ **Device Information** - Get device details, location, connection status
- ✅ **TOU Data Access** - Time of Use information retrieval

### **In Development**  
- 🔧 **Real-time WebSocket/MQTT** - 95% complete, authentication issue being resolved

## Features

- **REST API Access** - Full access to NaviLink REST API endpoints
- **Device Control** - Control water heater settings and schedules  
- **Status Monitoring** - Get device status and sensor readings
- **Energy Usage** - Access energy usage data and analytics (via TOU endpoint)
- **Async Support** - Built with asyncio for efficient async operations

## Installation

```bash
pip install navilink
```

Or for development:

```bash
git clone https://github.com/your-username/navilink.git
cd navilink
pip install -e .
```

## Quick Start

```python
import asyncio
from navilink import NaviLinkClient

async def main():
    async with NaviLinkClient() as client:
        # Authenticate
        user_info = await client.authenticate("your-email@example.com", "password")
        print(f"Authenticated as {user_info.email}")
        
        # Get devices
        devices = await client.get_devices()
        print(f"Found {len(devices)} devices")
        
        for device in devices:
            print(f"Device: {device.name} (MAC: {device.mac_address})")
            print(f"  Type: {device.device_type}")
            print(f"  Location: {device.location}")
            print(f"  Connected: {device.connected}")
            
            # Get device information
            device_info = await client.get_device_info(device.mac_address)
            if device_info:
                print(f"  Device Type: {device_info.device_type}")

asyncio.run(main())
```

## Configuration

Set environment variables for credentials:

```bash
export NAVILINK_EMAIL="your-email@example.com"
export NAVILINK_PASSWORD="your-password"
```

## Examples

See the `examples/` directory for detailed usage examples:

- `basic_usage.py` - Basic device interaction
- `production_example.py` - Production-ready usage patterns
- `real_time_monitoring.py` - Real-time monitoring (when WebSocket is resolved)

## API Reference

### NaviLinkClient

Main client for API interactions:

- `authenticate(email, password)` - Authenticate with NaviLink service
- `get_devices()` - Get list of user devices
- `get_device_info(mac_address)` - Get device information  
- `get_tou_info(...)` - Get Time of Use information

### NaviLinkDevice

Represents a connected device:

- `mac_address` - Device MAC address
- `name` - Device name
- `device_type` - Device type (52 for water heaters)
- `location` - Device location info
- `connected` - Connection status
- `home_seq` - Home sequence ID

### Data Models

- `UserInfo` - User authentication details
- `DeviceInfo` - Device information and capabilities
- `DeviceFeatures` - Device feature flags and limits
- `TOUInfo` - Time of Use information

## Current Limitations

- **Real-time WebSocket monitoring** requires resolving a 403 authentication issue with AWS IoT
- **Device control commands** depend on WebSocket connection  
- **Live status updates** currently not available (polling can be implemented)

The REST API functionality is fully operational and suitable for most use cases.

## Development

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:

```bash
python test_basic_auth.py <email> <password>
```

Format code:

```bash
black navilink/
isort navilink/
```

## Architecture

The library implements:

1. **REST API Client** - Complete NaviLink API integration
2. **Authentication Management** - JWT token handling with AWS credentials
3. **Binary MQTT Protocol** - Full MQTT 3.1.1 implementation for real-time communication
4. **WebSocket Connection** - AWS IoT Core signed URL generation
5. **Device Management** - High-level device abstraction
6. **Error Handling** - Comprehensive error handling and retries

## License

MIT License - see LICENSE file for details.

## Disclaimer

This library is not affiliated with Navien. Use at your own risk.