# MQTT5 Enhanced Implementation

## Overview

The NaviLink library has been enhanced with MQTT5 support and advanced resilience features while maintaining backward compatibility. This implementation provides production-ready monitoring capabilities with automatic reconnection, enhanced error handling, and comprehensive statistics.

## Key Enhancements

### 1. MQTT5 Support with MQTT3 Fallback
- **Enhanced AWS IoT WebSocket Connection**: Uses MQTT5 when available, automatically falls back to MQTT3
- **Backward Compatibility**: All existing code continues to work without changes
- **Performance Improvements**: Better connection management and error handling

### 2. Advanced Connection Management
- **Connection State Tracking**: Detailed state management (DISCONNECTED, CONNECTING, CONNECTED, RECONNECTING, FAILED)
- **Automatic Reconnection**: Configurable exponential backoff with jitter
- **Connection Health Monitoring**: Continuous monitoring with automatic recovery
- **Enhanced Timeouts**: Configurable timeouts for all operations

### 3. Resilience Features
- **Exponential Backoff**: Intelligent retry logic with configurable parameters
- **Error Recovery**: Graceful handling of connection interruptions
- **Jitter Support**: Randomization to prevent thundering herd problems
- **Max Retry Limits**: Configurable limits to prevent infinite retry loops

### 4. Enhanced Monitoring and Statistics
- **Real-time Statistics**: Message counts, connection metrics, uptime tracking
- **Connection Health**: Monitoring of reconnection attempts and success rates
- **Performance Metrics**: Detailed logging and statistics collection

## New Configuration Options

### ReconnectConfig
```python
from navilink.mqtt import ReconnectConfig

config = ReconnectConfig(
    max_retries=20,           # Maximum reconnection attempts
    initial_delay=2.0,        # Initial delay between retries (seconds)
    max_delay=120.0,          # Maximum delay between retries (seconds)
    backoff_multiplier=1.5,   # Exponential backoff multiplier
    jitter=True               # Add randomization to delays
)
```

### Enhanced Device Connection
```python
# Get MQTT connection with enhanced configuration
mqtt_conn = await device.get_mqtt_connection(reconnect_config=config)

# Connect with auto-reconnect enabled
await mqtt_conn.connect(enable_auto_reconnect=True)

# Check connection statistics
stats = mqtt_conn.statistics
print(f"Messages received: {stats['messages_received']}")
print(f"Reconnection count: {stats['reconnection_count']}")
print(f"Uptime: {stats['uptime_seconds']} seconds")
```

## Enhanced Tank Monitoring Example

The new `examples/tank_monitoring_enhanced.py` demonstrates:

### Features
- **Long-term Monitoring**: Designed for continuous operation (hours to days)
- **Automatic Recovery**: Handles network interruptions gracefully
- **CSV Logging**: Comprehensive data logging with timestamps
- **Statistics Tracking**: Connection health and performance metrics
- **Configurable Polling**: Adjustable polling intervals (default: 5 minutes)

### Usage
```bash
# Run indefinitely with 5-minute polling
python examples/tank_monitoring_enhanced.py

# Run for 24 hours with 2-minute polling
python examples/tank_monitoring_enhanced.py --hours 24 --interval 120

# Enable verbose logging for debugging
python examples/tank_monitoring_enhanced.py --verbose
```

### CSV Output
The enhanced monitoring creates CSV files with the following columns:
- `timestamp`: ISO format timestamp
- `dhw_charge_percent`: Tank charge level (0-100%)
- `dhw_temperature_f`: Current water temperature (°F)
- `dhw_temperature_setting_f`: Target temperature setting (°F)
- `operation_mode`: Numeric operation mode
- `operation_mode_description`: Human-readable operation mode
- `dhw_use`: Hot water usage indicator
- `error_code` / `sub_error_code`: Error information
- `wifi_rssi`: WiFi signal strength (dBm)
- `connection_state`: MQTT connection state
- `messages_received` / `messages_sent`: Message statistics
- `reconnection_count`: Number of reconnections
- `uptime_seconds`: Connection uptime

## Operation Modes

The system now includes comprehensive operation mode mapping:
- **0**: Standby
- **1**: Heat Pump Only (efficient operation)
- **2**: Resistive Element Only (backup heating)
- **3**: Heat Pump + Resistive Element (high demand)
- **4**: Defrost Mode (heat pump maintenance)
- **5**: Error Mode (fault condition)
- **6**: Maintenance Mode

