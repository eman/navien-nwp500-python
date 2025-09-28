# NaviLink Python Library - Copilot Instructions

## 🚨 **CRITICAL: AI Assistant Test Requirements** 

### **🧪 MANDATORY TESTING WORKFLOW**
**ALL AI assistants and coding tools MUST follow this workflow before submitting any code:**

1. **✅ ALWAYS run tests before submitting code:**
   ```bash
   pytest tests/ -v
   ```

2. **✅ ALWAYS ensure tests pass (target: 24+ passing tests):**
   ```bash
   # Expected result: 24 passed, 3 skipped (or better)
   # If tests fail, you MUST fix them before submitting
   ```

3. **✅ ALWAYS run code formatting before submitting:**
   ```bash
   black navien_nwp500 tests examples
   isort navien_nwp500 tests examples
   ```

4. **✅ If you break tests, you MUST fix them in the same commit:**
   - Debug the test failures
   - Update code to make tests pass
   - Never submit code with failing tests
   - Exception: Only if explicitly asked to create failing tests for debugging

5. **✅ For releases and packaging changes, ALSO run package build tests:**
   ```bash
   # Test package building (before any release-related changes)
   python -m build --sdist --wheel
   
   # Test package installation (verify setup.py/pyproject.toml changes)
   pip install -e .
   
   # Test import after installation
   python -c "import navien_nwp500; print('✅ Import successful')"
   
   # Test release workflow (before submitting release PRs)
   # Verify GitHub Actions will pass:
   # 1. All tests pass across Python 3.9-3.13 (Python 3.8 removed)
   # 2. Black formatting passes
   # 3. Package builds successfully 
   # 4. No breaking changes to API
   ```

### **🎯 Test Quality Standards**
- **Current baseline: 24 passing tests (89% pass rate)**
- **DO NOT decrease the number of passing tests**
- **If you add features, add corresponding tests**
- **All tests in `tests/` are active and must pass**

### **⚠️ Zero Tolerance Policy**
**Code submissions that break existing tests will be rejected.** Always verify your changes don't introduce regressions.

---

## Project Overview
This is a production-ready Python library for communicating with the Navien NaviLink service, enabling control and monitoring of Navien water heaters and smart home devices. The library provides both REST API access and AWS IoT Core MQTT real-time communication capabilities, with a focus on heat pump water heater monitoring and data collection.

**Status**: Production Ready ✅ v1.0.0  
**Primary Use Case**: Long-term tank monitoring with DHW (Domestic Hot Water) charge level tracking + device control
**Testing**: Validated with Navien NWP500 Heat Pump Water Heater in 24+ hour production sessions
**Architecture**: Enterprise-grade async Python with comprehensive configuration and error handling
**Control Capabilities**: DHW mode changes, temperature setting, turn on/off operations ✅

## 🏢 Enterprise Production Standards

### Configuration Management (Production Implementation) ✅
The library uses a unified configuration system that supports:

```python
# Method 1: .env file (recommended for production)
cp .env.template .env  # Edit with actual credentials
config = NaviLinkConfig.from_environment()

# Method 2: Environment variables
export NAVILINK_EMAIL="user@example.com"
export NAVILINK_PASSWORD="password" 
export NAVILINK_LOG_LEVEL="INFO"
config = NaviLinkConfig.from_environment()

# Method 3: Direct configuration (for applications)
config = NaviLinkConfig(
    email="user@example.com",
    password="password"
)
```

**No credentials.py files**: Legacy approach removed. All examples standardized on .env/.env.template pattern.

### Code Organization (Production Refactored) ✅
```
navilink/                     # Core library (production-ready)
├── __init__.py              # Clean exports, version 1.0.0
├── client.py                # NaviLinkClient with enterprise session management
├── auth.py                  # Authentication with AWS IoT credential handling
├── device.py                # NaviLinkDevice with MQTT integration + control methods
├── aws_iot_websocket.py     # AWS IoT WebSocket/MQTT with MQTT5 support
├── config.py                # Enterprise configuration management with .env support
├── models.py                # Comprehensive data models with production field insights
├── exceptions.py            # Complete custom exception hierarchy
└── utils.py                 # Utility functions

examples/                     # Sample applications only (no library code)
├── basic_usage.py           # ⭐ Getting started example (standardized config)
├── tank_monitoring_production.py  # ⭐ Production monitoring with CSV export
└── README.md                # Comprehensive usage guide

docs/                        # Consolidated documentation
├── DEVICE_DATA_SCHEMA.md    # Complete field definitions and units
├── FIELD_INSIGHTS.md        # Production data analysis insights
└── README.md                # API documentation

tests/
├── test_integration.py      # Production integration tests
└── __init__.py
```

