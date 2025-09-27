# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-09-27

### 🎉 Initial Production Release

#### Added
- **Complete MQTT Integration**: Real-time device communication via AWS IoT Core
- **Tank Monitoring**: Production-ready tank monitoring with CSV export (`tank_monitoring_production.py`)
- **Device Control**: Full device control capabilities (temperature, mode, on/off)
- **HAR-Based Testing**: Comprehensive parser validation using real API responses
- **Configuration Management**: Enterprise .env-based configuration system
- **Production Examples**: Working examples for monitoring and device control

#### Core Features
- **NaviLinkClient**: Main client with session management and authentication
- **NaviLinkDevice**: Device abstraction with MQTT integration
- **AWS IoT WebSocket**: MQTT3/MQTT5 support with connection recovery
- **DeviceStatus Model**: Complete data model with 80+ device status fields
- **Exception Handling**: Comprehensive custom exception hierarchy

#### Monitoring Capabilities
- DHW (Domestic Hot Water) charge percentage tracking
- Heat pump operation mode detection (Mode 0: Standby, Mode 32: Active)
- Power consumption monitoring (1W standby, 400W+ heat pump)
- Temperature sensor readings (hot water delivery, system sensors)
- WiFi connectivity and signal strength monitoring
- Error code detection and reporting

#### Device Control
- Temperature setting adjustment (70°F - 140°F range)
- Operation mode switching (Heat Pump, Electric, Hybrid)
- Device on/off control
- Vacation mode configuration
- Schedule management (future enhancement)

#### Technical Highlights
- **Async Python**: Full asyncio implementation for concurrent operations
- **Type Safety**: Complete type hints and dataclass models
- **Error Recovery**: Exponential backoff and connection retry logic
- **Production Logging**: Structured logging with configurable levels
- **Test Coverage**: HAR-validated parsers and integration tests
- **Documentation**: Comprehensive API docs and usage examples

#### Security & Privacy
- No hardcoded credentials or sensitive data
- Secure AWS IoT authentication with proper signature generation
- Sanitized test data and examples
- .env template for secure credential management

#### Supported Hardware
- Navien NWP500 Heat Pump Water Heater (50-gallon, validated)
- Compatible with NaviLink smart control service
- Supports residential installation types

#### Python Compatibility
- Python 3.8+ support
- Tested on Python 3.9, 3.10, 3.11, 3.12, 3.13
- Cross-platform compatibility (Windows, macOS, Linux)

## [Unreleased]

### Planned Features
- Additional device type support (tankless water heaters)
- Energy usage analytics and reporting
- Home Assistant integration
- Advanced scheduling and automation features

[Unreleased]: https://github.com/eman/navien-nwp500-python/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/eman/navien-nwp500-python/releases/tag/v1.0.0
