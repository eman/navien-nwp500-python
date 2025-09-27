# NaviLink Examples

This directory contains example scripts demonstrating how to use the NaviLink Python library.

## DHW Charge Level Monitoring

### 📊 Current Status: Device Connection Issues

**Important Note:** The Navien NWP500 device is currently not responding to MQTT commands. This is common and can be resolved with the troubleshooting steps below.

### 🔧 **Troubleshooting Your Device:**

**Try these steps to get your NWP500 responding:**

1. **🚿 Activate the Device:**
   - Turn on hot water at your location
   - Run a hot water tap for 2-3 minutes
   - This may wake the device from sleep mode

2. **📱 Check NaviLink Mobile App:**
   - Open the official NaviLink app
   - Verify your device shows as "Online"
   - Try controlling it from the app first

3. **🔌 Check Physical Device:**
   - Look at the WiFi/status LED on your NWP500
   - Ensure it shows connected (not blinking)
   - Check device display for error codes

4. **🔄 Network Reset:**
   - Power cycle your NWP500 (turn off/on)
   - Check your WiFi router connectivity
   - Consider re-pairing device if needed

### 📊 `dhw_charge_logger_robust.py` - Robust Data Logger

**This version handles offline devices and logs connection attempts:**

**Features:**
- Aggressive retry logic for offline devices
- Logs connection attempts even when device doesn't respond
- Tracks device connectivity status over time
- Provides detailed diagnostics about device state

**Usage:**
```bash
# Check device every 2 minutes (120 seconds)
python dhw_charge_logger_robust.py your@email.com your_password 120

# More frequent checking (every minute)
python dhw_charge_logger_robust.py your@email.com your_password 60
```

**Output Files:**
- `dhw_charge_data_robust.csv` - Connection attempts and status
- `dhw_logger_robust.log` - Detailed diagnostic logs

### 📈 `dhw_data_plotter.py` - Data Visualization

Creates comprehensive plots and analysis from logged data (when available).

### 🧪 **Diagnostic Tools:**

**Test Device Responsiveness:**
```bash
python test_device_wake_up.py your@email.com your_password
```

**Analyze Device Data Structure:**
```bash
python test_device_info_detailed.py your@email.com your_password
```

## Expected Behavior

### When Device is Online and Responding:
```
🔋 DHW Charge: 78% | Temp: 125°F | Mode: HEAT_PUMP | Power: 850W
🔋 DHW Charge: 82% | Temp: 128°F | Mode: HEAT_PUMP | Power: 920W  
🔋 DHW Charge: 85% | Temp: 130°F | Mode: STANDBY | Power: 45W
```

### When Device is Offline (Current Status):
```
❌ Attempt #1: Success=False | Connected=2 | MQTT=True | Status request timeout (30s)
❌ Attempt #2: Success=False | Connected=2 | MQTT=True | Connection failed: Command timeout
```

## Key Metrics We'll Capture (When Device Responds)

### Core DHW Metrics
- **DHW Charge Percentage** - Tank charge level (0-100%)
- **DHW Temperature** - Current hot water temperature 
- **DHW Temperature Setting** - Target temperature
- **DHW Use** - Hot water demand status

### Operation Analysis  
- **Operation Mode** - Current heating mode
- **Heat Pump Use** - When heat pump is active
- **Electric Use** - When electric elements are active
- **Power Consumption** - Real-time wattage

## Common Device Issues and Solutions

### Device Not Responding (Current Issue)
- **Symptom:** Commands sent successfully but no responses
- **Cause:** Device offline, sleeping, or network issues
- **Solution:** Use hot water, check mobile app, verify WiFi

### Device Shows as Offline
- **Symptom:** `device.connected = 0` or `is_connected = False`
- **Cause:** Network connectivity problems
- **Solution:** Check WiFi, power cycle device

### MQTT Connection Fails
- **Symptom:** WebSocket 403 errors
- **Cause:** Authentication or credential issues  
- **Solution:** ✅ **RESOLVED** - Our library handles this correctly

### Partial Data Only
- **Symptom:** Some fields are 0 or missing
- **Cause:** Device in partial operation mode
- **Solution:** Wait for full heating cycle or use hot water

## Success Indicators

**✅ Your setup will be working when you see:**
1. Device responds to commands within 5-30 seconds
2. DHW charge percentage shows non-zero values (0-100%)
3. Temperature data reflects actual device readings
4. Operation modes change based on device activity

## Next Steps

1. **Try the troubleshooting steps above**
2. **Run the robust logger to track connection attempts**
3. **Once device responds, switch to the standard logger**
4. **Use the plotter to analyze your heat pump efficiency**

The infrastructure is ready - we just need your NWP500 to come online! 🔥