## Connection States

Enhanced connection state tracking:
- **DISCONNECTED**: Not connected
- **CONNECTING**: Initial connection attempt
- **CONNECTED**: Successfully connected and operational
- **RECONNECTING**: Attempting to reconnect after failure
- **FAILED**: Connection failed (manual intervention may be required)

## Best Practices for Long-term Monitoring

### 1. Configuration
```python
# Recommended configuration for long-term monitoring
reconnect_config = ReconnectConfig(
    max_retries=20,        # Allow many retries for network issues
    initial_delay=2.0,     # Quick initial retry
    max_delay=120.0,       # Cap at 2 minutes between retries
    backoff_multiplier=1.5, # Gentle exponential backoff
    jitter=True            # Prevent synchronized retries
)
```

### 2. Monitoring Setup
```python
# Use 5-minute polling for tank charge monitoring
polling_interval = 300  # 5 minutes = 300 seconds

# This provides good balance of:
# - Responsiveness to changes
# - Reduced network traffic
# - Battery/power efficiency
```

### 3. Error Handling
The enhanced implementation includes robust error handling:
- Connection failures are automatically retried
- Polling errors don't stop monitoring
- Statistics help identify connection issues
- Graceful degradation under poor network conditions

### 4. Data Collection
- CSV files are flushed regularly to prevent data loss
- Timestamps are in ISO format for easy parsing
- All relevant metrics are logged for analysis
- File size monitoring prevents runaway log growth

## Testing

A comprehensive test suite is available:

```bash
# Test basic MQTT5 functionality
python test_mqtt5_enhanced.py

# Quick connection test
python test_basic_auth.py

# Enhanced monitoring test (short duration)
python examples/tank_monitoring_enhanced.py --hours 1 --interval 30
```

## Performance Improvements

### Connection Efficiency
- Reused event loop groups and client bootstrap
- Connection pooling for better resource utilization
- Enhanced timeout management
- Reduced connection overhead

### Message Handling
- Asynchronous message processing
- Improved error recovery
- Better queue management
- Enhanced callback handling

### Monitoring Performance
- Fire-and-forget polling (doesn't wait for responses)
- Configurable polling intervals
- Efficient subscription management
- Optimized topic patterns

## Migration Guide

### From Basic Implementation
Existing code continues to work without changes. To use enhanced features:

```python
# Before
device = devices[0]
await device.connect()
await device.start_monitoring()

# After (enhanced)
reconnect_config = ReconnectConfig(max_retries=10)
mqtt_conn = await device.get_mqtt_connection(reconnect_config=reconnect_config)
await mqtt_conn.connect(enable_auto_reconnect=True)
await mqtt_conn.start_monitoring(polling_interval=300)
```

### Configuration Updates
No breaking changes - all enhancements are additive:
- Existing timeout values are preserved
- Default behavior remains the same
- New features are opt-in

## Troubleshooting

### Connection Issues
1. Check connection state: `mqtt_conn.connection_state`
2. Review statistics: `mqtt_conn.statistics`
3. Enable verbose logging: `--verbose` flag
4. Monitor reconnection attempts in logs

### Performance Issues
1. Adjust polling interval based on requirements
2. Monitor message statistics for bottlenecks  
3. Check network conditions and WiFi signal strength
4. Review CSV file size growth

### Data Quality
1. Verify polling interval is appropriate for use case
2. Check for gaps in CSV data indicating connection issues
3. Monitor error codes for device problems
4. Review operation mode changes for system behavior

## Future Enhancements

Potential future improvements:
1. **Full MQTT5 Features**: Complete MQTT5 feature implementation when SDK stabilizes
2. **Advanced Analytics**: Built-in data analysis and trend detection
3. **Alerting System**: Configurable alerts for error conditions
4. **Dashboard Integration**: Real-time monitoring dashboard
5. **Cloud Storage**: Direct integration with cloud storage services
6. **Machine Learning**: Predictive analytics for maintenance scheduling

## Dependencies

- `awsiotsdk>=1.21.0`: AWS IoT SDK with MQTT5 support
- `aiohttp>=3.8.0`: Async HTTP client
- `cryptography>=3.4.0`: Cryptographic operations
- Standard library: `asyncio`, `logging`, `csv`, `dataclasses`