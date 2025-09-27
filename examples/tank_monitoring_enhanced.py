#!/usr/bin/env python3
"""
Enhanced Tank Monitoring Example with MQTT5 and Resilience Features

This example demonstrates:
- MQTT5 connection with automatic reconnection
- Enhanced error handling and connection monitoring
- Tank charge level tracking with statistics
- Operation mode detection (heat pump vs resistive heating)
- CSV logging with detailed metrics
- Connection health monitoring
"""

import asyncio
import csv
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add the parent directory to the path so we can import navilink
sys.path.insert(0, str(Path(__file__).parent.parent))

from navilink import NaviLinkClient
from navilink.models import DeviceStatus
from navilink.mqtt import ReconnectConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tank_monitoring_enhanced.log')
    ]
)
logger = logging.getLogger(__name__)

# CSV configuration
CSV_FILENAME = "tank_data_enhanced.csv"
CSV_HEADERS = [
    'timestamp', 'dhw_charge_percent', 'dhw_temperature_f', 'dhw_temperature_setting_f',
    'operation_mode', 'operation_mode_description', 'dhw_use', 'error_code', 'sub_error_code',
    'wifi_rssi', 'connection_state', 'messages_received', 'messages_sent', 
    'reconnection_count', 'uptime_seconds'
]

# Operation mode descriptions
OPERATION_MODES = {
    0: "Standby",
    1: "Heat Pump Only", 
    2: "Resistive Element Only",
    3: "Heat Pump + Resistive Element",
    4: "Defrost Mode",
    5: "Error Mode",
    6: "Maintenance Mode"
}

