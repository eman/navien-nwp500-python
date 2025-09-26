# NaviLink Python Library

A Python library for communicating with the Navien NaviLink service, which allows control and monitoring of Navien water heaters and other smart home devices.

## Features

- **REST API Access** - Full access to NaviLink REST API endpoints
- **Real-time Communication** - WebSocket/MQTT support for live device monitoring  
- **Device Control** - Control water heater settings and schedules
- **Status Monitoring** - Get real-time device status and sensor readings
- **Energy Usage** - Access energy usage data and analytics
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
        await client.authenticate("your-email@example.com", "password")
        
        # Get devices
        devices = await client.get_devices()
        device = devices[0]
        
        # Get current status
        status = await device.get_status()
        print(f"Water temperature: {status.dhw_temperature}°F")
        
        # Start real-time monitoring
        async def on_update(status):
            print(f"Temperature updated: {status.dhw_temperature}°F")
            
        await device.start_monitoring(callback=on_update)

asyncio.run(main())
```

## Configuration

Set environment variables for credentials:

```bash
export NAVILINK_EMAIL="your-email@example.com"
export NAVILINK_PASSWORD="your-password"
```

## Examples

See the `examples/` directory for more detailed usage examples:

- `basic_usage.py` - Basic device interaction
- `real_time_monitoring.py` - Real-time status monitoring

## API Reference

### NaviLinkClient

Main client for API interactions:

- `authenticate(email, password)` - Authenticate with NaviLink service
- `get_devices()` - Get list of user devices
- `get_device_info(mac_address)` - Get device information
- `get_tou_info(...)` - Get Time of Use information

### NaviLinkDevice

Represents a connected device:

- `get_status()` - Get current device status
- `get_info()` - Get device information
- `get_reservations()` - Get device schedules
- `set_temperature(temp)` - Set target temperature
- `start_monitoring()` - Start real-time monitoring
- `connect()` / `disconnect()` - Manage device connection

### Data Models

- `DeviceStatus` - Current device status and sensors
- `DeviceInfo` - Device information and capabilities
- `DeviceFeatures` - Device feature flags and limits
- `Reservation` - Scheduled operation
- `EnergyUsage` - Energy consumption data

## Development

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```

Format code:

```bash
black navilink/
isort navilink/
```

## License

MIT License - see LICENSE file for details.

## Disclaimer

This library is not affiliated with Navien. Use at your own risk.