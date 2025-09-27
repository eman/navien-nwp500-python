# Ctrl+C Regression Investigation Notes

## Background
The user reported that Ctrl+C was working fine in earlier versions (yesterday), but our fixes seem to have introduced a regression where Ctrl+C doesn't work during certain phases of execution.

## Current Status
- ✅ **Duration-based shutdown**: Working perfectly 
- ✅ **Resource cleanup**: Proper disconnection and cleanup
- ⚠️ **Ctrl+C during MQTT setup**: Blocks and doesn't respond

## Last Working Version
- Commit: `b639291` - "fix shutdown" (yesterday)
- This suggests the asyncio signal handling changes may have introduced the regression

## Investigation Needed

### 1. Compare Signal Handling Approaches
```bash
# Check the difference in signal handling between versions
git diff b639291..HEAD -- examples/tank_monitoring_production.py
```

### 2. Identify Blocking Operations
The Ctrl+C seems to work in some phases but not others:
- ✅ Works: After MQTT connection established and during monitoring loop
- ❌ Blocks: During initial MQTT connection setup (~50 seconds)

### 3. Potential AWS IoT SDK Issue
The blocking appears to happen during:
```python
await self._mqtt.connect()  # This can take 50+ seconds
```

### 4. Previous Working Implementation
The previous version (b639291) likely had a different approach to:
- Signal handler registration
- Task cancellation during blocking operations
- AsyncIO integration

## Recommended Next Steps

1. **Revert Signal Handling**: Test reverting just the signal handling code to the previous version
2. **Timeout Wrapper**: Add timeout wrapper around MQTT connection with cancellation
3. **Background Connection**: Make MQTT connection non-blocking with progress updates

## Workaround for Production
Use duration-based monitoring instead of relying on Ctrl+C:
```bash
python examples/tank_monitoring_production.py --duration 60  # 1 hour
```

## Files to Investigate
- `examples/tank_monitoring_production.py` (signal handling changes)
- `navien_nwp500/mqtt.py` (connection blocking)
- `navien_nwp500/aws_iot_websocket.py` (AWS IoT connection)