class EnhancedTankMonitor:
    """Enhanced tank monitoring with MQTT5 and resilience features."""
    
    def __init__(self):
        self.client = None
        self.device = None
        self.csv_file = None
        self.csv_writer = None
        self.monitoring = False
        self.last_status = None
        self.status_count = 0
        
        # Statistics tracking
        self.session_start = datetime.now()
        self.total_messages = 0
        self.connection_issues = 0
        
    async def setup(self):
        """Initialize client and authenticate."""
        try:
            # Get credentials from environment or prompt
            email = os.getenv('NAVILINK_EMAIL')
            password = os.getenv('NAVILINK_PASSWORD')
            
            if not email or not password:
                logger.info("Please enter your NaviLink credentials:")
                email = input("Email: ")
                password = input("Password: ")
            
            # Authenticate (client should already be set by run_monitoring_session)
            logger.info("🔐 Authenticating...")
            await self.client.authenticate(email=email, password=password)
            logger.info("✅ Authentication successful")
            
            # Get devices
            logger.info("📱 Getting device list...")
            devices = await self.client.get_devices()
            
            if not devices:
                raise Exception("No devices found")
            
            # Use first device (or prompt for selection if multiple)
            self.device = devices[0]
            logger.info(f"🏠 Using device: {self.device.device_name} (MAC: {self.device.mac_address})")
            
            # Setup CSV logging
            self._setup_csv()
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            raise
    
    def _setup_csv(self):
        """Setup CSV file for data logging."""
        # Check if file exists to determine if we need to write headers
        file_exists = Path(CSV_FILENAME).exists()
        
        self.csv_file = open(CSV_FILENAME, 'a', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        
        # Write headers if new file
        if not file_exists:
            self.csv_writer.writerow(CSV_HEADERS)
            logger.info(f"📝 Created CSV file: {CSV_FILENAME}")
        else:
            logger.info(f"📝 Appending to existing CSV file: {CSV_FILENAME}")
        
        # Flush to ensure headers are written
        self.csv_file.flush()
    
    async def start_monitoring(self, polling_interval: int = 300):  # 5 minutes default
        """Start enhanced monitoring with MQTT5."""
        try:
            logger.info("🔌 Connecting to MQTT with enhanced configuration...")
            
            # Configure enhanced reconnection settings
            reconnect_config = ReconnectConfig(
                max_retries=20,  # More retries for long-term monitoring
                initial_delay=2.0,
                max_delay=120.0,  # Up to 2 minutes between retries
                backoff_multiplier=1.5,
                jitter=True
            )
            
            # Get MQTT connection with enhanced config
            mqtt_conn = await self.device.get_mqtt_connection(reconnect_config=reconnect_config)
            
            # Connect with auto-reconnect enabled
            await mqtt_conn.connect(enable_auto_reconnect=True)
            
            # Set up status callback
            mqtt_conn.set_status_callback(self.on_status_update)
            
            # Start monitoring with the specified interval
            await mqtt_conn.start_monitoring(polling_interval=polling_interval)
            
            self.monitoring = True
            logger.info(f"🔄 Enhanced monitoring started (polling every {polling_interval}s)")
            logger.info("📊 Monitoring tank charge level, operation mode, and connection health")
            
            # Print connection statistics
            await self._print_connection_info(mqtt_conn)
            
            return mqtt_conn
            
        except Exception as e:
            logger.error(f"❌ Failed to start monitoring: {e}")
            raise
    
    async def _print_connection_info(self, mqtt_conn):
        """Print connection and configuration information."""
        stats = mqtt_conn.statistics
        logger.info("📡 Connection Information:")
        logger.info(f"   State: {mqtt_conn.connection_state.value}")
        logger.info(f"   Reconnection Config: max_retries={mqtt_conn._reconnect_config.max_retries}")
        logger.info(f"   Session ID: {mqtt_conn._session_id}")
        logger.info(f"   Device Type: {self.device.device_type}")
        logger.info(f"   MAC Address: {self.device.mac_address}")
    
    async def on_status_update(self, status: DeviceStatus):
        """Handle status updates with enhanced logging and CSV writing."""
        try:
            self.total_messages += 1
            self.last_status = status
            
            # Extract key metrics
            dhw_charge = getattr(status, 'dhw_charge', 0)  # Tank charge percentage
            dhw_temp = getattr(status, 'dhw_temperature', 0)
            dhw_setting = getattr(status, 'dhw_temperature_setting', 0)
            operation_mode = getattr(status, 'operation_mode', 0)
            dhw_use = getattr(status, 'dhw_use', 0)
            error_code = getattr(status, 'error_code', 0)
            sub_error_code = getattr(status, 'sub_error_code', 0)
            wifi_rssi = getattr(status, 'wifi_rssi', 0)
            
            # Get operation mode description
            mode_desc = OPERATION_MODES.get(operation_mode, f"Unknown ({operation_mode})")
            
            # Get connection statistics
            mqtt_conn = await self.device.get_mqtt_connection()
            connection_stats = mqtt_conn.statistics
            
            timestamp = datetime.now()
            
            # Log the status
            logger.info(f"🔋 Tank Status Update #{self.total_messages}")
            logger.info(f"   Charge: {dhw_charge}%")
            logger.info(f"   Temperature: {dhw_temp}°F (Setting: {dhw_setting}°F)")
            logger.info(f"   Operation: {mode_desc}")
            logger.info(f"   Hot Water Use: {'Active' if dhw_use else 'Inactive'}")
            
            if error_code != 0:
                logger.warning(f"   Error: {error_code} (Sub: {sub_error_code})")
            
            logger.info(f"   WiFi RSSI: {wifi_rssi} dBm")
            logger.info(f"   Connection: {mqtt_conn.connection_state.value} (Reconnects: {connection_stats['reconnection_count']})")
            
            # Write to CSV
            self.csv_writer.writerow([
                timestamp.isoformat(),
                dhw_charge,
                dhw_temp,
                dhw_setting,
                operation_mode,
                mode_desc,
                dhw_use,
                error_code,
                sub_error_code,
                wifi_rssi,
                mqtt_conn.connection_state.value,
                connection_stats['messages_received'],
                connection_stats['messages_sent'],
                connection_stats['reconnection_count'],
                connection_stats.get('uptime_seconds', 0)
            ])
            
            # Flush CSV data to disk
            self.csv_file.flush()
            
            self.status_count += 1
            
            # Periodic summary (every 12 readings = 1 hour with 5min polling)
            if self.status_count % 12 == 0:
                await self._print_session_summary()
                
        except Exception as e:
            logger.error(f"❌ Error processing status update: {e}")
    
    async def _print_session_summary(self):
        """Print session summary statistics."""
        runtime = datetime.now() - self.session_start
        logger.info("📊 Session Summary:")
        logger.info(f"   Runtime: {runtime}")
        logger.info(f"   Total Status Updates: {self.status_count}")
        logger.info(f"   Total MQTT Messages: {self.total_messages}")
        
        if self.last_status:
            logger.info(f"   Current Tank Charge: {getattr(self.last_status, 'dhw_charge', 0)}%")
            logger.info(f"   Current Temperature: {getattr(self.last_status, 'dhw_temperature', 0)}°F")
            
        # Check CSV file size
        if Path(CSV_FILENAME).exists():
            size_mb = Path(CSV_FILENAME).stat().st_size / 1024 / 1024
            logger.info(f"   CSV File Size: {size_mb:.1f} MB")
    
    async def stop_monitoring(self):
        """Stop monitoring and cleanup."""
        self.monitoring = False
        
        if self.device:
            try:
                mqtt_conn = await self.device.get_mqtt_connection()
                await mqtt_conn.stop_monitoring()
                await mqtt_conn.disconnect()
            except Exception as e:
                logger.warning(f"⚠️ Error stopping MQTT: {e}")
        
        if self.csv_file:
            self.csv_file.close()
            
        logger.info("🛑 Monitoring stopped")
    
    async def run_monitoring_session(self, duration_hours: Optional[int] = None, polling_interval: int = 300):
        """Run a complete monitoring session."""
        # Use client as async context manager to ensure proper session handling
        async with NaviLinkClient() as client:
            self.client = client
            
            try:
                await self.setup()
                mqtt_conn = await self.start_monitoring(polling_interval=polling_interval)
                
                if duration_hours:
                    logger.info(f"⏰ Running for {duration_hours} hours...")
                    end_time = datetime.now() + timedelta(hours=duration_hours)
                    
                    while datetime.now() < end_time and self.monitoring:
                        await asyncio.sleep(60)  # Check every minute
                        
                        # Check connection health
                        if not mqtt_conn.is_connected:
                            self.connection_issues += 1
                            logger.warning(f"⚠️ Connection issue detected (#{self.connection_issues})")
                            
                else:
                    logger.info("⏰ Running indefinitely (press Ctrl+C to stop)...")
                    # Run until interrupted
                    while self.monitoring:
                        await asyncio.sleep(60)
                        
                        # Check connection health
                        if not mqtt_conn.is_connected:
                            self.connection_issues += 1
                            logger.warning(f"⚠️ Connection issue detected (#{self.connection_issues})")
                            
            except KeyboardInterrupt:
                logger.info("⏹️ Interrupted by user")
            except Exception as e:
                logger.error(f"❌ Monitoring session failed: {e}")
            finally:
                await self.stop_monitoring()
                await self._print_final_summary()
    
    async def _print_final_summary(self):
        """Print final session summary."""
        runtime = datetime.now() - self.session_start
        logger.info("🏁 Final Session Summary:")
        logger.info(f"   Total Runtime: {runtime}")
        logger.info(f"   Status Updates Received: {self.status_count}")
        logger.info(f"   Connection Issues: {self.connection_issues}")
        logger.info(f"   Data saved to: {CSV_FILENAME}")
        
        if Path(CSV_FILENAME).exists():
            size_mb = Path(CSV_FILENAME).stat().st_size / 1024 / 1024
            logger.info(f"   Final CSV Size: {size_mb:.2f} MB")

async def main():
    """Main function with command line options."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced NaviLink Tank Monitor with MQTT5")
    parser.add_argument('--hours', type=float, help='Run for specified hours (default: indefinite)')
    parser.add_argument('--minutes', type=float, help='Run for specified minutes (default: indefinite)')
    parser.add_argument('--interval', type=int, default=300, help='Polling interval in seconds (default: 300)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Convert minutes to hours if specified
    duration_hours = args.hours
    if args.minutes:
        duration_hours = args.minutes / 60
    
    if args.verbose:
        logging.getLogger('navilink').setLevel(logging.DEBUG)
    
    logger.info("🚀 Starting Enhanced NaviLink Tank Monitor")
    logger.info(f"⏱️ Polling interval: {args.interval} seconds ({args.interval/60:.1f} minutes)")
    
    if duration_hours:
        if args.minutes:
            logger.info(f"🕐 Duration: {args.minutes} minutes")
        else:
            logger.info(f"🕐 Duration: {args.hours} hours")
    else:
        logger.info("♾️ Duration: indefinite (until interrupted)")
    
    monitor = EnhancedTankMonitor()
    await monitor.run_monitoring_session(
        duration_hours=duration_hours,
        polling_interval=args.interval
    )

if __name__ == "__main__":
    # Handle Windows event loop issues
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())