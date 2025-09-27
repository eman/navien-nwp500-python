# NaviLink Python Library - Copilot Instructions

## Project Overview
This is a production-ready Python library for communicating with the Navien NaviLink service, enabling control and monitoring of Navien water heaters and smart home devices. The library provides both REST API access and AWS IoT Core MQTT real-time communication capabilities, with a focus on heat pump water heater monitoring and data collection.

**Status**: Production Ready ✅
**Primary Use Case**: Long-term tank monitoring with DHW (Domestic Hot Water) charge level tracking
**Testing**: Validated with Navien NWP500 Heat Pump Water Heater

## Core Requirements

### 1. Library Structure
- **Package Name**: `navilink` (lowercase)
- **Main Module**: `navilink/__init__.py`
- **Core Classes**: 
  - `NaviLinkClient` - Main client for API interactions with session management
  - `NaviLinkDevice` - Represents a connected device with MQTT capabilities
  - `NaviLinkAuth` - Handles authentication and token management with AWS IoT credentials
  - `AWSIoTWebSocket` - AWS IoT Core WebSocket/MQTT communication with MQTT5 support

### 2. API Endpoints (Validated Production)
Base URL: `https://nlus.naviensmartcontrol.com/api/v2.1/`

#### Authentication ✅
- **POST** `/user/sign-in` - User authentication
  - **Required Headers**: `Content-Type: application/json`
  - **Request Body**: `{"email": "user@example.com", "password": "password"}`
  - **Returns**: Authentication tokens, user info, and AWS IoT credentials
  - **Critical**: Must include proper session management for subsequent calls

#### Device Management ✅
- **GET** `/device/list` - Get list of user's devices
  - **Authentication**: Requires session from sign-in
  - **Returns**: Array of devices with `device_type: 52` for water heaters
- **GET** `/device/info` - Get detailed device information
  - **Query Params**: `additionalValue`, `controllerId`, `macAddress`, `userId`, `userType`
  - **Returns**: Comprehensive device features and configuration
- **GET** `/device/firmware/info` - Get device firmware information
- **GET** `/device/tou` - Get Time of Use (TOU) information
- **GET** `/device/connectivity-status` - **NEW**: Check if device is online for MQTT

#### App Management ✅
- **POST** `/app/update-push-token` - Update push notification token

### 3. AWS IoT Core MQTT Communication (Production Implementation)
- **WebSocket URL**: `wss://nlus-iot.naviensmartcontrol.com/mqtt`
- **Backend**: AWS IoT Core with MQTT over WebSocket
- **Authentication**: AWS Signature Version 4 (AWS4-HMAC-SHA256)
- **Protocol Support**: 
  - **MQTT3**: Production stable (current default)
  - **MQTT5**: Infrastructure ready, fallback enabled
- **Topics Pattern**: 
  - **Command**: `cmd/{deviceType}/{deviceId}/st` (QoS 0 for polling)
  - **Response**: `cmd/{deviceType}/{groupId}/{userId}/{sessionId}/res/st` (QoS 1 for reliability)

#### Critical MQTT Commands (Production Validated) ✅
- **16777217** (0x1000001) - Get device information (DID)
- **16777219** (0x1000003) - **Primary**: Get comprehensive device status
- **16777222** (0x1000006) - Get reservations/schedules

#### MQTT Message Format (Binary Protocol)
```python
# Command structure (8 bytes + payload)
command_bytes = struct.pack('>I', command)  # 4 bytes, big-endian
device_id_bytes = device_id.encode('utf-8')[:4].ljust(4, b'\x00')  # 4 bytes
message = command_bytes + device_id_bytes
```

### 4. Device Data Models (Production Validated)

