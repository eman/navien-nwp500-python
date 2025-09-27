#!/usr/bin/env python3
"""
Enhanced NaviLink Tank Monitor with MQTT5 and improved data collection.
Monitors DHW (Domestic Hot Water) charge levels and operation modes periodically.
"""

import asyncio
import argparse
import logging
import json
import csv
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

from navilink import NaviLinkClient
from navilink.models import DeviceStatus
from navilink.exceptions import NaviLinkError

# Try to import credentials
try:
    from credentials import EMAIL, PASSWORD, DEVICE_MAC, POLLING_INTERVAL as DEFAULT_POLLING_INTERVAL
    HAS_CREDENTIALS_FILE = True
except ImportError:
    EMAIL = PASSWORD = DEVICE_MAC = None
    DEFAULT_POLLING_INTERVAL = 300
    HAS_CREDENTIALS_FILE = False

# Set up logging
logging.basicConfig(
    level=logging.INFO,  # Back to INFO, debug in mqtt.py will still show
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('tank_monitoring_enhanced.log')
    ]
)
logger = logging.getLogger(__name__)

class TankMonitor:
    """Enhanced tank monitoring with improved data collection and reliability."""
    
    def __init__(self, email: str, password: str, output_file: str = "tank_data_enhanced.csv", 
                 polling_interval: int = 300, duration_minutes: Optional[int] = None):
        """
        Initialize tank monitor.
        
        Args:
            email: NaviLink account email
            password: NaviLink account password  
            output_file: CSV file to save data
            polling_interval: Seconds between status checks (default: 300 = 5 minutes)
            duration_minutes: Total monitoring duration in minutes (None = indefinite)
        """
        self.email = email
        self.password = password
        self.output_file = output_file
        self.polling_interval = polling_interval
        self.duration_minutes = duration_minutes
        
        self.client = None
        self.device = None
        self._session = None
        self.csv_writer = None
        self.csv_file = None
        self.start_time = None
        self.stop_requested = False
        
        # Statistics
        self.stats = {
            'updates_received': 0,
            'connection_issues': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals for graceful shutdown."""
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
        self.stop_requested = True
    
    async def setup(self):
        """Set up client, authenticate, and prepare for monitoring."""
        try:
            # Create session and client with proper session management
            import aiohttp
            self._session = aiohttp.ClientSession()
            self.client = NaviLinkClient(session=self._session)
            logger.info("✅ Client context created") 
            
            logger.info("🔐 Authenticating...")
            await self.client.authenticate(self.email, self.password)
            logger.info("✅ Authentication successful")
            
            # Get devices
            logger.info("📱 Getting device list...")
            devices = await self.client.get_devices()
            logger.info(f"✅ Found {len(devices)} devices")
            
            if not devices:
                raise NaviLinkError("No devices found")
            
            # Use first device (or specific MAC if configured)
            if DEVICE_MAC:
                for device in devices:
                    if device.mac_address.lower() == DEVICE_MAC.lower():
                        self.device = device
                        break
                if not self.device:
                    raise NaviLinkError(f"Device with MAC {DEVICE_MAC} not found")
            else:
                self.device = devices[0]
            
            logger.info(f"🏠 Using device: {self.device.name} (MAC: {self.device.mac_address})")
            
            # Set up CSV file
            self._setup_csv()
            
            self.stats['start_time'] = datetime.now()
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            return False
    
    def _setup_csv(self):
        """Set up CSV file for data logging with comprehensive field set."""
        # Define CSV columns for comprehensive monitoring
        fieldnames = [
            'timestamp',
            'dhw_charge_percent',  # Main field we're tracking
            'operation_mode',      # Heat pump vs resistance mode
            'dhw_temperature',
            'dhw_temperature_setting',
            'tank_upper_temperature',  # Tank sensor readings
            'tank_lower_temperature',
            'discharge_temperature',
            'ambient_temperature',
            'comp_use',           # Heat pump compressor status  
            'heat_upper_use',     # Upper heating element
            'heat_lower_use',     # Lower heating element
            'current_heat_use',   # Any heating active
            'eva_fan_use',        # Evaporator fan
            'current_inst_power', # Instantaneous power
            'outside_temperature',
            'dhw_use',           # Hot water being used
            'error_code',
            'sub_error_code',
            'wifi_rssi',
            'tou_status',        # Time of Use status
            'total_energy_capacity',
            'available_energy_capacity',
            'device_connected'
        ]
        
        # Open CSV file and write header
        self.csv_file = open(self.output_file, 'w', newline='')
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()
        self.csv_file.flush()
        
        logger.info(f"📊 CSV logging initialized: {self.output_file}")
    
    def _log_status_to_csv(self, status: DeviceStatus):
        """Log device status to CSV file with comprehensive data."""
        try:
            # Debug the status object
            logger.debug(f"🔍 Status object type: {type(status)}")
            logger.debug(f"🔍 Status dhw_charge_per: {getattr(status, 'dhw_charge_per', 'MISSING')}")
            logger.debug(f"🔍 Status dhw_temperature: {getattr(status, 'dhw_temperature', 'MISSING')}")
            logger.debug(f"🔍 Status operation_mode: {getattr(status, 'operation_mode', 'MISSING')}")
            
            # Convert status to CSV row with all the important fields
            row = {
                'timestamp': datetime.now().isoformat(),
                'dhw_charge_percent': getattr(status, 'dhw_charge_per', None),
                'operation_mode': getattr(status, 'operation_mode', None),
                'dhw_temperature': getattr(status, 'dhw_temperature', None),
                'dhw_temperature_setting': getattr(status, 'dhw_temperature_setting', None),
                'tank_upper_temperature': getattr(status, 'tank_upper_temperature', None),
                'tank_lower_temperature': getattr(status, 'tank_lower_temperature', None),
                'discharge_temperature': getattr(status, 'discharge_temperature', None),
                'ambient_temperature': getattr(status, 'ambient_temperature', None),
                'comp_use': getattr(status, 'comp_use', None),  # Heat pump
                'heat_upper_use': getattr(status, 'heat_upper_use', None),  # Upper element
                'heat_lower_use': getattr(status, 'heat_lower_use', None),  # Lower element
                'current_heat_use': getattr(status, 'current_heat_use', None),  # Any heating
                'eva_fan_use': getattr(status, 'eva_fan_use', None),
                'current_inst_power': getattr(status, 'current_inst_power', None),
                'outside_temperature': getattr(status, 'outside_temperature', None),
                'dhw_use': getattr(status, 'dhw_use', None),
                'error_code': getattr(status, 'error_code', None),
                'sub_error_code': getattr(status, 'sub_error_code', None),
                'wifi_rssi': getattr(status, 'wifi_rssi', None),
                'tou_status': getattr(status, 'tou_status', None),
                'total_energy_capacity': getattr(status, 'total_energy_capacity', None),
                'available_energy_capacity': getattr(status, 'available_energy_capacity', None),
                'device_connected': self.device.connected if self.device else None
            }
            
            self.csv_writer.writerow(row)
            self.csv_file.flush()
            self.stats['updates_received'] += 1
            
            # Log key metrics with enhanced information
            dhw_charge = row['dhw_charge_percent']
            op_mode = row['operation_mode']
            temp = row['dhw_temperature']
            comp_use = row['comp_use']
            heat_upper = row['heat_upper_use']
            heat_lower = row['heat_lower_use']
            
            # Decode operation mode for better logging
            mode_desc = self._decode_operation_mode(op_mode)
            heating_status = self._decode_heating_status(comp_use, heat_upper, heat_lower)
            
            logger.info(f"📊 Charge: {dhw_charge}% | Mode: {mode_desc} | Temp: {temp}°F | Heating: {heating_status}")
            
        except Exception as e:
            logger.error(f"❌ Failed to log status to CSV: {e}")
            self.stats['connection_issues'] += 1
    
    def _decode_operation_mode(self, mode: int) -> str:
        """Decode operation mode number to human readable string."""
        mode_map = {
            0: "Off",
            1: "Heat Pump Only", 
            2: "Electric Only",
            3: "Hybrid",
            32: "Auto",  # From HAR file
            # Add more as we discover them
        }
        return mode_map.get(mode, f"Unknown({mode})")
    
    def _decode_heating_status(self, comp_use: int, heat_upper: int, heat_lower: int) -> str:
        """Decode heating element status to human readable string."""
        status = []
        if comp_use == 1:
            status.append("HP")  # Heat Pump
        if heat_upper == 1:
            status.append("UE")  # Upper Element
        if heat_lower == 1:
            status.append("LE")  # Lower Element
        
        if not status:
            return "Idle"
        return "+".join(status)
    
    async def monitor_loop(self):
        """Main monitoring loop."""
        if not self.device:
            raise NaviLinkError("No device available for monitoring")
        
        end_time = None
        if self.duration_minutes:
            end_time = datetime.now() + timedelta(minutes=self.duration_minutes)
            logger.info(f"⏰ Monitoring will stop at {end_time.strftime('%H:%M:%S')}")
        
        try:
            while not self.stop_requested:
                # Check if we've reached the duration limit
                if end_time and datetime.now() >= end_time:
                    logger.info("⏰ Monitoring duration reached")
                    break
                
                try:
                    # Get current status via REST API (more reliable than MQTT for periodic checks)
                    logger.debug("🔍 Requesting device status...")
                    status = await self.device.get_status(use_cache=False)  # Force fresh data, don't use cache
                    
                    logger.debug(f"🔍 Received status: {type(status)} with charge: {getattr(status, 'dhw_charge_per', 'MISSING') if status else 'No status'}")
                    
                    if status:
                        self._log_status_to_csv(status)
                    else:
                        logger.warning("⚠️ No status data received")
                        self.stats['connection_issues'] += 1
                
                except Exception as e:
                    logger.error(f"❌ Failed to get device status: {e}")
                    self.stats['connection_issues'] += 1
                
                # Wait for next polling interval (unless stopping)
                if not self.stop_requested:
                    logger.debug(f"⏱️ Waiting {self.polling_interval} seconds until next check...")
                    await asyncio.sleep(self.polling_interval)
                    
        except Exception as e:
            logger.error(f"❌ Monitoring loop failed: {e}")
            raise
    
    async def run(self):
        """Run the complete monitoring session."""
        self.stats['start_time'] = datetime.now()
        
        try:
            # Setup phase
            if not await self.setup():
                raise NaviLinkError("Setup failed")
            
            logger.info("🚀 Starting monitoring loop...")
            logger.info(f"⏱️ Polling interval: {self.polling_interval} seconds ({self.polling_interval/60:.1f} minutes)")
            if self.duration_minutes:
                logger.info(f"⏰ Duration: {self.duration_minutes} minutes")
            else:
                logger.info("♾️ Duration: indefinite (until interrupted)")
            
            # Main monitoring
            await self.monitor_loop()
            
        except Exception as e:
            logger.error(f"❌ Monitoring session failed: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources."""
        self.stats['end_time'] = datetime.now()
        
        logger.info("🛑 Monitoring stopped")
        
        # Close CSV file
        if self.csv_file:
            self.csv_file.close()
        
        # Disconnect device
        if self.device:
            try:
                await self.device.disconnect()
            except:
                pass  # Best effort cleanup
        
        # Close client
        if self.client:
            try:
                await self.client.close()
            except:
                pass  # Best effort cleanup
                
        # Close session
        if hasattr(self, '_session') and self._session:
            try:
                await self._session.close()
            except:
                pass  # Best effort cleanup
        
        # Print summary
        runtime = self.stats['end_time'] - self.stats['start_time'] if self.stats['start_time'] else timedelta(0)
        logger.info("🏁 Final Session Summary:")
        logger.info(f"   Total Runtime: {runtime}")
        logger.info(f"   Status Updates Received: {self.stats['updates_received']}")
        logger.info(f"   Connection Issues: {self.stats['connection_issues']}")
        logger.info(f"   Data saved to: {self.output_file}")

def create_parser():
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Enhanced NaviLink Tank Monitor - DHW charge and operation tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --email user@example.com --password mypass
  %(prog)s --email user@example.com --password mypass --interval 120 --duration 60
  %(prog)s --email user@example.com --password mypass --output my_tank_data.csv
        """.strip()
    )
    
    if not HAS_CREDENTIALS_FILE:
        parser.add_argument("--email", required=True, help="NaviLink account email")
        parser.add_argument("--password", required=True, help="NaviLink account password")
    else:
        parser.add_argument("--email", default=EMAIL, help="NaviLink account email (from credentials.py)")
        parser.add_argument("--password", default=PASSWORD, help="NaviLink account password (from credentials.py)")
    
    parser.add_argument("--interval", type=int, default=DEFAULT_POLLING_INTERVAL,
                        help=f"Polling interval in seconds (default: {DEFAULT_POLLING_INTERVAL})")
    parser.add_argument("--duration", type=int, 
                        help="Monitoring duration in minutes (default: indefinite)")
    parser.add_argument("--output", default="tank_data_enhanced.csv",
                        help="Output CSV file (default: tank_data_enhanced.csv)")
    parser.add_argument("--verbose", action="store_true", 
                        help="Enable verbose logging")
    
    return parser

async def main():
    """Main function."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate credentials
    if not args.email or not args.password:
        logger.error("❌ Email and password are required")
        parser.print_help()
        sys.exit(1)
    
    # Create and run monitor
    monitor = TankMonitor(
        email=args.email,
        password=args.password,
        output_file=args.output,
        polling_interval=args.interval,
        duration_minutes=args.duration
    )
    
    logger.info("🚀 Starting Enhanced NaviLink Tank Monitor")
    logger.info(f"⏱️ Polling interval: {args.interval} seconds ({args.interval/60:.1f} minutes)")
    if args.duration:
        logger.info(f"⏰ Duration: {args.duration} minutes") 
    else:
        logger.info("♾️ Duration: indefinite (until interrupted)")
    
    try:
        await monitor.run()
        logger.info("✅ Monitoring completed successfully")
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("👋 Interrupted by user")
        sys.exit(0)  
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())