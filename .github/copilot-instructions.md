# NaviLink Python Library - Copilot Instructions

## Project Overview
This is a Python library for communicating with the Navien NaviLink service, which allows control and monitoring of Navien water heaters and other smart home devices. The library should provide both REST API access and WebSocket/MQTT real-time communication capabilities.

## Core Requirements

### 1. Library Structure
- **Package Name**: `navilink` (lowercase)
- **Main Module**: `navilink/__init__.py`
- **Core Classes**: 
  - `NaviLinkClient` - Main client for API interactions
  - `NaviLinkDevice` - Represents a connected device
  - `NaviLinkAuth` - Handles authentication and token management
  - `NaviLinkMQTT` - Handles WebSocket/MQTT real-time communication

### 2. API Endpoints (from reference HAR files)
Base URL: `https://nlus.naviensmartcontrol.com/api/v2.1/`

#### Authentication
- **POST** `/user/sign-in` - User authentication
  - Returns authentication tokens and user info

#### Device Management  
- **GET** `/device/list` - Get list of user's devices
- **GET** `/device/info` - Get detailed device information
- **GET** `/device/firmware/info` - Get device firmware information
- **GET** `/device/tou` - Get Time of Use (TOU) information
  - Query params: `additionalValue`, `controllerId`, `macAddress`, `userId`, `userType`

#### App Management
- **POST** `/app/update-push-token` - Update push notification token

### 3. WebSocket/MQTT Communication
- **WebSocket URL**: `wss://nlus-iot.naviensmartcontrol.com/mqtt`
- Uses AWS IoT Core with signed URLs (AWS4-HMAC-SHA256 signature)
- Protocol: MQTT over WebSocket
- Topics pattern: `cmd/{deviceType}/{deviceId}/st` for status
- Response topics: `cmd/{deviceType}/{groupId}/{userId}/{sessionId}/res`

#### Key MQTT Commands (from analysis)
- **16777217** - Get device information (DID)
- **16777219** - Get device status 
- **16777222** - Get reservations

### 4. Device Types and Data Models

#### Device Information
```python
@dataclass
class DeviceFeatures:
    country_code: int
    model_type_code: int
    control_type_code: int
    volume_code: int
    controller_sw_version: int
    panel_sw_version: int
    wifi_sw_version: int
    # ... (many more fields from HAR analysis)

@dataclass
class DeviceInfo:
    device_type: int  # 52 for water heaters
    mac_address: str
    additional_value: str
    controller_serial_number: str
    features: DeviceFeatures
```

#### Device Status
```python
@dataclass  
class DeviceStatus:
    command: int
    outside_temperature: int
    operation_mode: int
    dhw_temperature: int  # Domestic Hot Water
    dhw_temperature_setting: int
    dhw_use: int
    error_code: int
    sub_error_code: int
    wifi_rssi: int
    # ... (comprehensive status from HAR data)
```

### 5. Authentication Flow
1. User provides email/password
2. Library calls `/user/sign-in` endpoint
3. Store returned authentication tokens
4. Use tokens for subsequent API calls and WebSocket connection
5. Handle token refresh as needed

### 6. Real-time Communication Flow
1. Authenticate via REST API to get credentials
2. Generate AWS IoT signed WebSocket URL
3. Connect to WebSocket with MQTT protocol
4. Subscribe to device response topics
5. Send commands to device command topics
6. Handle real-time status updates

### 7. Error Handling
- HTTP errors (4xx, 5xx responses)
- WebSocket connection failures
- MQTT protocol errors
- Authentication failures and token expiry
- Device offline/unreachable scenarios

### 8. Configuration
- Support environment variables for credentials
- Configuration file support (YAML/JSON)
- Runtime configuration options

### 9. Async Support
- Use `asyncio` and `aiohttp` for async operations
- Support both sync and async clients
- WebSocket connections should be async

### 10. Testing Strategy
- Unit tests for all core functionality
- Integration tests with mock servers
- Example scripts demonstrating usage
- Test data based on HAR file analysis

## Implementation Guidelines

### Code Style
- Follow PEP 8 Python style guide
- Use type hints throughout
- Use dataclasses for data models
- Include comprehensive docstrings
- Use `logging` module for debug/info output

### Dependencies
- `aiohttp` - Async HTTP client
- `websockets` - WebSocket client  
- `paho-mqtt` or `aiomqtt` - MQTT client
- `pydantic` - Data validation (optional)
- `cryptography` - For AWS signature generation
- Standard library: `json`, `logging`, `dataclasses`, `typing`

### Project Structure
```
navilink/
├── __init__.py           # Main exports
├── client.py            # NaviLinkClient class
├── auth.py              # Authentication handling  
├── device.py            # Device classes
├── mqtt.py              # MQTT/WebSocket communication
├── models.py            # Data models
├── exceptions.py        # Custom exceptions
└── utils.py             # Utility functions

tests/
├── __init__.py
├── test_client.py
├── test_auth.py
├── test_device.py
└── test_mqtt.py

examples/
├── basic_usage.py
├── real_time_monitoring.py
└── device_control.py
```

### Example Usage
```python
from navilink import NaviLinkClient

# Initialize client
client = NaviLinkClient()

# Authenticate
await client.authenticate(email="user@example.com", password="password")

# Get devices
devices = await client.get_devices()

# Get device status
device = devices[0]
status = await device.get_status()

# Start real-time monitoring
async def on_status_update(status):
    print(f"Temperature: {status.dhw_temperature}°F")

await device.start_monitoring(callback=on_status_update)
```

## Security Considerations
- Never log or expose user credentials
- Securely handle authentication tokens
- Validate all input data
- Use secure WebSocket connections (WSS)
- Follow AWS IoT security best practices

## Reference Files Location
The `reference/` directory contains:
- `HTTPToolkit_2025-09-26_13-48.har` - Main API calls
- `GET nlus-iot.naviensmartcontrol.com.har` - WebSocket/MQTT data
- `AmazonRootCA1.pem` - AWS Root CA certificate

Use these files to understand the exact API request/response formats and WebSocket message structures.