#### Critical DHW Fields for Tank Monitoring ✅
```python
@dataclass
class DHWStatus:
    # Core tank monitoring fields
    dhw_charge_per: int           # 0-100% tank thermal energy level
    dhw_temperature: int          # °F - Current hot water output temperature
    dhw_temperature_setting: int  # °F - Target temperature setpoint
    operation_mode: int           # Heat pump operation mode (see codes below)
    
    # Heat source status (validated field names)
    comp_use: int                 # 0-2: Compressor/heat pump status
    heat_upper_use: int           # 0-2: Upper electric element status  
    heat_lower_use: int           # 0-2: Lower electric element status
    eva_fan_use: int             # 0-2: Evaporator fan status
    
    # System status
    dhw_use: int                 # 0-2: Hot water demand status
    error_code: int              # 0=No error
    sub_error_code: int          # Additional error detail
    wifi_rssi: int               # WiFi signal strength
    device_connected: int        # 0=Offline, 1=Online, 2=Active
```

#### Temperature Sensors (High Precision) ✅
```python
# Most temperature fields are in 0.1°F units - divide by 10
tank_upper_temperature: int    # 0.1°F units (divide by 10)
tank_lower_temperature: int    # 0.1°F units (divide by 10) 
discharge_temperature: int     # 0.1°F units (divide by 10)
ambient_temperature: int       # 0.1°F units (divide by 10)
outside_temperature: int       # °F units (direct)
```

#### Operation Mode Codes (Heat Pump Water Heater) ✅
Based on production data analysis:
- **Mode 0**: Standby - No active heating
- **Mode 1**: Heat Pump Only - Efficient operation (430-450W)
- **Mode 2**: Resistive Element Only - Backup heating (4000W+)
- **Mode 3**: Heat Pump + Resistive Element - High demand mode

#### Status Codes (0-2 Pattern) ✅
- **0**: Off/Inactive
- **1**: On/Ready  
- **2**: Active/Operating

### 5. Authentication Flow (Production Implementation) ✅
1. **POST** `/user/sign-in` with email/password
2. Extract session cookies and authorization tokens
3. Store AWS IoT credentials from response
4. Generate AWS signed WebSocket URL with proper signature
5. Maintain session for subsequent REST API calls
6. Handle authentication errors and token refresh

### 6. Real-time Communication Flow (Production Implementation) ✅
1. **Authenticate** via REST API to get AWS IoT credentials
2. **Check Connectivity** via `/device/connectivity-status` before MQTT
3. **Generate AWS IoT WebSocket URL** with proper signature
4. **Connect** to AWS IoT with MQTT3 (stable) or MQTT5 (fallback enabled)
5. **Subscribe** to device response topics with QoS 1
6. **Send Status Commands** (16777219) with QoS 0 for polling
7. **Parse Binary Responses** and update device status
8. **Handle Connection Recovery** with exponential backoff

### 7. Production Error Handling ✅
- **HTTP Errors**: 403 Forbidden, 500 Internal Server, network timeouts
- **MQTT Connection Issues**: WebSocket timeouts, AWS IoT authentication failures
- **Device Offline**: Graceful handling when devices don't respond to MQTT
- **Session Expiry**: Automatic re-authentication and session recovery
- **Network Interruptions**: Exponential backoff reconnection with jitter

### 8. Configuration (Production Ready) ✅
```python
# Environment variables supported
NAVILINK_EMAIL=""
NAVILINK_PASSWORD=""

# Reconnection configuration
@dataclass
class ReconnectConfig:
    max_retries: int = 20
    initial_delay: float = 2.0
    max_delay: float = 120.0
    jitter: bool = True
```

### 9. Async Support (Production Implementation) ✅
- **Fully Async**: All operations use `asyncio` and `aiohttp`
- **Connection Pooling**: Reused AWS IoT client resources
- **Context Management**: Proper resource cleanup with async context managers
- **Event Loop Management**: Single event loop for all operations

### 10. Testing Strategy (Production Validated) ✅
- **Live Integration Tests**: Validated with real Navien NWP500 device
- **Tank Monitoring**: 35+ data points collected over production usage
- **Connection Stability**: Multi-hour monitoring sessions validated
- **Error Recovery**: Network interruption and reconnection tested