**Removed**: All development artifacts, duplicate monitoring scripts, credentials_template.py

## 🔬 Critical Production Discoveries ⚠️

### Temperature Sensor Reality Check (FIELD VALIDATED)
**MAJOR DISCOVERY**: Field names are misleading! "Tank" sensors do NOT measure hot water tank temperatures.

**Production Data Analysis Reveals**:
- ✅ `dhw_temperature`: Only true hot water sensor (119-122°F actual delivery temperature)
- ❌ `tank_upper_temperature`: Actually cold water inlet/evaporator sensor (~60.5°F) 
- ❌ `tank_lower_temperature`: Actually heat pump ambient sensor (~61.1°F)
- **MISSING**: Hot water tank internal temperatures NOT accessible via NaviLink API
- **Critical**: Tank thermal monitoring must rely on `dhw_charge_percent` only

### Power vs Status Codes (PRODUCTION VALIDATED)
**IMPORTANT**: Status codes indicate readiness, NOT active operation!
- Production data: `heat_upper_use=1`, `heat_lower_use=1` (ready) but 1W power = not active
- `comp_use=2`, `eva_fan_use=2` + 466W power = actual heat pump operation
- **Rule**: Trust power consumption over status codes for operation determination

### Operation Mode Reality (CORRECTED)
Production system uses these modes (original 1-3 assumption was incorrect):
- **Mode 0**: Standby/Off (1W power consumption)
- **Mode 32**: Heat Pump Active (430-470W power consumption)
- **Mode 33**: Electric backup (4000W+, not observed in production)
- **Mode 34**: Hybrid mode (mixed power consumption)

## Core Requirements

### 1. Library Structure (Production Refactored) ✅
```
navilink/
├── __init__.py              # Main exports and version 1.0.0
├── client.py                # NaviLinkClient with enterprise session management
├── auth.py                  # Authentication with AWS IoT credential handling
├── device.py                # NaviLinkDevice with MQTT integration
├── aws_iot_websocket.py     # AWS IoT WebSocket/MQTT with MQTT5 support
├── config.py                # Enterprise configuration management
├── models.py                # Data models and status parsing
├── exceptions.py            # Comprehensive custom exceptions
└── utils.py                 # Utility functions

examples/
├── tank_monitoring_production.py  # ⭐ Main production example
├── basic_usage.py                 # Simple getting-started example
├── device_control_demo.py   # ⭐ Complete device control demonstration ✅
├── debug/                         # Development debugging tools
│   ├── debug_aws_creds.py
│   └── debug_websocket.py
└── README.md                      # Comprehensive usage guide

tests/
├── __init__.py
├── test_integration.py            # Production integration tests
└── [legacy test files moved here]

docs/
├── DEVICE_DATA_SCHEMA.md          # Complete field definitions and units
├── FIELD_INSIGHTS.md              # Production data analysis insights
└── README.md                      # API documentation
```

### 2. Enterprise Configuration System ✅
```python
from navien_nwp500 import NaviLinkConfig, NaviLinkClient

# Method 1: Environment variables (recommended for production)
export NAVILINK_EMAIL="user@example.com"
export NAVILINK_PASSWORD="password"
export NAVILINK_LOG_LEVEL="INFO"
export NAVILINK_MQTT_PROTOCOL="MQTT3"
config = NaviLinkConfig.from_environment()

# Method 2: Direct configuration
config = NaviLinkConfig(
    email="user@example.com",
    password="password"
)

# Use with client
client = NaviLinkClient(config=config)
```

### 3. API Endpoints (Validated Production)
Base URL: `https://nlus.naviensmartcontrol.com/api/v2.1/`

