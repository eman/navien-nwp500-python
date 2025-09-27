# NaviLink Python Library Documentation

## Overview

The NaviLink Python library provides production-ready access to Navien smart water heating systems through both REST API and real-time MQTT communication. This documentation covers the complete API reference, data schemas, and production insights.

## Quick Start

### Installation

```bash
pip install navilink
```

### Basic Usage

```python
import asyncio
from navilink import NaviLinkClient, NaviLinkConfig

async def main():
    # Configure from environment variables (recommended)
    config = NaviLinkConfig.from_environment()
    
    async with NaviLinkClient(config=config) as client:
        # Authenticate
        await client.authenticate()
        
        # Get devices
        devices = await client.get_devices()
        device = devices[0]
        
        # Get real-time status
        mqtt_conn = await device.get_mqtt_connection()
        await mqtt_conn.connect()
        
        async def on_status(status):
            print(f"Tank charge: {status.dhw_charge_per}%")
            print(f"Temperature: {status.dhw_temperature}°F")
            print(f"Mode: {status.operation_mode}")
            
        mqtt_conn.set_status_callback(on_status)
        await mqtt_conn.start_monitoring(polling_interval=300)

asyncio.run(main())
```

### Environment Configuration

```bash
export NAVILINK_EMAIL="your@email.com"
export NAVILINK_PASSWORD="your_password" 
export NAVILINK_LOG_LEVEL="INFO"
export NAVILINK_MQTT_PROTOCOL="MQTT3"
```

## Core Classes

### NaviLinkClient

Main client for API interactions:

- `authenticate(email, password)` - Authenticate with NaviLink service
- `get_devices()` - Get list of user's devices
- `close()` - Clean up resources

### NaviLinkDevice

Represents a single water heater device:

- `get_device_info()` - Get device details via REST API
- `get_connectivity_status()` - Check if device is online
- `get_mqtt_connection()` - Get real-time MQTT connection

### NaviLinkConfig

Configuration management with enterprise patterns:

- `from_environment()` - Load from environment variables
- `validate()` - Validate configuration
- Support for debug mode, logging levels, retry policies

## Data Schema Reference

See [DEVICE_DATA_SCHEMA.md](DEVICE_DATA_SCHEMA.md) for complete field definitions.

### Key Fields for Tank Monitoring

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `dhw_charge_per` | int | % | Tank thermal energy level (0-100%) |
| `dhw_temperature` | int | °F | Hot water output temperature |
| `dhw_temperature_setting` | int | °F | Target temperature setpoint |
| `operation_mode` | int | code | Heat pump operation mode |
| `current_inst_power` | int | W | Real-time power consumption |

### Critical Production Notes ⚠️

**Temperature Sensor Field Names are Misleading!**

- `tank_upper_temperature` - Actually **cold water inlet** temperature (÷10 for °F)
- `tank_lower_temperature` - Actually **heat pump ambient** temperature (÷10 for °F)
- Hot water tank internal temperatures are **NOT available** via API
- Use `dhw_charge_per` for tank thermal state monitoring

### Operation Mode Codes (Production Validated)

- **Mode 0**: Standby/Off (1W power)
- **Mode 32**: Heat Pump Active (430-470W power)
- **Mode 33**: Electric Backup Only (4000W+)
- **Mode 34**: Hybrid Mode (variable power)

### Status Codes (0-2 Pattern)

- **0**: Off/Inactive
- **1**: On/Ready (standby)
- **2**: Active/Operating

**Important**: Status codes indicate readiness, not active operation. Use power consumption to determine actual heating activity.

## Production Examples

### Tank Monitoring

```python
from navilink import NaviLinkClient, NaviLinkConfig
from navilink.aws_iot_websocket import ReconnectConfig

async def monitor_tank():
    config = NaviLinkConfig.from_environment()
    
    async with NaviLinkClient(config=config) as client:
        await client.authenticate()
        devices = await client.get_devices()
        device = devices[0]
        
        # Check connectivity before MQTT
        connectivity = await device.get_connectivity_status()
        if not connectivity.get('device_connected'):
            print("Device offline")
            return
            
        # Production reconnection config
        reconnect_config = ReconnectConfig(
            max_retries=20,
            initial_delay=2.0,
            max_delay=120.0,
            jitter=True
        )
        
        mqtt_conn = await device.get_mqtt_connection(reconnect_config)
        await mqtt_conn.connect()
        
        def log_status(status):
            print(f"Tank: {status.dhw_charge_per}% | "
                  f"Temp: {status.dhw_temperature}°F | " 
                  f"Mode: {status.operation_mode} | "
                  f"Power: {status.current_inst_power}W")
                  
        mqtt_conn.set_status_callback(log_status)
        await mqtt_conn.start_monitoring(polling_interval=300)
```

