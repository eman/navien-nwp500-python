# NaviLink Examples

This directory contains example scripts demonstrating how to use the NaviLink Python library.

## Configuration

All examples use a standardized configuration approach:

1. **Copy the template**: `cp .env.template .env`
2. **Edit .env** with your actual credentials:
   ```bash
   NAVILINK_EMAIL=your_email@example.com
   NAVILINK_PASSWORD=your_password
   NAVILINK_POLLING_INTERVAL=300  # Optional: 5 minutes default
   ```
3. **Run examples** - they will automatically load from .env

Alternatively, you can:
- Set environment variables: `export NAVILINK_EMAIL="..." NAVILINK_PASSWORD="..."`
- Use command line arguments (see `--help` for each example)

## Examples

### basic_usage.py
**Perfect for getting started**

Demonstrates basic authentication, device discovery, and status retrieval.
- Shows how to connect to devices
- Retrieves device information and status
- Checks device connectivity
- Explains key metrics like DHW charge percentage and operation modes

```bash
python examples/basic_usage.py
# or with debug logging
python examples/basic_usage.py --debug
```

### tank_monitoring_production.py
**Production-ready monitoring for long-term data collection**

Designed for continuous monitoring of heat pump water heater operations.
- Monitors DHW (Domestic Hot Water) charge levels
- Tracks operation modes and power consumption
- Logs data to CSV files for analysis
- Robust error handling and reconnection
- Configurable polling intervals

```bash
# Standard 5-minute monitoring
python examples/tank_monitoring_production.py

# Custom intervals and duration
python examples/tank_monitoring_production.py --interval 60 --duration 120

# Monitor for 24 hours with 10-minute intervals
python examples/tank_monitoring_production.py --interval 600 --duration 1440
```

## Key Concepts

### DHW Charge Percentage
The most important metric for tank monitoring. Represents the thermal energy level in the hot water tank as a percentage of maximum capacity (0-100%).

### Operation Modes (Heat Pump Water Heater)
- **Mode 0**: Standby/Off (1W power consumption)
- **Mode 32**: Heat Pump Active (430-470W power consumption) 
- **Mode 33**: Electric Elements Only (4000W+ power consumption)
- **Mode 34**: Hybrid Mode (mixed power consumption)

### Temperature Sensors
- **dhw_temperature**: Actual hot water output temperature (°F)
- **dhw_temperature_setting**: Target temperature setpoint (°F)
- **tank_upper_temperature**: Cold water inlet sensor (0.1°F units)
- **tank_lower_temperature**: Heat pump ambient sensor (0.1°F units)

## Troubleshooting

### Authentication Issues
- Verify credentials in .env file
- Check that NAVILINK_EMAIL and NAVILINK_PASSWORD are set correctly
- Try command line arguments to test: `--email user@example.com --password yourpass`

### Device Offline
- Check device connectivity with `basic_usage.py` first
- Ensure device is powered on and connected to WiFi
- MQTT monitoring requires device to be online

### Empty CSV Files
- Device must be online for data collection
- Check connectivity status before starting monitoring
- Enable debug mode to see detailed connection logs

## Data Analysis

The production monitoring example generates CSV files perfect for analysis:

```python
import pandas as pd
import matplotlib.pyplot.plt

# Load and analyze tank data
df = pd.read_csv('tank_data_production.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Plot DHW charge over time
plt.figure(figsize=(12, 6))
plt.plot(df['timestamp'], df['dhw_charge_percent'])
plt.title('DHW Tank Charge Level Over Time')
plt.ylabel('Charge Percentage (%)')
plt.xlabel('Time')
plt.grid(True)
plt.show()
```

## Additional Resources

- See `docs/` directory for complete API documentation
- `docs/DEVICE_DATA_SCHEMA.md` - Complete field definitions and units
- `docs/FIELD_INSIGHTS.md` - Production data analysis insights
- GitHub Issues for bug reports and feature requests