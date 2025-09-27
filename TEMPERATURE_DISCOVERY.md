# Critical Temperature Sensor Discovery

## Summary
Analysis of production data from a Navien NWP500 Heat Pump Water Heater revealed that **temperature sensors labeled as "tank" temperatures are misleading** - they do NOT measure hot water tank internal temperatures.

## Key Findings

### What We Expected vs Reality

| Expected | Reality |
|----------|---------|
| `tank_upper_temperature`: Hot water tank upper sensor (~120°F) | **Cold water inlet/evaporator temperature** (~60°F) |
| `tank_lower_temperature`: Hot water tank lower sensor (~115°F) | **Heat pump ambient temperature** (~60°F) |

### Actual Temperature Sources

1. **Hot Water Output**: `dhw_temperature` = 119-120°F ✅
2. **Cold Water System**: "Tank" sensors = ~60°F (normal cold water inlet temp)
3. **Heat Pump Components**: `discharge_temperature` = ~75°F (heat pump working)
4. **Missing**: No API access to actual hot water tank internal sensors

### Impact on Monitoring

- **Tank thermal state** must be inferred from `dhw_charge_percent` (0-100%)
- **Hot water availability** indicated by charge percentage, not temperature sensors  
- **System efficiency** still trackable via power consumption patterns
- **Heat pump operation** confirmed by discharge temperature changes

## Corrected Documentation

All documentation updated with this critical discovery:
- ✅ `docs/DEVICE_DATA_SCHEMA.md` - Updated field definitions
- ✅ `docs/TEMPERATURE_UNITS_ANALYSIS.md` - Corrected analysis
- ✅ `docs/FIELD_INSIGHTS.md` - Updated with real sensor meanings
- ✅ `.github/copilot-instructions.md` - Corrected for future development

## For Developers

When monitoring tank thermal state:
- Use `dhw_charge_percent` for energy level (93% = near capacity)
- Use `dhw_temperature` for hot water output temperature
- Consider "tank" sensors as heat pump system diagnostics only
- Actual hot water tank temperatures are not exposed by the NaviLink API

This discovery prevents incorrect interpretation of temperature data and ensures accurate system monitoring.