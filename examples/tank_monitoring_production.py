#!/usr/bin/env python3
"""
Production-Ready Tank Monitoring Example

This example demonstrates enterprise-grade tank monitoring using the NaviLink library.
Features:
- Configuration via environment variables or CLI arguments
- Structured logging with configurable levels  
- CSV data export with proper error handling
- Graceful shutdown and resource cleanup
- Connection monitoring and automatic recovery
- Production data analysis and alerting

Usage:
    # Using environment variables
    export NAVILINK_EMAIL="user@example.com"
    export NAVILINK_PASSWORD="password"
    python tank_monitoring_production.py

    # Using command line arguments
    python tank_monitoring_production.py --email user@example.com --password password
    
    # With custom polling interval and output file
    python tank_monitoring_production.py --interval 300 --output tank_data.csv
"""

import asyncio
import argparse
import csv
import logging
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

# Import navilink library components
from navilink import NaviLinkClient, NaviLinkConfig, ReconnectConfig
from navilink.exceptions import NaviLinkError, DeviceOfflineError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tank_monitoring.log')
    ]
)
logger = logging.getLogger(__name__)

class TankMonitor:
    """Production-grade tank monitoring system."""
    
    def __init__(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        polling_interval: int = 300,
        output_file: str = "tank_data.csv",
        duration: Optional[int] = None
    ):
        """
        Initialize tank monitor.
        
        Args:
            email: NaviLink account email
            password: NaviLink account password  
            polling_interval: Time between status polls in seconds (default: 300 = 5 minutes)
            output_file: CSV file to save data (default: tank_data.csv)
            duration: Maximum monitoring duration in seconds (None = indefinite)
        """
        # Create configuration
        self.config = NaviLinkConfig.from_environment()
        if email:
            self.config.email = email
        if password:
            self.config.password = password
            
        self.polling_interval = polling_interval
        self.output_file = Path(output_file)
        self.duration = duration
        
        # Statistics tracking
        self.stats = {
            'start_time': None,
            'updates_received': 0,
            'connection_errors': 0,
            'last_successful_update': None,
            'alert_conditions': []
        }
        
        # Shutdown handling
        self._shutdown_event = asyncio.Event()
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self):
        """Set up graceful shutdown signal handlers."""
        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
            self._shutdown_event.set()
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    def _init_csv_file(self):
        """Initialize CSV file with headers."""
        headers = [
            'timestamp',
            'dhw_charge_percent',
            'operation_mode', 
            'dhw_temperature',
            'dhw_temperature_setting',
            'current_inst_power',
            'tank_upper_temp',  # Actually cold water inlet (°F/10)
            'tank_lower_temp',  # Actually heat pump ambient (°F/10)
            'comp_use',
            'heat_upper_use',
            'heat_lower_use',
            'eva_fan_use',
            'error_code',
            'wifi_rssi',
            'device_connected'
        ]
        
        # Create CSV file with headers if it doesn't exist
        if not self.output_file.exists():
            with open(self.output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
            logger.info(f"📊 CSV file initialized: {self.output_file}")
        else:
            logger.info(f"📊 Using existing CSV file: {self.output_file}")
            
    def _log_status_update(self, status: Any):
        """
        Log status update to CSV and analyze for alerts.
        
        Args:
            status: Device status object
        """
        timestamp = datetime.now().isoformat()
        
        # Extract key metrics with proper units and interpretations
        row = [
            timestamp,
            status.dhw_charge_per,                    # 0-100% tank thermal energy
            status.operation_mode,                     # Heat pump mode (0=standby, 32=active)
            status.dhw_temperature,                    # °F - hot water output temperature
            status.dhw_temperature_setting,           # °F - target temperature
            status.current_inst_power,                # W - current power consumption
            status.tank_upper_temperature / 10.0,     # °F - cold water inlet (NOT tank temp!)
            status.tank_lower_temperature / 10.0,     # °F - heat pump ambient (NOT tank temp!)
            status.comp_use,                          # 0-2: Compressor status
            status.heat_upper_use,                    # 0-2: Upper element status  
            status.heat_lower_use,                    # 0-2: Lower element status
            status.eva_fan_use,                       # 0-2: Evaporator fan status
            status.error_code,                        # 0=No error
            status.wifi_rssi,                         # WiFi signal strength
            status.device_connected                    # 0=Offline, 1=Online, 2=Active
        ]
        
        # Write to CSV
        with open(self.output_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)
            
        # Update statistics
        self.stats['updates_received'] += 1
        self.stats['last_successful_update'] = datetime.now()
        
        # Check for alert conditions based on production insights
        alerts = []
        
        if status.error_code != 0:
            alerts.append(f"System error: code {status.error_code}")
            
        if status.dhw_charge_per < 20:
            alerts.append(f"Low hot water: {status.dhw_charge_per}% charge")
            
        if status.current_inst_power > 4000:
            alerts.append(f"High power consumption: {status.current_inst_power}W (electric backup active)")
            
        if status.device_connected == 0:
            alerts.append("Device offline")
            
        # Log alerts
        for alert in alerts:
            logger.warning(f"⚠️ ALERT: {alert}")
            self.stats['alert_conditions'].append({
                'timestamp': timestamp,
                'alert': alert
            })
        
        # Log status summary with production insights
        mode_description = {
            0: "Standby",
            32: "Heat Pump Active", 
            33: "Electric Backup",
            34: "Hybrid Mode"
        }.get(status.operation_mode, f"Unknown({status.operation_mode})")
        
        logger.info(
            f"📊 Tank: {status.dhw_charge_per}% | "
            f"Temp: {status.dhw_temperature}°F | "
            f"Mode: {mode_description} | " 
            f"Power: {status.current_inst_power}W | "
            f"WiFi: {status.wifi_rssi}dBm"
        )
        
    async def monitor(self):
        """Main monitoring loop with enterprise error handling."""
        logger.info("🚀 Starting Production Tank Monitor")
        logger.info(f"⏱️ Polling interval: {self.polling_interval} seconds")
        logger.info(f"📁 Output file: {self.output_file}")
        
        self.stats['start_time'] = datetime.now()
        
        # Initialize CSV
        self._init_csv_file()
        
        async with NaviLinkClient(config=self.config) as client:
            try:
                # Authenticate
                logger.info("🔐 Authenticating...")
                await client.authenticate()
                logger.info("✅ Authentication successful")
                
                # Get devices
                logger.info("📱 Getting device list...")
                devices = await client.get_devices()
                
                if not devices:
                    logger.error("❌ No devices found")
                    return
                    
                device = devices[0]
                logger.info(f"🏠 Monitoring device: {device.name} (MAC: {device.mac_address})")
                
                # Check device connectivity
                try:
                    connectivity = await device.get_connectivity_status()
                    if not connectivity.get('device_connected'):
                        logger.warning("⚠️ Device shows offline - MQTT may not respond")
                except Exception as e:
                    logger.warning(f"⚠️ Could not check device connectivity: {e}")
                
                # Configure MQTT connection with production settings
                reconnect_config = ReconnectConfig(
                    max_retries=20,
                    initial_delay=2.0,
                    max_delay=120.0,
                    jitter=True
                )
                
                # Get MQTT connection
                mqtt_conn = await device.get_mqtt_connection(reconnect_config=reconnect_config)
                await mqtt_conn.connect()
                logger.info("🔗 MQTT connection established")
                
                # Set up status callback
                mqtt_conn.set_status_callback(self._log_status_update)
                
                # Start monitoring loop
                logger.info("🔄 Starting monitoring loop...")
                end_time = None
                if self.duration:
                    end_time = datetime.now() + timedelta(seconds=self.duration)
                    logger.info(f"⏰ Will run for {self.duration} seconds")
                else:
                    logger.info("♾️ Running indefinitely (Ctrl+C to stop)")
                
                while not self._shutdown_event.is_set():
                    try:
                        # Check if we've reached the duration limit
                        if end_time and datetime.now() >= end_time:
                            logger.info("⏰ Duration limit reached")
                            break
                            
                        # Request status update
                        await mqtt_conn.request_status()
                        
                        # Wait for next poll or shutdown signal
                        try:
                            await asyncio.wait_for(
                                self._shutdown_event.wait(), 
                                timeout=self.polling_interval
                            )
                        except asyncio.TimeoutError:
                            continue  # Normal timeout, continue polling
                            
                    except DeviceOfflineError:
                        logger.warning("📵 Device is offline - retrying...")
                        self.stats['connection_errors'] += 1
                        await asyncio.sleep(30)  # Wait before retry
                        
                    except Exception as e:
                        logger.error(f"❌ Error in monitoring loop: {e}")
                        self.stats['connection_errors'] += 1
                        await asyncio.sleep(10)  # Brief pause before retry
                        
            except NaviLinkError as e:
                logger.error(f"❌ NaviLink error: {e}")
                raise
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                raise
            finally:
                await self._log_final_summary()
                
    async def _log_final_summary(self):
        """Log final session summary."""
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
            
            logger.info("🏁 Final Session Summary:")
            logger.info(f"   Total Runtime: {runtime}")
            logger.info(f"   Status Updates: {self.stats['updates_received']}")
            logger.info(f"   Connection Errors: {self.stats['connection_errors']}")
            logger.info(f"   Alert Conditions: {len(self.stats['alert_conditions'])}")
            logger.info(f"   Data saved to: {self.output_file}")
            
            if self.stats['alert_conditions']:
                logger.warning("⚠️ Alert Summary:")
                for alert in self.stats['alert_conditions'][-5:]:  # Last 5 alerts
                    logger.warning(f"   {alert['timestamp']}: {alert['alert']}")

def main():
    """Main entry point with CLI argument support."""
    parser = argparse.ArgumentParser(
        description="Production tank monitoring with NaviLink",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--email', help='NaviLink account email')
    parser.add_argument('--password', help='NaviLink account password')
    parser.add_argument('--interval', type=int, default=300,
                       help='Polling interval in seconds (default: 300)')
    parser.add_argument('--output', default='tank_data.csv',
                       help='Output CSV file (default: tank_data.csv)')
    parser.add_argument('--duration', type=int,
                       help='Maximum runtime in seconds (default: unlimited)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Configure debug logging
    if args.debug:
        logging.getLogger('navilink').setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        
    # Create and run monitor
    monitor = TankMonitor(
        email=args.email,
        password=args.password,
        polling_interval=args.interval,
        output_file=args.output,
        duration=args.duration
    )
    
    try:
        asyncio.run(monitor.monitor())
    except KeyboardInterrupt:
        logger.info("🛑 Monitoring stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()