### Error Handling

```python
from navilink.exceptions import (
    AuthenticationError,
    DeviceOfflineError, 
    CommunicationError
)

try:
    await client.authenticate(email, password)
except AuthenticationError:
    print("Invalid credentials")
except CommunicationError as e:
    print(f"Network error: {e}")
```

## API Reference

### REST Endpoints

Base URL: `https://nlus.naviensmartcontrol.com/api/v2.1/`

#### Authentication
- `POST /user/sign-in` - User authentication
- Returns: Session tokens and AWS IoT credentials

#### Device Management
- `POST /device/list` - Get user's devices
- `POST /device/info` - Get device details
- `GET /device/connectivity-status` - Check device online status

### MQTT Communication

- **WebSocket URL**: `wss://nlus-iot.naviensmartcontrol.com/mqtt`
- **Protocol**: AWS IoT Core with WebSocket transport
- **Authentication**: AWS Signature Version 4
- **Command Topics**: `cmd/{deviceType}/{deviceId}/st`
- **Response Topics**: `cmd/{deviceType}/{groupId}/{userId}/{sessionId}/res/st`

#### Key MQTT Commands
- `16777219` (0x1000003) - Get device status (primary)
- `16777217` (0x1000001) - Get device information
- `16777222` (0x1000006) - Get schedules/reservations

## Configuration Options

### NaviLinkConfig Fields

```python
@dataclass
class NaviLinkConfig:
    # Authentication
    email: Optional[str] = None
    password: Optional[str] = None
    
    # Endpoints
    base_url: str = "https://nlus.naviensmartcontrol.com/api/v2.1"
    websocket_url: str = "wss://nlus-iot.naviensmartcontrol.com/mqtt"
    
    # Protocol settings
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    http: HTTPConfig = field(default_factory=HTTPConfig)
    
    # Logging
    log_level: LogLevel = LogLevel.INFO
    debug_mode: bool = False
```

### Reconnection Configuration

```python
@dataclass 
class ReconnectConfig:
    max_retries: int = 20
    initial_delay: float = 2.0
    max_delay: float = 120.0
    jitter: bool = True
    backoff_multiplier: float = 2.0
```

## Production Guidelines

### Connection Management
- Always check device connectivity before MQTT operations
- Use exponential backoff for reconnection attempts
- Handle network interruptions gracefully

### Data Validation
- Trust power consumption over status codes for operation detection
- Validate `dhw_charge_per` range (0-100%)
- Check `error_code` for system faults

### Logging and Monitoring
- Use structured logging with correlation IDs
- Monitor connection stability metrics
- Log data to CSV for analysis

### Security
- Store credentials in environment variables
- Never log passwords or tokens
- Use TLS/WSS encryption for all communications

## Error Handling

### Exception Hierarchy

```
NaviLinkError (base)
├── AuthenticationError
├── DeviceError
│   └── DeviceOfflineError
├── CommunicationError
│   ├── APIError
│   ├── WebSocketError
│   └── MQTTError
```

### Common Error Scenarios

1. **403 WebSocket Error**: Check AWS IoT credentials and signature
2. **Device Offline**: Verify connectivity status before MQTT
3. **Authentication Failure**: Validate email/password credentials
4. **Connection Timeout**: Implement retry logic with backoff

## Testing

Run integration tests with real hardware:

```bash
export NAVILINK_EMAIL="your@email.com"
export NAVILINK_PASSWORD="your_password"
python tests/test_integration.py
```

## Version Information

- **Library Version**: 1.0.0 (Production Ready)
- **Tested Hardware**: Navien NWP500 Heat Pump Water Heater
- **MQTT Protocol**: MQTT3 (stable), MQTT5 (infrastructure ready)
- **Python Compatibility**: 3.8+

## Support

For issues and questions:
- Review production logs for error details
- Validate device connectivity status
- Check network connectivity and firewall settings
- Verify credentials and session management

## License

MIT License - see LICENSE file for details.