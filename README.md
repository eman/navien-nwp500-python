# Navien NWP500 Python Library

Control and monitor your Navien NWP500 Heat Pump Water Heater remotely using Python. This library provides complete access to the NaviLink cloud service, enabling real-time monitoring, device control, and data collection.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://badge.fury.io/py/navien-nwp500.svg)](https://badge.fury.io/py/navien-nwp500)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/eman/navien-nwp500-python/workflows/Tests/badge.svg)](https://github.com/eman/navien-nwp500-python/actions)

## Features

- **🔧 Device Control**: Change temperature settings, DHW modes, and turn your water heater on/off
- **📊 Real-time Monitoring**: Get live data on tank charge level, temperature, power consumption, and operation modes  
- **⚡ Async/Await Support**: Built for modern Python with full async support
- **🏠 Home Assistant Ready**: Perfect for creating custom Home Assistant integrations
- **📈 Data Export**: Built-in CSV logging for long-term analysis
- **🔒 Production Ready**: Comprehensive error handling and connection recovery

## Installation

```bash
pip install navien-nwp500
```

## Quick Start

### 1. Setup Credentials

Create a `.env` file with your NaviLink account details:

```bash
NAVILINK_EMAIL=your_email@example.com
NAVILINK_PASSWORD=your_password
```

### 2. Basic Usage

```python
import asyncio
from navien_nwp500 import NaviLinkClient, NaviLinkConfig

async def main():
    # Load credentials from .env file
    config = NaviLinkConfig.from_environment()
    
    async with NaviLinkClient(config=config) as client:
        # Connect to your water heater
        await client.authenticate(config.email, config.password)
        devices = await client.get_devices()
        device = devices[0]  # Your water heater
        
        # Get current status
        status = await device.get_status()
        print(f"Tank Level: {status.dhw_charge_per}%")
        print(f"Temperature: {status.dhw_temperature}°F")
        print(f"Power Usage: {status.current_inst_power}W")
        
        # Control your water heater
        await device.set_temperature(120)  # Set to 120°F
        await device.set_dhw_mode(1)       # Set DHW mode

asyncio.run(main())
```

## Key Features

### Device Control
```python
# Change temperature
await device.set_temperature(125)

# Change DHW mode (0=Off, 1=Heat Pump, 2=Electric, 3=Hybrid)
await device.set_dhw_mode(1)

# Turn on/off
await device.turn_on()
await device.turn_off()
```

### Real-time Monitoring
```python
# Start live monitoring with automatic reconnection
mqtt_conn = await device.get_mqtt_connection()
await mqtt_conn.connect()

def on_status_update(status):
    print(f"Tank: {status.dhw_charge_per}% | Temp: {status.dhw_temperature}°F")

mqtt_conn.set_status_callback(on_status_update)
await mqtt_conn.start_monitoring(polling_interval=60)  # Update every minute
```

### Data Export
```python
# CSV logging for analysis
import csv
from datetime import datetime

def log_to_csv(status):
    with open('tank_data.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            status.dhw_charge_per,
            status.dhw_temperature,
            status.operation_mode,
            status.current_inst_power
        ])
```

## Understanding Your Data

### Tank Charge Level
The `dhw_charge_per` field (0-100%) shows how much thermal energy is stored in your tank. This is the best indicator of available hot water - not the temperature sensors.

### Operation Modes
- **Mode 0**: Standby (~1W) - No heating
- **Mode 32**: Heat Pump (~450W) - Efficient heating  
- **Mode 33**: Electric Elements (~4000W) - Backup heating
- **Mode 34**: Hybrid - Both heat pump and electric

### Power Consumption
Monitor `current_inst_power` to see energy usage in real-time. Heat pump mode is 8-10x more efficient than electric backup.

## Home Assistant Integration

Perfect for custom Home Assistant components:

```python
# In your Home Assistant component
REQUIREMENTS = ["navien-nwp500>=1.0.0"]

from navien_nwp500 import NaviLinkClient, NaviLinkConfig

async def async_setup_entry(hass, config_entry):
    config = NaviLinkConfig(
        email=config_entry.data["email"],
        password=config_entry.data["password"]
    )
    
    client = NaviLinkClient(config=config)
    await client.authenticate(config.email, config.password)
    
    # Store client in hass.data for use by entities
    hass.data[DOMAIN] = {"client": client}
    return True
```

## Requirements

- Python 3.8+
- Navien NWP500 Heat Pump Water Heater
- NaviLink account (set up through Navien mobile app)
- Stable internet connection

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b my-new-feature`
3. Make your changes and add tests
4. Run the test suite: `pytest tests/`
5. Submit a pull request

## Support

- **Documentation**: [API Reference](docs/README.md)
- **Issues**: [GitHub Issues](https://github.com/eman/navien-nwp500-python/issues)
- **Discussions**: [GitHub Discussions](https://github.com/eman/navien-nwp500-python/discussions)

## Hardware Compatibility

**Tested**: Navien NWP500 Heat Pump Water Heater  
**Likely Compatible**: Other Navien water heaters with NaviLink support (untested)

If you test with other models, please report your results!
