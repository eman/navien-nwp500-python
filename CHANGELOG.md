# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial public release
- Complete REST API integration with NaviLink cloud service
- Real-time MQTT monitoring via AWS IoT WebSocket
- Device control capabilities (temperature, DHW mode, on/off)
- Async/await support throughout the library
- CSV data export for long-term analysis
- Home Assistant integration support
- Comprehensive error handling and connection recovery
- Multi-platform wheel support (Linux, Windows, macOS, ARM64)

### Hardware Validated
- Navien NWP500 Heat Pump Water Heater (65-gallon, 4.5kW heat pump)
- 24+ hours continuous operation testing
- Real-world production data collection and analysis

## [1.0.0] - 2024-01-XX

### Added
- Production-ready library for Navien NWP500 Heat Pump Water Heaters
- Enterprise authentication and session management
- Real-time tank monitoring with validated field interpretations  
- Complete device control via REST API and MQTT
- Production examples with CSV export and monitoring statistics
- Comprehensive documentation and API reference

[Unreleased]: https://github.com/eman/navien-nwp500-python/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/eman/navien-nwp500-python/releases/tag/v1.0.0
