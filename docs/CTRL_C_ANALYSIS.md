# Ctrl+C Regression Analysis

## Key Differences Found

### Working Version (b639291) - Yesterday
```python
def signal_handler(signum, frame):
    logger.info("🛑 Shutdown signal received...")
    shutdown_event.set()
    if monitor:
        monitor.running = False  # ← CRITICAL: Directly stops monitor loop

signal.signal(signal.SIGINT, signal_handler)  # ← Traditional signal handling
signal.signal(signal.SIGTERM, signal_handler)
```

### Current Version (Our Changes)
```python
def signal_handler():  # ← No signum/frame params
    logger.info("🛑 Shutdown signal received...")
    shutdown_event.set()
    # ← MISSING: monitor.running = False

if sys.platform != "win32":
    loop = asyncio.get_running_loop()  # ← Asyncio signal handling
    loop.add_signal_handler(signal.SIGINT, signal_handler)
    loop.add_signal_handler(signal.SIGTERM, signal_handler)
```

## Root Cause
1. **Missing Direct Loop Control**: We removed `monitor.running = False` which directly breaks the monitoring loop
2. **Asyncio Signal Limitation**: `loop.add_signal_handler()` only works AFTER the event loop is running, not during blocking operations
3. **Connection Phase Blocking**: During MQTT connection (~50s), the event loop may not be processing signals properly

## The Fix
We need to combine both approaches:
- Keep asyncio signal handling for clean integration
- Restore the direct `monitor.running = False` for immediate loop termination
- Ensure the monitor reference is available to the signal handler