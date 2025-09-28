# Temperature Analysis and Troubleshooting Guide

## Overview

This document provides analysis of temperature behavior in Navien NWP500 Heat Pump Water Heaters, specifically addressing common questions about apparent discrepancies between displayed setpoints and actual operation.

## Case Study: 121°F vs 141°F Setpoint Discrepancy

### Problem Description
User reported observing:
- Current temperature: 121°F 
- Expected setpoint: 141°F
- Tank charge: 100%
- Question: Why is tank "fully charged" at 121°F when setpoint should be 141°F?

### Data Analysis
From monitoring data (`tank_data_production.csv`):
```csv
timestamp,dhw_charge_per,dhw_temperature,dhw_temperature_setting,operation_mode,current_inst_power,...
2025-09-27T20:57:58.296360,100,121,121,0,1,...
```

**Key findings:**
- `dhw_temperature`: 121°F (actual hot water output)
- `dhw_temperature_setting`: 121°F (current active setpoint) 
- `dhw_charge_per`: 100% (tank fully charged)
- `operation_mode`: 0 (standby - no heating needed)

### Root Cause Analysis

#### Multiple Temperature Settings
Navien water heaters maintain **multiple temperature configurations**:

1. **Active Setpoint** (`dhw_temperature_setting`): 121°F
   - Currently controlling system operation
   - What the tank is maintaining

2. **Target/Comfort Setpoint** (`dhw_target_temperature_setting`): Potentially 141°F
   - User-configured comfort temperature
   - May be different from active setpoint

3. **Display Setpoint**: May show 141°F
   - What user sees on physical display or app
   - May represent comfort setting, not active setting

#### Energy Management Modes

**Most likely explanation: Energy-saving operation**

The system is operating in an energy management mode where:
- **Comfort setpoint**: 141°F (configured maximum)
- **Active setpoint**: 121°F (energy-saving mode)
- **Tank status**: 100% charged for the 121°F target

**Common energy management scenarios:**

1. **Time-of-Use (TOU) Schedule**:
   - Peak hours: 141°F (high demand periods)
   - Off-peak hours: 121°F (energy saving periods)
   - Reduces energy costs during peak rate times

2. **Eco/Energy Saver Mode**:
   - Manual or automatic activation
   - Reduces temperature to save energy
   - Maintains adequate hot water supply

3. **Vacation Mode**:
   - Extended energy saving
   - Lower temperature during low usage periods
   - Automatic or scheduled activation

4. **Demand Response**:
   - Utility signal participation
   - Temporary temperature reduction during grid peak demand
   - Part of smart grid programs

### Why 100% Charge at 121°F is Correct

#### Understanding DHW Charge Percentage
- **Definition**: Thermal energy available relative to **current active setpoint**
- **100% charge** = Sufficient energy to deliver hot water at current target (121°F)
- **Not temperature-based**: Represents available energy, not absolute temperature

#### System Logic
```
If active_setpoint = 121°F:
  Tank reaches thermal equilibrium at ~121°F
  Charge = 100% (sufficient energy for 121°F delivery)
  Operation_mode = 0 (standby, no heating needed)
```

This is **optimal operation** - the system maintains exactly the energy needed for the current setpoint.

## Temperature Field Reference

### Primary Temperature Fields

| Field | Example | Description | Notes |
|-------|---------|-------------|-------|
| `dhw_temperature` | 121°F | Current hot water output temperature | Actual delivery temperature |
| `dhw_temperature_setting` | 121°F | Active setpoint controlling operation | Currently enforced target |
| `dhw_target_temperature_setting` | 141°F | User comfort/maximum setpoint | May differ from active setting |
| `dhw_temperature2` | 121°F | Secondary temperature reading | Backup/verification sensor |

### System Status Indicators

| Field | Example | Meaning |
|-------|---------|---------|
| `dhw_charge_per` | 100% | Tank energy level for current setpoint |
| `operation_mode` | 0 | 0=Standby, 32=Heat pump active, 33=Electric |
| `eco_use` | 1 | Energy saving mode active |
| `tou_status` | 2 | Time-of-Use schedule status |