#### Authentication ✅
- **POST** `/user/sign-in` - User authentication
  - **Required Headers**: `Content-Type: application/json`
  - **Request Body**: `{"email": "user@example.com", "password": "password"}`
  - **Returns**: Authentication tokens, user info, and AWS IoT credentials
  - **Critical**: Must include proper session management for subsequent calls

#### Device Management ✅
- **POST** `/device/list` - Get list of user's devices (corrected from GET)
  - **Authentication**: Requires session from sign-in
  - **Body**: `{"offset": 0, "count": 20, "userId": "email"}`
  - **Returns**: Array of devices with `device_type: 52` for water heaters
- **POST** `/device/info` - Get detailed device information (corrected from GET)
  - **Body Params**: `macAddress`, `additionalValue`, `userId`
  - **Returns**: Comprehensive device features and configuration
- **GET** `/device/firmware/info` - Get device firmware information
- **GET** `/device/tou` - Get Time of Use (TOU) information
- **GET** `/device/connectivity-status` - Check if device is online for MQTT

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

#### Temperature Sensors (High Precision) ✅ **PRODUCTION VALIDATED**

**CRITICAL DISCOVERY**: Field names are misleading! "Tank" sensors do NOT measure hot water tank temperatures.

```python
# Direct Fahrenheit sensors (production validated)
dhw_temperature: int              # °F - Actual hot water output (119-122°F)
dhw_temperature_setting: int      # °F - User target temperature (121°F)
outside_temperature: int          # °F - External sensor (often 0°F)

# Heat pump system sensors (0.1°F units - divide by 10) - CORRECTED
tank_upper_temperature: int       # 0.1°F - **Cold water inlet/evaporator temp** (~605 = 60.5°F)
tank_lower_temperature: int       # 0.1°F - **Heat pump ambient temperature** (~611 = 61.1°F)
discharge_temperature: int        # 0.1°F - Heat pump discharge temp (~761 = 76.1°F)
ambient_temperature: int          # 0.1°F - System ambient with offset (~238 = 23.8°F raw)
```

**MISSING**: API does not expose actual hot water tank internal temperatures. Tank thermal state must be inferred from `dhw_charge_percent`.

#### Operation Mode Codes (Heat Pump Water Heater) ✅ **PRODUCTION VALIDATED**
Based on extensive production data analysis:
- **Mode 0**: Standby/Off - No active heating (1W power consumption)
- **Mode 32**: Heat Pump Active - Efficient operation (430-470W power)
- **Mode 33**: Electric Elements Only - Backup heating (4000W+) [*inferred from documentation*]
- **Mode 34**: Hybrid Mode - Heat pump + electric (mixed power) [*inferred from documentation*]

**Note**: Original assumption about mode 1-3 was incorrect. Production system uses mode 0 and 32 primarily.

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
from navien_nwp500 import NaviLinkClient
from navien_nwp500.aws_iot_websocket import ReconnectConfig

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

### Power Consumption Patterns (Production Validated) ✅
- **Standby Operation**: 1W (mode 0 - no heating active)
- **Heat Pump Operation**: 430-470W (mode 32 - compressor + evaporator fan)
- **Resistance Heating**: 4000W+ (backup electric elements - not observed in production data) 
- **Efficiency Indicator**: Heat pump mode provides 8-10x efficiency vs resistance heating
- **Alert Conditions**:
  - `error_code != 0`: System fault requiring attention
  - `dhw_charge_percent < 20`: Low hot water availability warning  
  - `current_inst_power > 4000W`: Unexpected electric heating activation
  - `device_connected == 0`: Device offline - MQTT will not respond
  - `operation_mode` transitions indicate heating demand patterns

### CSV Data Logging (Production Format) ✅ **VALIDATED**
```csv
timestamp,dhw_charge_percent,operation_mode,dhw_temperature,current_inst_power,tank_upper_temp,tank_lower_temp
2025-09-26T22:18:03,99,32,121,466,60.5,61.0
2025-09-26T22:33:23,100,0,122,1,61.0,61.5
```

**PRODUCTION INSIGHTS**: 
- Tank charge remained 99-100% (at capacity)
- Mode alternated between 0 (standby) and 32 (heat pump)  
- Power consumption: 1W standby, 466W heat pump active
- "Tank" temperatures are cold water system sensors (~60-61°F), NOT hot water tank sensors
- DHW charge percentage is the primary tank thermal state indicator