## Implementation Guidelines

### Code Style (Production Standard) ✅
- **PEP 8 Compliance**: Full adherence to Python style guidelines
- **Type Hints**: Comprehensive type annotations throughout
- **Dataclasses**: All data models use `@dataclass` with proper typing
- **Logging**: Structured logging with configurable levels
- **Error Messages**: User-friendly error messages with debug details

### Dependencies (Production Tested) ✅
```python
# Core requirements
aiohttp>=3.8.0           # Async HTTP client
awsiotsdk>=1.21.0       # AWS IoT SDK with MQTT5 support  
cryptography>=3.4.0     # AWS signature generation

# Development/analysis
pandas>=1.5.0           # Data analysis (optional)
matplotlib>=3.5.0       # Data visualization (optional)
```

### Project Structure (Production Implementation) ✅
```
navilink/
├── __init__.py              # Main exports and version
├── client.py                # NaviLinkClient with session management
├── auth.py                  # Authentication with AWS IoT credential handling
├── device.py                # NaviLinkDevice with MQTT integration
├── aws_iot_websocket.py     # AWS IoT WebSocket/MQTT with MQTT5 support
├── mqtt.py                  # High-level MQTT wrapper (legacy)
├── models.py                # Data models and status parsing
├── exceptions.py            # Custom exceptions
└── utils.py                 # Utility functions

examples/
├── tank_monitoring_enhanced.py    # Production tank monitoring script
├── tank_monitoring_hybrid.py      # REST + MQTT hybrid approach
├── basic_usage.py                 # Simple client usage
└── README.md                      # Usage examples

docs/
├── DEVICE_DATA_SCHEMA.md          # Complete field definitions and units
├── FIELD_INSIGHTS.md              # Production data analysis insights
└── README.md                      # API documentation

tests/
├── test_enhanced_quick_final.py   # Production integration test
├── test_connectivity_status.py    # Device connectivity validation
└── test_rest_vs_mqtt.py          # API comparison tests
```

### Example Usage (Production Code) ✅
```python
from navilink import NaviLinkClient
from navilink.aws_iot_websocket import ReconnectConfig

async def monitor_tank():
    """Production-ready tank monitoring example."""
    
    # Initialize client with session management
    client = NaviLinkClient()
    
    try:
        # Authenticate with automatic session handling
        await client.authenticate("user@example.com", "password")
        
        # Get devices (typically returns 1 water heater)
        devices = await client.get_devices()
        device = devices[0]
        
        # Check device connectivity before MQTT
        connectivity = await device.get_connectivity_status()
        if not connectivity.get('device_connected'):
            print("Device offline - cannot start MQTT monitoring")
            return
            
        # Configure enhanced reconnection
        reconnect_config = ReconnectConfig(
            max_retries=20,
            initial_delay=2.0,
            max_delay=120.0,
            jitter=True
        )
        
        # Get MQTT connection with production settings
        mqtt_conn = await device.get_mqtt_connection(
            reconnect_config=reconnect_config
        )
        await mqtt_conn.connect()
        
        # Set up status callback for tank monitoring
        async def on_status_update(status):
            # Core tank metrics for analysis
            charge = status.dhw_charge_per        # Tank energy level %
            temp = status.dhw_temperature         # Output temperature °F
            mode = status.operation_mode          # Heat pump mode
            power = status.current_inst_power     # Power consumption W
            
            print(f"Tank: {charge}% | Temp: {temp}°F | Mode: {mode} | Power: {power}W")
            
            # CSV logging for long-term analysis
            with open('tank_data.csv', 'a') as f:
                f.write(f"{datetime.now().isoformat()},{charge},{temp},{mode},{power}\n")
        
        mqtt_conn.set_status_callback(on_status_update)
        
        # Start monitoring with 5-minute polling (production recommended)
        await mqtt_conn.start_monitoring(polling_interval=300)
        
    finally:
        await client.close()  # Proper resource cleanup
```

