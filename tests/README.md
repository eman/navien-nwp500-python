# NaviLink Parser Tests

This directory contains comprehensive tests for the NaviLink Python library, including parser validation tests based on real HAR file data.

## Test Structure

### Core Tests
- `test_models.py` - Data model validation and serialization
- `test_config.py` - Configuration management tests
- `test_client.py` - Client functionality tests
- `test_device.py` - Device management tests
- `test_exceptions.py` - Exception handling tests

### HAR-Based Parser Tests 
- `test_har_integration.py` - **NEW**: Parser validation using real API responses
- `test_parser_validation.py` - Comprehensive parser structure validation

### Integration Tests
- `test_integration.py` - End-to-end integration tests
- `test_simple.py` - Simple functionality verification

## HAR-Based Parser Testing

### Overview
The HAR-based tests validate that our parsers correctly handle real API responses from the NaviLink service. These tests use sanitized data extracted from HTTP Archive (HAR) files captured during actual device interactions.

### Data Extraction Process
1. **HAR File Capture**: HTTP/WebSocket traffic captured using HTTP Toolkit
2. **Data Sanitization**: Sensitive data (MAC addresses, tokens, emails) automatically sanitized
3. **Test Fixture Generation**: Sanitized data converted to JSON test fixtures
4. **Parser Validation**: Tests verify parsers handle real-world data structures

### Key Test Files

#### `tests/fixtures/har_test_data.json`
Contains sanitized API responses and MQTT messages:
- **API Responses**: 7 different endpoint responses (sign-in, device-list, etc.)
- **MQTT Messages**: 45 real device status messages from production monitoring
- **Data Safety**: All sensitive data sanitized (MAC addresses → `aabbccddeeff`, tokens → `REDACTED_TOKEN_*`)

#### `tests/test_har_integration.py`
Core parser validation tests:

```python
# Test API response parsing
def test_authentication_response_structure()    # Login response validation
def test_device_list_response_structure()       # Device discovery validation

# Test MQTT message parsing  
def test_mqtt_status_messages_structure()       # WebSocket/MQTT structure
def test_device_status_model_compatibility()    # DeviceStatus model creation
def test_production_data_validation()           # Real-world data range validation

# Test data sanitization
def test_mac_addresses_sanitized()              # Verify MAC address safety
def test_user_info_sanitized()                  # Verify user data safety
```

### Production Data Insights Validated

#### API Endpoints Tested
- `POST /user/sign-in` - Authentication with AWS IoT credentials
- `POST /device/list` - Device discovery and enumeration  
- `POST /device/info` - Detailed device information
- `GET /device/tou` - Time-of-use electricity rate data
- `POST /device/firmware/info` - Firmware version information

#### MQTT Device Status Fields
- **Core Status**: `errorCode`, `operationMode`, `dhwChargePer`, `currentInstPower`
- **Temperatures**: `dhwTemperature`, `tankUpperTemperature`, `tankLowerTemperature`
- **Heat Sources**: `compUse`, `heatUpperUse`, `heatLowerUse`, `evaFanUse`
- **System Info**: `wifiRssi`, `dhwTemperatureSetting`, `operationBusy`

#### Production Data Ranges Validated
- **Operation Modes**: 0 (standby), 32 (heat pump), 64, 96 (extended modes)
- **DHW Charge**: 0-100% tank thermal capacity
- **Power Consumption**: 1W (standby) to 400W+ (heat pump active)
- **Temperature Ranges**: 70-140°F for hot water delivery

### Running HAR-Based Tests

```bash
# Run all HAR integration tests
pytest tests/test_har_integration.py -v

# Run specific test categories
pytest tests/test_har_integration.py::TestHarApiResponses -v
pytest tests/test_har_integration.py::TestHarMqttData -v

# Run parser validation tests  
pytest tests/test_parser_validation.py -v
```

### Test Coverage Results

The HAR-based tests provide validation for:
- ✅ **Authentication Response Parsing** - JWT tokens, AWS IoT credentials
- ✅ **Device Discovery Parsing** - Device list, location, connection status  
- ✅ **MQTT Status Parsing** - Real-time device status, sensor readings
- ✅ **Data Model Compatibility** - DeviceStatus object creation from real data
- ✅ **Production Data Validation** - Operational ranges, mode patterns
- ✅ **Field Mapping Verification** - camelCase API ↔ snake_case models

### Data Safety & Privacy

#### Sanitization Applied
- **MAC Addresses**: `04786332fca0` → `aabbccddeeff`
- **Email Addresses**: `user@domain.com` → `test@example.com`
- **User IDs**: Real IDs → `test_user_123`
- **Authentication Tokens**: JWT tokens → `REDACTED_TOKEN_[length]`
- **AWS Credentials**: Access keys → `REDACTED_TOKEN_*`

#### What's Preserved
- **API Response Structure** - Complete JSON schema and nesting
- **Field Names** - All original field names maintained  
- **Data Types** - Integer, string, boolean types preserved
- **Value Ranges** - Realistic ranges for temperatures, percentages, etc.
- **Operational Patterns** - Real device behavior and state transitions

### Benefits for Development

1. **Real-World Validation**: Tests use actual production API responses
2. **Field Mapping Verification**: Ensures camelCase ↔ snake_case conversions work  
3. **Data Range Validation**: Confirms expected ranges for sensor readings
4. **Model Compatibility**: Verifies DeviceStatus models handle real data
5. **Parser Robustness**: Tests edge cases from production usage
6. **Regression Prevention**: Catches parsing issues before deployment

### Future Enhancements

- **Additional Device Types**: Expand beyond NWP500 water heater
- **Error Condition Testing**: Add HAR data for error scenarios  
- **Control Command Testing**: Include device control command responses
- **Energy Usage Testing**: Add energy usage query responses
- **Multi-Device Testing**: Test parsing for multiple device configurations

This HAR-based testing approach ensures our parsers handle real-world data correctly while maintaining complete data privacy and security.