## Troubleshooting Guide

### Step 1: Verify Active vs Target Setpoints
Check if `dhw_temperature_setting` differs from `dhw_target_temperature_setting`:

```python
# In monitoring data or API response
active_setpoint = status.dhw_temperature_setting      # 121°F
target_setpoint = status.dhw_target_temperature_setting # 141°F

if active_setpoint != target_setpoint:
    print("System in energy management mode")
```

### Step 2: Check Energy Management Mode Status
Look for indicators of energy-saving operation:

```python
# Check for energy management indicators
if status.eco_use:
    print("Eco mode active")
    
if status.tou_status != 0:
    print(f"Time-of-Use schedule active (status: {status.tou_status})")
```

### Step 3: Verify Normal Operation
Confirm system is working correctly:

```python
# Normal operation indicators
if (status.dhw_charge_per == 100 and 
    status.operation_mode == 0 and
    status.error_code == 0):
    print("System operating normally at current setpoint")
```

### Step 4: Physical Display Check
**Check the water heater display/NaviLink app for:**
- Current operating mode (Normal, Eco, Vacation, etc.)
- Schedule settings (TOU, time-based temperature changes)
- Multiple setpoint configurations
- Energy-saving mode indicators

## Expected Behavior Patterns

### Normal Energy Management
```
Time Period          | Active Setpoint | Display Shows | Tank Charge
Peak Hours (6-9 PM) | 141°F          | 141°F         | 100%
Off-Peak (10 PM-5 AM)| 121°F          | 141°F         | 100%
```

### Eco Mode Operation
```
Mode        | Active Setpoint | Display Shows | Tank Charge | Power Usage
Normal      | 141°F          | 141°F        | 100%        | Higher
Eco Active  | 121°F          | 141°F (goal) | 100%        | Lower
```

## Resolution Strategies

### If Behavior is Unwanted
1. **Disable Eco Mode**: Check water heater controls for energy-saving modes
2. **Modify TOU Schedule**: Adjust time-based temperature schedules
3. **Update Setpoint**: Ensure comfort temperature is set as active setpoint
4. **Check Utility Programs**: Verify demand response participation

### If Behavior is Desired
This is optimal operation providing:
- **Energy savings**: Lower temperature when high heat not needed
- **Cost reduction**: Lower energy usage during peak rate periods  
- **Equipment longevity**: Reduced cycling and wear
- **Adequate hot water**: Still maintains comfortable supply

## Monitoring Recommendations

### Key Metrics to Track
1. **Setpoint Variance**: Monitor when `dhw_temperature_setting` != `dhw_target_temperature_setting`
2. **Mode Changes**: Track `operation_mode` and `eco_use` changes
3. **Schedule Patterns**: Correlate temperature changes with time of day
4. **Energy Usage**: Compare `current_inst_power` during different setpoints

### Alert Conditions
- **Unexpected setpoint changes**: Active setpoint drops without user action
- **Failed heating**: Tank charge < 80% with heating demand
- **Temperature deviation**: Output temperature significantly below active setpoint
- **Error codes**: Any non-zero error_code values

## Conclusion

The observed behavior (121°F operation with 141°F expectation) is typically **normal energy management operation**. The Navien system is intelligently managing energy usage while ensuring adequate hot water supply. 

**Key takeaway**: Always compare the **active setpoint** (`dhw_temperature_setting`) with actual operation, not the comfort/display setpoint. A tank at 100% charge for its active setpoint is performing optimally.

## Diagnostic Tools

### Quick Status Check
Monitor these fields to understand current operation:
```
dhw_temperature_setting    (active setpoint)
dhw_target_temperature_setting (comfort setpoint) 
dhw_charge_per            (energy level)
operation_mode            (heating status)
eco_use                   (energy saving mode)
```

### Data Collection
For detailed analysis, log these fields over time to identify patterns:
- Temperature setpoints throughout day
- Mode changes and triggers  
- Energy usage correlation with setpoints
- Schedule-based variations

This analysis framework can be applied to similar temperature behavior questions in Navien heat pump water heater systems.