## Production Data Insights ✅

### DHW Charge Percentage Analysis
- **Definition**: Tank thermal energy level as percentage of maximum capacity
- **Range**: 0-100% (observed stable at 93% during optimal operation)
- **Not Temperature**: This represents available energy for hot water delivery
- **Monitoring Value**: Critical for understanding hot water availability

### Power Consumption Patterns (Validated)
- **Heat Pump Operation**: 428-451W average (compressor + evaporator fan)
- **Resistance Heating**: 4000W+ (backup electric elements) 
- **Efficiency Indicator**: <500W = heat pump, >4000W = electric backup

### Temperature Relationships (Production Data)
- **Tank Stratification**: Upper tank 1-3°F higher than lower during heating
- **Precision**: Most sensors provide 0.1°F resolution (divide by 10)
- **Discharge Temperature**: Heat pump discharge typically higher than tank sensors

### Operation Mode Behavior (Real Device)
- **Mode 1 Dominance**: Heat pump water heaters spend majority of time in Mode 1
- **Mode Changes**: Indicate demand patterns and system responses
- **Efficiency Correlation**: Mode 1 = optimal efficiency, Mode 2/3 = backup operation

## Monitoring Best Practices (Production Validated) ✅

### Data Collection Intervals
- **Tank Monitoring**: 5-minute intervals for long-term efficiency analysis
- **Real-time Debug**: 30-60 second intervals for troubleshooting
- **High-frequency**: 10-30 second intervals for detailed system analysis

### Critical Alerts
- `error_code != 0`: System fault requiring attention
- `dhw_charge_per < 20`: Low hot water availability warning  
- `current_inst_power > 4000W`: Unexpected electric heating activation
- `device_connected == 0`: Device offline - MQTT will not respond

### CSV Data Logging (Production Format)
```csv
timestamp,dhw_charge_percent,operation_mode,dhw_temperature,current_inst_power,tank_upper_temp,tank_lower_temp
2025-09-26T19:00:00.000000,93,1,117,442,58.9,57.1
```

## Security Considerations (Production) ✅
- **Credential Management**: Never log passwords or tokens in production
- **AWS IoT Security**: Proper signature generation and WebSocket security
- **Session Handling**: Secure session cookie management
- **Input Validation**: All user inputs validated and sanitized
- **Network Security**: TLS/WSS encryption for all communications

## MQTT5 Future Enhancement ✅
The library includes complete MQTT5 infrastructure ready for activation:
```python
# Enable MQTT5 when AWS IoT SDK stabilizes
# In aws_iot_websocket.py:
self.use_mqtt5 = True  # Current: False for stability
```

## Troubleshooting (Production Experience) ✅

### Common Issues
1. **403 WebSocket Error**: Check authentication and AWS IoT credentials
2. **Empty CSV Files**: Device offline or MQTT commands not reaching device
3. **Connection Timeouts**: Use connectivity status check before MQTT operations
4. **Missing Data**: Ensure proper MQTT subscription and binary message parsing

### Debugging Tools
- `test_enhanced_quick_final.py` - Complete integration test
- `test_connectivity_status.py` - Device online verification
- Enhanced logging with connection statistics and retry counts

## Reference Files (Production Analysis) ✅
The `reference/` directory contains:
- `HTTPToolkit_2025-09-26_13-48.har` - Complete API interaction capture
- `GET nlus-iot.naviensmartcontrol.com.har` - WebSocket/MQTT message analysis
- `AmazonRootCA1.pem` - AWS Root CA certificate for SSL verification

## Version Information
- **Library Version**: 1.0.0 (Production Ready)
- **Tested Device**: Navien NWP500 Heat Pump Water Heater
- **MQTT Protocol**: MQTT3 (stable), MQTT5 (infrastructure ready)
- **Python Compatibility**: 3.8+ (async/await required)