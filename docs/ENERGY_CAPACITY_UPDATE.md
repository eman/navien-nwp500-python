# Energy Capacity Fields Added to Home Assistant Integration

## Summary

Added thermal energy capacity fields (`total_energy_capacity` and `available_energy_capacity`) to the Home Assistant compatibility layer, providing better insights into the water heater's thermal energy state.

## Changes Made

### 1. Updated Home Assistant Compatibility Layer (`navien_nwp500/ha_compat.py`)

Added two new fields to both Home Assistant data conversion methods:

```python
# Energy Capacity Data (useful for thermal energy monitoring)
"total_energy_capacity": float(status.total_energy_capacity),
"available_energy_capacity": float(status.available_energy_capacity),
```

### 2. Updated HA Demo Example (`examples/ha_compat_demo.py`)

Enhanced the demo to display and validate the new energy capacity fields:

```python
# Display energy capacity in demo output
logger.info(f"   ⚡ Total Energy Capacity: {device_data['total_energy_capacity']}")
logger.info(f"   ⚡ Available Energy Capacity: {device_data['available_energy_capacity']}")

# Calculate energy utilization percentage
utilization_percent = (used_capacity / total_capacity) * 100
logger.info(f"   📊 Energy Utilization: {utilization_percent:.1f}%")
```

## Available Fields for Home Assistant

Home Assistant integrations can now access:

| Field | Type | Description | Example Value |
|-------|------|-------------|---------------|
| `total_energy_capacity` | `float` | Total thermal energy capacity of the tank | `1861.0` |
| `available_energy_capacity` | `float` | Available thermal energy capacity | `632.0` |

## Usage in Home Assistant

### Basic Usage

```python
from navien_nwp500 import NavienClient

async with NavienClient(email, password) as client:
    await client.authenticate()
    data = await client.get_device_data()
    
    # Access energy capacity fields
    total_capacity = data["total_energy_capacity"]
    available_capacity = data["available_energy_capacity"]
    
    # Calculate derived metrics
    used_capacity = total_capacity - available_capacity
    utilization_percent = (used_capacity / total_capacity) * 100
```

### Home Assistant Sensor Configuration

These fields can be used to create Home Assistant sensors:

```yaml
# configuration.yaml
sensor:
  - platform: template
    sensors:
      navien_total_energy_capacity:
        friendly_name: "Water Heater Total Energy Capacity"
        value_template: "{{ state_attr('water_heater.navien', 'total_energy_capacity') }}"
        unit_of_measurement: "units"
        
      navien_available_energy_capacity:
        friendly_name: "Water Heater Available Energy Capacity"  
        value_template: "{{ state_attr('water_heater.navien', 'available_energy_capacity') }}"
        unit_of_measurement: "units"
        
      navien_energy_utilization:
        friendly_name: "Water Heater Energy Utilization"
        value_template: >
          {% set total = state_attr('water_heater.navien', 'total_energy_capacity') | float %}
          {% set available = state_attr('water_heater.navien', 'available_energy_capacity') | float %}
          {% if total > 0 %}
            {{ (((total - available) / total) * 100) | round(1) }}
          {% else %}
            0
          {% endif %}
        unit_of_measurement: "%"
```

### Automation Examples

```yaml
# Automation based on energy capacity
automation:
  - alias: "Water Heater Low Energy Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.navien_energy_utilization
        below: 20
    action:
      - service: notify.mobile_app
        data:
          message: "Water heater energy capacity is low ({{ trigger.to_state.state }}%)"
          
  - alias: "Water Heater High Energy Usage"
    trigger:
      - platform: numeric_state  
        entity_id: sensor.navien_energy_utilization
        above: 90
    action:
      - service: notify.mobile_app
        data:
          message: "Water heater energy capacity is high ({{ trigger.to_state.state }}%)"
```

## Energy Capacity vs DHW Charge Percentage

| Metric | Description | Use Case |
|--------|-------------|----------|
| `dhw_charge_percent` | Tank charge level (0-100%) | Basic tank monitoring |
| `total_energy_capacity` | Total thermal energy capacity | Advanced energy analysis |
| `available_energy_capacity` | Available thermal energy | Energy efficiency tracking |

The energy capacity fields provide more granular information about the tank's thermal state compared to the simple percentage charge level.

## Benefits for Home Assistant Users

### Enhanced Monitoring

- **Thermal Energy Tracking**: Monitor actual energy capacity vs simple percentage
- **Energy Efficiency**: Calculate utilization rates and efficiency metrics  
- **Advanced Automation**: Create smarter automations based on energy state
- **Trend Analysis**: Track energy patterns over time

### Better Understanding

- **Tank State**: More detailed view of thermal energy storage
- **Heating Patterns**: Understand how energy capacity changes during operation
- **Optimization**: Identify opportunities for energy savings

## Real-World Example Values

Based on typical Navien NWP500 operation:

```python
{
    "total_energy_capacity": 1861.0,     # Total capacity
    "available_energy_capacity": 632.0,  # Available capacity  
    "dhw_charge_percent": 76,            # 76% charged
    
    # Calculated metrics:
    # Used capacity: 1861 - 632 = 1229
    # Utilization: (1229 / 1861) * 100 = 66.0%
}
```

## Testing

The energy capacity fields are automatically included in:

- ✅ `get_device_data()` method output
- ✅ Real-time monitoring callbacks  
- ✅ HA compatibility demo (`examples/ha_compat_demo.py`)
- ✅ Field validation in demo script

## Backwards Compatibility

- ✅ **No breaking changes** - existing code continues to work
- ✅ **Additive enhancement** - new fields are additional, not replacements
- ✅ **Optional usage** - integrations can use these fields if needed

The energy capacity fields complement the existing `dhw_charge_percent` field and provide deeper insights into the water heater's thermal energy management.