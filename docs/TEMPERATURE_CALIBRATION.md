# Temperature Calibration in NaviLink Python Library

## Overview

The NaviLink Python library includes automatic temperature calibration to ensure that temperature readings match the values displayed on the Navien app and water heater display.

## Background

User observation revealed that raw temperature values from the NaviLink API were consistently **20°F lower** than the temperatures shown on:
- The Navien mobile app
- The water heater's physical display panel
- The reported target temperatures

## Automatic Calibration

The library automatically applies a **+20°F offset** to all temperature readings and compensates for this offset when sending temperature commands.

### Temperature Fields Affected

The following temperature fields are automatically calibrated:

- `dhw_temperature` - Current hot water temperature (+20°F calibration)
- `dhw_temperature_setting` - User's target temperature setting (+20°F calibration)
- `dhw_target_temperature_setting` - Target temperature setting (+20°F calibration)
- `ambient_temperature` - Ambient air temperature (Celsius → Fahrenheit conversion)

### Special Case: Ambient Temperature

The `ambient_temperature` field is unique - it reports values in **Celsius** while other temperatures are in Fahrenheit. The library automatically converts this to Fahrenheit:

```python
# Raw value: 21.4 (Celsius)  
# Converted: 70.5°F
status = await device.get_status()
print(f"Room temperature: {status.ambient_temperature}°F")  # Shows 70.5°F
```

This was validated by user testing where the device reported 21.4°C and a room thermometer read 69.7°F (difference of only 0.8°F).

### How It Works

#### Reading Temperatures (Device → Display)
```python
# Raw API value: 121°F
# Calibrated display value: 141°F (121 + 20)

status = await device.get_status()
print(f"Temperature: {status.dhw_temperature}°F")  # Shows 141°F
```

#### Setting Temperatures (Display → Device)
```python
# User wants to set 141°F (as shown on app/display)
# Library automatically sends 121°F to device (141 - 20)

await device.set_temperature(141)  # User sees 141°F, device receives 121°F
```

## Temperature Ranges

| Range Type | Values | Description |
|------------|--------|-------------|
| **Raw Device Range** | 70-131°F | Internal device protocol values |
| **Calibrated Display Range** | 90-151°F | Values matching app/display |
| **Recommended Safe Range** | 100-140°F | Typical water heater operation |

## Manual Calibration Functions

For advanced use cases, calibration functions are available:

```python
from navien_nwp500 import (
    calibrate_temperature_from_raw,
    calibrate_temperature_to_raw,
    TEMPERATURE_CALIBRATION_OFFSET
)

# Convert raw device temperature to display temperature
raw_temp = 121
display_temp = calibrate_temperature_from_raw(raw_temp)
print(f"Raw: {raw_temp}°F → Display: {display_temp}°F")  # Raw: 121°F → Display: 141°F

# Convert display temperature to raw device value
display_temp = 141
raw_temp = calibrate_temperature_to_raw(display_temp)
print(f"Display: {display_temp}°F → Raw: {raw_temp}°F")  # Display: 141°F → Raw: 121°F

# Check the calibration offset
print(f"Offset: +{TEMPERATURE_CALIBRATION_OFFSET}°F")  # Offset: +20°F
```

## Real-World Example

Based on the HAR file analysis, the following temperature sequence was observed:

```python
# Raw API sequence from HAR data: 121°F → 117°F → 121°F
# With calibration, users see: 141°F → 137°F → 141°F

# This matches what users would see on their app/display
```

## Backwards Compatibility

The calibration is applied **automatically** and **transparently**:

- ✅ Existing code continues to work unchanged
- ✅ Temperature values now match app/display values
- ✅ No manual conversion needed in user applications
- ✅ Device protocol compatibility maintained

## Configuration

The calibration offset is defined as a constant:

```python
# In navien_nwp500/models.py
TEMPERATURE_CALIBRATION_OFFSET = 20  # °F
```

To modify the offset (if needed for other devices or calibration):

```python
import navien_nwp500.models as models
models.TEMPERATURE_CALIBRATION_OFFSET = 25  # Custom offset
```

## Validation Results

The temperature calibration has been validated with:

- ✅ **Unit Tests**: All conversion functions pass round-trip tests
- ✅ **HAR Analysis**: Matches observed temperature change patterns  
- ✅ **Range Validation**: Proper handling of min/max temperatures
- ✅ **Protocol Compatibility**: Raw device communication unchanged

## Examples

See the following example files:

- `examples/temperature_calibration_demo.py` - Complete calibration demonstration
- `test_temperature_calibration.py` - Validation tests and examples

## Notes for Developers

### Adding New Temperature Fields

When adding new temperature fields to `DeviceStatus`, apply calibration:

```python
# In mqtt.py parsing methods:
new_temperature_field=calibrate_temperature_from_raw(status_data.get("newTempField", 0)),
```

### Creating Custom Temperature Controls

For custom temperature controls, use the calibration functions:

```python
async def set_custom_temperature(self, display_temperature: int):
    raw_temperature = calibrate_temperature_to_raw(display_temperature)
    # Send raw_temperature to device protocol
```

## Future Considerations

- The offset can be made configurable per device if needed
- Different device models may require different offsets  
- Calibration could be extended to other sensor types if needed
- Temperature units (°C) could be supported with appropriate conversion