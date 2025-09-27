# NaviLink Examples

This directory contains examples demonstrating various usage patterns of the NaviLink Python library.

## Prerequisites

Before running any examples, ensure you have:

1. **Installed the library**:
   ```bash
   pip install navilink
   ```

2. **Set up credentials** (choose one method):

   **Option A: Environment Variables (Recommended)**
   ```bash
   export NAVILINK_EMAIL="your@email.com"
   export NAVILINK_PASSWORD="your_password"
   export NAVILINK_LOG_LEVEL="INFO"
   ```

   **Option B: Command Line Arguments**
   ```bash
   python example.py --email "your@email.com" --password "password"
   ```

   **Option C: Credentials File**
   ```bash
   cp credentials_template.py credentials.py
   # Edit credentials.py with your actual credentials
   ```

## Examples

### [basic_usage.py](basic_usage.py) - Getting Started ⭐

**Best for**: First-time users learning the library basics

```bash
python basic_usage.py
```

**Features**:
- Simple authentication
- Device discovery
- Single status request via MQTT
- Basic error handling
- Operation mode interpretation

**Output Example**:
```
🔐 Authenticating...
✅ Authentication successful
📱 Getting device list...
🏠 Found device: NWP500
📊 Status received:
   Tank Charge: 95%
   Temperature: 121°F
   System Status: Heat Pump Active
```

### [tank_monitoring_production.py](tank_monitoring_production.py) - Production Monitoring 🏭

**Best for**: Continuous monitoring and data logging in production environments

```bash
python tank_monitoring_production.py --interval 300 --output tank_data.csv
```

**Features**:
- Enterprise configuration management
- Continuous MQTT monitoring with 5-minute intervals
- CSV data logging for analysis
- Connection recovery with exponential backoff
- Production-grade error handling and logging
- Graceful shutdown with signal handling
- Connection stability monitoring

**Output Example**:
```
📊 Tank: 99% | Temp: 121°F | Mode: 32 | Power: 466W
📊 Tank: 100% | Temp: 122°F | Mode: 0 | Power: 1W
⚠️ No updates received in 10 minutes, connection may be stale
```

**CSV Output**:
```csv
timestamp,dhw_charge_percent,operation_mode,dhw_temperature,current_inst_power
2024-01-01T10:30:00,99,32,121,466
2024-01-01T10:35:00,100,0,122,1
```

**⚠️ Never commit credentials.py to version control!**

## Data Analysis

### Understanding CSV Output

The production monitoring script outputs data with proper field interpretations:

- **`dhw_charge_percent`**: Tank thermal energy level (0-100%) - PRIMARY TANK METRIC
- **`dhw_temperature`**: Hot water output temperature (°F) - ACTUAL hot water temp
- **`tank_upper_temp`**: Cold water inlet temperature (°F) - NOT tank temp!
- **`tank_lower_temp`**: Heat pump ambient temperature (°F) - NOT tank temp!
- **`operation_mode`**: Heat pump mode (0=Standby, 32=Heat Pump, 33=Electric)
- **`current_inst_power`**: Power consumption (W) - Key efficiency indicator

### Critical Production Insights

1. **Tank Monitoring**: Use `dhw_charge_percent` (not temperature sensors) for tank state
2. **Mode Detection**: Trust power consumption over status codes for actual operation  
3. **Temperature Reality**: "Tank" sensors are cold water system sensors (~60°F), not hot water
4. **Efficiency**: Heat pump mode (32) uses 430-470W vs electric backup 4000W+

## Sample Data Analysis

```python
import pandas as pd
import matplotlib.pyplot as plt

# Load and analyze data
df = pd.read_csv('tank_data.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Plot tank charge over time
plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['dhw_charge_percent'])
plt.title('Tank Thermal Energy Level Over Time')
plt.ylabel('DHW Charge (%)')
plt.xlabel('Time')
plt.grid(True)
plt.show()

# Analyze power consumption patterns
power_modes = df.groupby('operation_mode')['current_inst_power'].agg(['mean', 'count'])
print("Power consumption by operation mode:")
print(power_modes)
```

## Debugging

### Debug Scripts
The `debug/` directory contains development debugging tools:
- `debug_aws_creds.py` - AWS IoT credential debugging
- `debug_websocket.py` - WebSocket connection debugging

### Connectivity Issues
1. Check device online status first
2. Verify credentials and authentication
3. Enable debug logging: `--debug` or `NAVILINK_DEBUG=true`
4. Check WiFi signal strength in device data

### Common Issues
- **Empty CSV**: Device offline or MQTT not responding
- **403 Errors**: Authentication expired or invalid
- **Connection Timeouts**: Check device connectivity status first

## Support

For issues or questions:
1. Check the main project README.md
2. Review production validation in `.github/copilot-instructions.md`  
3. Examine HAR files in `reference/` directory for API details