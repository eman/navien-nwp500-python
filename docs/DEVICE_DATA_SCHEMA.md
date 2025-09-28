# NaviLink Device Data Schema

This document defines all data fields available from NaviLink devices, their units, ranges, and meanings. The data is primarily from Navien NWP500 Heat Pump Water Heater but should apply to other Navien smart water heating systems.

## Data Collection Methods

Data can be retrieved through two methods:
1. **REST API** - Basic device information and connectivity status
2. **MQTT Real-time** - Comprehensive operational data and sensor readings

## Field Definitions

### Core Status Fields

| Field | Unit | Range | Description | Notes |
|-------|------|-------|-------------|-------|
| `dhw_charge_percent` | % | 0-100 | Domestic Hot Water tank charge level | Tank energy/heat content relative to maximum |
| `operation_mode` | code | varies | Current operational mode | See Operation Mode Codes below |
| `dhw_temperature` | °F | 32-180 | Current hot water outlet temperature | Temperature at water heater output |
| `dhw_temperature_setting` | °F | 80-140 | Target hot water temperature setting | User-configured setpoint |

### Temperature Sensors ⚠️ CRITICAL: Misleading Field Names

**IMPORTANT**: Fields named "tank_temperature" do NOT measure hot water tank temperatures!

| Field | Unit | Range | Description | Notes |
|-------|------|-------|-------------|-------|
| `tank_upper_temperature` | 0.1°F | 320-1800 | **Heat pump evaporator/inlet temperature** | **NOT hot water tank!** Divide by 10 |
| `tank_lower_temperature` | 0.1°F | 320-1800 | **Heat pump ambient temperature** | **NOT hot water tank!** Divide by 10 |
| `discharge_temperature` | 0.1°F | 320-1800 | Heat pump discharge/condenser temperature | Divide by 10 for actual °F |
| `ambient_temperature` | °C | -40-50 | **Ambient air temperature in Celsius** | ✅ **VALIDATED**: 21.4°C = 70.5°F (user tested) |
| `outside_temperature` | °F | -40-120 | External temperature (if available) | May be 0 if no external sensor |

### Missing: Actual Hot Water Tank Temperatures
The NaviLink API does **not expose actual hot water tank sensors**. Hot water temperature must be inferred from:
- `dhw_temperature`: Hot water output temperature (when flowing)
- `dhw_charge_percent`: Thermal energy level (0-100%)

### Heat Sources Status

| Field | Unit | Range | Description | Notes |
|-------|------|-------|-------------|-------|
| `comp_use` | status | 0-2 | Compressor (heat pump) status | 0=Off, 1=On, 2=Active |
| `heat_upper_use` | status | 0-2 | Upper resistance heater status | 0=Off, 1=On, 2=Active |
| `heat_lower_use` | status | 0-2 | Lower resistance heater status | 0=Off, 1=On, 2=Active |
| `current_heat_use` | mode | 0-3 | Current heating method | See Heating Method Codes |
| `eva_fan_use` | status | 0-2 | Evaporator fan status | 0=Off, 1=On, 2=Active |

### Power and Energy

| Field | Unit | Range | Description | Notes |
|-------|------|-------|-------------|-------|
| `current_inst_power` | Watts | 0-5000 | Instantaneous power consumption | Real-time electrical usage |
| `total_energy_capacity` | Wh | 0-50000 | Total tank energy capacity | Maximum energy storage |
| `available_energy_capacity` | Wh | 0-50000 | Available energy in tank | Current stored energy |

### System Status

| Field | Unit | Range | Description | Notes |
|-------|------|-------|-------------|-------|
| `dhw_use` | status | 0-2 | Hot water demand status | 0=No demand, 1=Demand, 2=Active |
| `error_code` | code | 0-999 | Primary error code | 0=No error |
| `sub_error_code` | code | 0-999 | Secondary error code | Additional error detail |
| `wifi_rssi` | dBm | 0-100 | WiFi signal strength | Higher = better signal |
| `tou_status` | code | 0-7 | Time of Use status | See TOU Status Codes |
| `device_connected` | status | 0-2 | Device connectivity status | 0=Offline, 1=Online, 2=Active |

## Code Definitions

### Operation Mode Codes
Based on observed data and typical heat pump water heater modes:

| Code | Mode | Description |
|------|------|-------------|
| 32 | Heat Pump | Primary heat pump operation |
| 33 | Electric | Electric resistance heating only |
| 34 | Hybrid | Heat pump + electric backup |
| 35 | Vacation | Energy saving mode |
| 36 | Emergency | Electric only (heat pump disabled) |

### Heating Method Codes
| Code | Method | Description |
|------|--------|-------------|
| 0 | None | No active heating |
| 1 | Heat Pump Only | Compressor providing heat |
| 2 | Electric Only | Resistance elements only |
| 3 | Hybrid | Both heat pump and electric |

### TOU (Time of Use) Status Codes
| Code | Status | Description |
|------|--------|-------------|
| 0 | Disabled | TOU not active |
| 1 | Peak | Peak rate period |
| 2 | Off-Peak | Off-peak rate period |
| 3 | Mid-Peak | Mid-peak rate period |

### Device Status Codes
| Code | Status | Description |
|------|--------|-------------|
| 0 | Offline | Device not connected |
| 1 | Online | Device connected but idle |
| 2 | Active | Device connected and operating |

## Data Interpretation Examples

### Power Analysis
From collected data showing 430-450W power consumption:
- This indicates heat pump operation (compressor + fan)
- Resistance heaters would show 4000-4500W consumption
- Heat pump efficiency is much higher than electric resistance

### Tank Charge Calculation
The `dhw_charge_percent` represents thermal energy stored:
- 93% = Tank is nearly at full thermal capacity
- This is independent of temperature - relates to available energy for hot water delivery
- Calculated from temperature stratification and total energy content

### Temperature Relationships
- Upper tank temperature typically 10-30°F higher than lower during heating
- Discharge temperature from heat pump is usually higher than tank temperatures
- Ambient temperature affects heat pump efficiency

## Monitoring Recommendations

### Critical Alerts
- `error_code` != 0: System fault requiring attention  
- `dhw_charge_percent` < 20: Low hot water availability
- `current_inst_power` > 4000W: Unexpected electric heating activation

### Efficiency Monitoring
- Track `current_inst_power` vs `dhw_charge_percent` changes
- Monitor heat pump operation time vs ambient temperature
- Compare energy input to hot water usage patterns

### Maintenance Indicators
- `wifi_rssi` declining: Network connectivity issues
- Frequent mode changes: Potential control issues
- High discharge temperatures: Possible refrigerant issues

## Data Collection Best Practices

### Polling Frequency
- **Real-time monitoring**: 30-60 second intervals during active periods
- **Efficiency analysis**: 5-15 minute intervals for long-term data
- **Troubleshooting**: 10-30 second intervals for detailed diagnostics

### Storage Considerations
- Include timestamp with timezone information
- Store raw values to preserve precision
- Consider data compression for long-term storage

### Analysis Tips
- Correlate power usage with ambient temperature
- Track performance seasonal variations  
- Monitor DHW charge patterns relative to usage schedules
- Compare actual vs predicted energy consumption

## Version History

- **v1.0** - Initial schema based on NWP500 data analysis
- **v1.1** - Added TOU status codes and power analysis examples