# Field Insights and Discoveries

This document captures insights gained from analyzing real NaviLink data from a Navien NWP500 Heat Pump Water Heater.

## Key Findings

### DHW Charge Percentage
- **What it means**: Tank thermal energy level as a percentage of maximum capacity
- **Observed behavior**: Stays constant at 93% when tank is at optimal charge level  
- **Not temperature**: This is energy content, not temperature - relates to available hot water delivery capacity
- **Range**: 0-100%, where higher values indicate more stored thermal energy

### Power Consumption Patterns
- **Heat Pump Operation**: 430-450W (compressor + evaporator fan)
- **Resistance Heating**: Would show 4000W+ (not observed in this dataset)
- **Efficiency**: Heat pump operation is much more energy efficient than electric resistance

### Temperature Measurements ⚠️ CORRECTED ANALYSIS
**CRITICAL DISCOVERY**: Fields named "tank_temperature" are misleading - they do NOT measure hot water tank temperatures!

- **DHW Temperature**: 119-120°F - Actual hot water output temperature ✅
- **"Tank" Sensors**: ~60°F - These measure **cold water inlet/heat pump evaporator temperatures** ⚠️
- **Discharge Temperature**: ~75°F - Heat pump condenser/discharge temperature ⚠️ 
- **Ambient Temperature**: ~24°F (raw) - Needs offset correction, likely indoor ambient ❌

**Missing Data**: The API does not expose actual hot water tank internal temperatures. Tank thermal state must be inferred from `dhw_charge_percent` (93% = nearly full thermal capacity).

### Temperature Unit Conversions (CORRECTED)
- **Direct °F**: `dhw_temperature`, `dhw_temperature_setting`, `outside_temperature`
- **0.1°F Units**: `tank_upper_temperature`, `tank_lower_temperature`, `discharge_temperature` (divide by 10)
- **Needs Investigation**: `ambient_temperature` (may need offset correction)

### Operation Modes
- **Code 32**: Heat Pump mode (primary efficient operation)
- **Code 33**: Electric resistance mode (backup/high demand)
- **Code 34**: Hybrid mode (heat pump + electric backup)
- **Code 35**: Vacation/energy saving mode

## Real-World Data Analysis

From 35 data points over 23 minutes of operation:

```
Tank Charge: Constant at 93% (tank at capacity)
Power Usage: 428-451W average 442W (heat pump operation)  
Operation Mode: Consistent Code 32 (Heat Pump)
DHW Temperature: Steady 117°F output
Tank Stratification: Upper 58.9°F, Lower 57.1°F (1.7°F difference)
```

## Field Units Reference (CORRECTED)

| Field | Units | Conversion | Example | Actual Measurement |
|-------|-------|------------|---------|-------------------|
| dhw_charge_percent | % | Direct | 93 = 93% | Tank thermal energy level |
| current_inst_power | Watts | Direct | 442 = 442W | Electrical power consumption |
| dhw_temperature | °F | Direct | 119 = 119°F | Hot water output temperature |
| tank_upper_temperature | 0.1°F | ÷ 10 | 596 = 59.6°F | **Cold water inlet/evaporator temp** |
| tank_lower_temperature | 0.1°F | ÷ 10 | 600 = 60.0°F | **Heat pump ambient temp** |
| discharge_temperature | 0.1°F | ÷ 10 | 750 = 75.0°F | Heat pump discharge temp |
| ambient_temperature | 0.1°F + offset? | ÷ 10 + ? | 240 = 24.0°F | Needs offset correction |

## Monitoring Recommendations

### For Efficiency Analysis
- Monitor `current_inst_power` to distinguish heat pump vs electric operation
- Track `dhw_charge_percent` to understand energy storage patterns
- Compare power consumption vs ambient temperature for seasonal analysis

### For Maintenance
- Watch for `operation_mode` changes that might indicate system issues
- Monitor temperature stratification (upper vs lower tank sensors)
- Alert on unexpected high power consumption (resistance heating activation)

### For Usage Patterns
- Track `dhw_use` status to correlate with energy consumption
- Monitor charge level drops to understand hot water demand
- Analyze recovery patterns after usage events

## Data Quality Insights

The NaviLink system provides very granular data:
- Updates approximately every 40 seconds during active monitoring
- High precision on power measurements (1W resolution)
- Temperature precision to 0.1°F for most sensors
- Consistent timestamp precision for accurate temporal analysis

This data quality enables detailed efficiency analysis and precise operational monitoring.