### Extended Production Analysis (Latest Findings) ✅

#### Temperature Sensor Reality Check
**CRITICAL DISCOVERY**: Field names are misleading based on extensive production data:
- **`dhw_temperature`**: Only true hot water sensor (121-122°F actual delivery temperature)
- **`tank_upper_temperature`**: Actually cold water inlet/evaporator sensor (~60.5°F) 
- **`tank_lower_temperature`**: Actually heat pump ambient sensor (~61.1°F)
- **Missing**: Hot water tank internal temperatures NOT accessible via NaviLink API
- **Implication**: Tank thermal monitoring must rely on `dhw_charge_percent` only

#### Heat Source Status vs Reality
**IMPORTANT**: Status codes indicate readiness, not active operation!
- Production data shows `heat_upper_use=1`, `heat_lower_use=1` (ready) but power shows not active
- `comp_use=2`, `eva_fan_use=2` correlates with actual 466W heat pump power draw
- **Rule**: Trust power consumption over status codes for actual operation determination

#### Mode Transition Patterns (Production Observed)
- **Mode 0 → 32 → 0**: Normal heating cycle pattern
- **Power correlation**: Mode 0 = 1W, Mode 32 = 430-470W
- **Frequency**: 40-second monitoring intervals showed regular mode cycling
- **Efficiency**: System prefers heat pump (mode 32) over electric backup

#### Connectivity and MQTT Reliability  
- **Critical**: Device must show online in `/device/connectivity-status` for MQTT responses
- **Observation**: Offline devices receive MQTT commands but never respond
- **Recommendation**: Always check connectivity before starting monitoring sessions

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
from navien_nwp500 import NaviLinkClient
from navien_nwp500.aws_iot_websocket import ReconnectConfig

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
- **Python Compatibility**: 3.9+ (async/await required, Python 3.8 support removed)

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
- **Python Compatibility**: 3.9+ (async/await required, Python 3.8 support removed)
## Critical Code Maintenance Notes ⚠️

### Temperature Sensor Field Names (DO NOT "FIX")
**IMPORTANT**: Do NOT rename misleading field names in the data models! They must match the actual API response fields exactly:
- Keep `tank_upper_temperature` and `tank_lower_temperature` as-is
- Use clear documentation comments explaining they are NOT tank temperatures
- Provide helper methods for proper temperature interpretation

### Status vs Power Consumption Logic
Always implement power consumption checking over status codes for actual operation detection:
```python
# Correct way to detect heat pump operation
if status.operation_mode == 32 and status.current_inst_power > 400:
    # Heat pump actively heating
elif status.operation_mode == 0 and status.current_inst_power <= 10:
    # Standby mode
```

### Device Connectivity Checking
Always check device connectivity before MQTT operations:
```python
connectivity = await device.get_connectivity_status()
if not connectivity.get('device_connected'):
    logger.warning("Device offline - MQTT monitoring not possible")
    return False
```

### CSV Schema Stability
Maintain CSV field order for data continuity across monitoring sessions:
```csv
timestamp,dhw_charge_percent,operation_mode,dhw_temperature,current_inst_power,...
```

## Production Validation Status ✅

All core functionality has been validated against real hardware:
- ✅ **Authentication**: Email/password login with session management
- ✅ **Device Discovery**: REST API device listing and info
- ✅ **MQTT Connection**: AWS IoT WebSocket with proper signing
- ✅ **Data Streaming**: Real-time status updates via binary MQTT
- ✅ **Tank Monitoring**: DHW charge percentage tracking (primary metric)
- ✅ **Mode Detection**: Heat pump (432W) vs standby (1W) operation
- ✅ **Error Handling**: Connection recovery, device offline handling
- ✅ **Long-term Stability**: Multi-hour monitoring sessions
- ✅ **Data Accuracy**: 40-second polling with consistent results

**Hardware Tested**: Navien NWP500 Heat Pump Water Heater (50-gallon, 4.5kW heat pump, 4.5kW electric backup)
**Monitoring Duration**: 24+ hours of continuous operation validated
**Data Points**: 35+ CSV entries with consistent sensor readings
