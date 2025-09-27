#!/usr/bin/env python3
"""
Enhanced NaviLink Tank Monitor - Hybrid Approach

This script combines REST API connectivity checks with MQTT real-time monitoring
to reliably capture DHW tank charge levels and operation data.

Key improvements:
- Uses REST API to check device connectivity before MQTT requests
- Implements proper MQTT command 16777219 for status updates 
- Falls back gracefully when devices are offline
- Captures all relevant heat pump water heater metrics
"""

import asyncio
import logging
import csv
import json
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from navilink import NaviLinkClient
from navilink.exceptions import NaviLinkError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tank_monitoring_hybrid.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TankDataPoint:
    """Data structure for tank monitoring readings."""
    timestamp: str
    dhw_charge_percent: Optional[int] = None
    dhw_temperature: Optional[int] = None
    dhw_temperature_setting: Optional[int] = None
    operation_mode: Optional[int] = None
    compressor_use: Optional[int] = None  # Heat pump
    heat_upper_use: Optional[int] = None  # Upper electric element
    heat_lower_use: Optional[int] = None  # Lower electric element
    operation_busy: Optional[int] = None
    error_code: Optional[int] = None
    wifi_rssi: Optional[int] = None
    tank_upper_temp: Optional[int] = None
    tank_lower_temp: Optional[int] = None
    ambient_temperature: Optional[int] = None
    device_online: Optional[bool] = None
    data_source: str = "unknown"  # "mqtt" or "rest_fallback" or "offline"


class HybridTankMonitor:
    """Hybrid monitoring system using REST + MQTT."""
    
    def __init__(self, client: NaviLinkClient, csv_file: str = "tank_data_hybrid.csv"):
        self.client = client
        self.csv_file = csv_file
        self.device = None
        self.running = False
        self.stats = {
            'total_readings': 0,
            'mqtt_readings': 0,
            'rest_readings': 0,
            'offline_readings': 0,
            'connection_issues': 0
        }
        
    async def setup(self, email: str = None, password: str = None) -> bool:
        """Initialize monitoring setup."""
        try:
            logger.info("🔐 Authenticating...")
            if email and password:
                await self.client.authenticate(email, password)
            else:
                await self.client.authenticate()
            logger.info("✅ Authentication successful")
            
            logger.info("📱 Getting device list...")
            devices = await self.client.get_devices()
            
            if not devices:
                logger.error("❌ No devices found")
                return False
                
            self.device = devices[0]
            logger.info(f"🏠 Using device: {getattr(self.device, 'controller_serial_number', 'Unknown')} (MAC: {self.device.mac_address})")
            
            # Initialize CSV file
            self._init_csv()
            logger.info(f"📊 CSV logging initialized: {self.csv_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            return False
    
    def _init_csv(self):
        """Initialize CSV file with headers."""
        fieldnames = [field.name for field in TankDataPoint.__dataclass_fields__.values()]
        
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
    
    def _save_data_point(self, data_point: TankDataPoint):
        """Save a data point to CSV."""
        with open(self.csv_file, 'a', newline='') as f:
            fieldnames = [field.name for field in TankDataPoint.__dataclass_fields__.values()]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(asdict(data_point))
    
    async def _check_device_connectivity(self) -> bool:
        """Check if device is online using REST API."""
        try:
            device_info = await self.device.get_info()
            # If we can get device info, assume device is reachable
            return True
        except Exception as e:
            logger.debug(f"Connectivity check failed: {e}")
            return False
    
    async def _get_mqtt_status(self) -> Optional[Dict[str, Any]]:
        """Get device status via MQTT using command 16777219."""
        try:
            # Connect to MQTT if not already connected
            if not (hasattr(self.device, '_connected') and self.device._connected):
                await self.device.connect()
            
            # Send status request (command 16777219)
            logger.debug("📡 Requesting device status via MQTT...")
            
            # Wait for status response with timeout
            status = await asyncio.wait_for(
                self.device.get_status(use_cache=False), 
                timeout=15.0
            )
            
            if status:
                logger.debug("✅ MQTT status received")
                return status
            else:
                logger.debug("⚠️ MQTT status empty")
                return None
                
        except asyncio.TimeoutError:
            logger.debug("⏰ MQTT status request timed out")
            return None
        except Exception as e:
            logger.debug(f"❌ MQTT status failed: {e}")
            return None
    
    def _extract_tank_data(self, mqtt_data: Dict[str, Any], is_online: bool, source: str) -> TankDataPoint:
        """Extract relevant data from MQTT response or create offline record."""
        timestamp = datetime.now().isoformat()
        
        if not mqtt_data or not is_online:
            # Create offline/unavailable record
            return TankDataPoint(
                timestamp=timestamp,
                device_online=is_online,
                data_source=source
            )
        
        # Check if this is a DeviceStatus object or raw dict
        if hasattr(mqtt_data, '__dict__'):
            # It's a DeviceStatus object - extract attributes
            return TankDataPoint(
                timestamp=timestamp,
                dhw_charge_percent=getattr(mqtt_data, 'dhw_charge_per', None),
                dhw_temperature=getattr(mqtt_data, 'dhw_temperature', None),
                dhw_temperature_setting=getattr(mqtt_data, 'dhw_temperature_setting', None),
                operation_mode=getattr(mqtt_data, 'operation_mode', None),
                compressor_use=getattr(mqtt_data, 'comp_use', None),
                heat_upper_use=getattr(mqtt_data, 'heat_upper_use', None),
                heat_lower_use=getattr(mqtt_data, 'heat_lower_use', None),
                operation_busy=getattr(mqtt_data, 'operation_busy', None),
                error_code=getattr(mqtt_data, 'error_code', None),
                wifi_rssi=getattr(mqtt_data, 'wifi_rssi', None),
                tank_upper_temp=getattr(mqtt_data, 'tank_upper_temperature', None),
                tank_lower_temp=getattr(mqtt_data, 'tank_lower_temperature', None),
                ambient_temperature=getattr(mqtt_data, 'ambient_temperature', None),
                device_online=is_online,
                data_source=source
            )
        else:
            # Fallback: Extract status data from raw dict response structure: response.status.xxx
            response = mqtt_data.get('response', {}) if isinstance(mqtt_data, dict) else {}
            status_data = response.get('status', {})

            return TankDataPoint(
                timestamp=timestamp,
                dhw_charge_percent=status_data.get('dhwChargePer'),
                dhw_temperature=status_data.get('dhwTemperature'),
                dhw_temperature_setting=status_data.get('dhwTemperatureSetting'),
                operation_mode=status_data.get('operationMode'),
                compressor_use=status_data.get('compUse'),
                heat_upper_use=status_data.get('heatUpperUse'),
                heat_lower_use=status_data.get('heatLowerUse'),
                operation_busy=status_data.get('operationBusy'),
                error_code=status_data.get('errorCode'),
                wifi_rssi=status_data.get('wifiRssi'),
                tank_upper_temp=status_data.get('tankUpperTemperature'),
                tank_lower_temp=status_data.get('tankLowerTemperature'),
                ambient_temperature=status_data.get('ambientTemperature'),
                device_online=is_online,
                data_source=source
            )
    
    async def _take_reading(self) -> TankDataPoint:
        """Take a single reading using hybrid approach."""
        # Step 1: Check connectivity via REST API
        is_online = await self._check_device_connectivity()
        
        if not is_online:
            logger.info("🔌 Device appears offline, recording offline status")
            self.stats['offline_readings'] += 1
            return self._extract_tank_data(None, False, "offline")
        
        # Step 2: Try to get data via MQTT
        mqtt_data = await self._get_mqtt_status()
        
        if mqtt_data:
            logger.info("📊 Data retrieved via MQTT")
            self.stats['mqtt_readings'] += 1
            
            # The status is now a DeviceStatus object, not raw MQTT data
            if hasattr(mqtt_data, '__dict__'):
                # It's a DeviceStatus object
                logger.debug(f"🔍 DeviceStatus object attributes: {vars(mqtt_data)}")
                
                charge = getattr(mqtt_data, 'dhw_charge_per', 'N/A')
                temp = getattr(mqtt_data, 'dhw_temperature', 'N/A') 
                mode = getattr(mqtt_data, 'operation_mode', 'N/A')
                comp = getattr(mqtt_data, 'comp_use', 'N/A')
                heat_upper = getattr(mqtt_data, 'heat_upper_use', 'N/A')
                heat_lower = getattr(mqtt_data, 'heat_lower_use', 'N/A')
                
                logger.info(f"   Tank Charge: {charge}% | Temp: {temp}°F | Mode: {mode}")
                logger.info(f"   Heat Pump: {comp} | Heat Upper: {heat_upper} | Heat Lower: {heat_lower}")
                
                return self._extract_tank_data(mqtt_data, True, "mqtt")
            else:
                # Fallback for raw dict data  
                logger.debug(f"🔍 Raw MQTT data (fallback): {mqtt_data}")
                
                # Extract key metrics for logging - using correct response structure
                response = mqtt_data.get('response', {}) if isinstance(mqtt_data, dict) else {}
                status_data = response.get('status', {})
                
                logger.debug(f"🔍 Status data keys: {list(status_data.keys()) if status_data else 'No status data'}")
                
                charge = status_data.get('dhwChargePer', 'N/A')
                temp = status_data.get('dhwTemperature', 'N/A')
                mode = status_data.get('operationMode', 'N/A')
                comp = status_data.get('compUse', 'N/A')
                heat_upper = status_data.get('heatUpperUse', 'N/A')
                heat_lower = status_data.get('heatLowerUse', 'N/A')
                
                logger.info(f"   Tank Charge: {charge}% | Temp: {temp}°F | Mode: {mode}")
                logger.info(f"   Heat Pump: {comp} | Heat Upper: {heat_upper} | Heat Lower: {heat_lower}")
                
                return self._extract_tank_data(mqtt_data, True, "mqtt")
        else:
            # Step 3: Fallback - device online but MQTT failed
            logger.warning("⚠️ Device online but MQTT failed, recording partial data")
            self.stats['connection_issues'] += 1
            return self._extract_tank_data(None, True, "rest_fallback")
    
    async def run_monitoring(self, interval_seconds: int = 300, duration_minutes: Optional[int] = None):
        """Run the monitoring loop."""
        self.running = True
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes) if duration_minutes else None
        
        logger.info("🚀 Starting monitoring loop...")
        logger.info(f"⏱️ Polling interval: {interval_seconds} seconds ({interval_seconds/60:.1f} minutes)")
        if duration_minutes:
            logger.info(f"⏳ Duration: {duration_minutes} minutes")
        else:
            logger.info("♾️ Duration: indefinite (until interrupted)")
        
        try:
            while self.running:
                # Check if duration limit reached
                if end_time and datetime.now() >= end_time:
                    logger.info("⏰ Monitoring duration completed")
                    break
                
                # Take reading
                try:
                    data_point = await self._take_reading()
                    self._save_data_point(data_point)
                    self.stats['total_readings'] += 1
                    
                    # Progress update
                    elapsed = datetime.now() - start_time
                    logger.info(f"📈 Reading #{self.stats['total_readings']} saved (elapsed: {elapsed})")
                    
                except Exception as e:
                    logger.error(f"❌ Reading failed: {e}")
                    self.stats['connection_issues'] += 1
                
                # Wait for next reading
                if self.running:  # Check again in case we were interrupted
                    logger.debug(f"😴 Sleeping {interval_seconds} seconds until next reading...")
                    await asyncio.sleep(interval_seconds)
                    
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring interrupted by user")
        except Exception as e:
            logger.error(f"💥 Monitoring error: {e}")
        finally:
            self.running = False
            
            # Cleanup
            if self.device and hasattr(self.device, '_connected') and self.device._connected:
                await self.device.disconnect()
                
            # Final stats
            elapsed = datetime.now() - start_time
            logger.info("🏁 Monitoring Session Summary:")
            logger.info(f"   Total Runtime: {elapsed}")
            logger.info(f"   Total Readings: {self.stats['total_readings']}")
            logger.info(f"   MQTT Readings: {self.stats['mqtt_readings']}")
            logger.info(f"   Offline Readings: {self.stats['offline_readings']}")
            logger.info(f"   Connection Issues: {self.stats['connection_issues']}")
            logger.info(f"   Data saved to: {self.csv_file}")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="NaviLink Tank Monitor - Hybrid Approach")
    parser.add_argument("--email", help="NaviLink account email")
    parser.add_argument("--password", help="NaviLink account password")
    parser.add_argument("--interval", type=int, default=300, help="Polling interval in seconds (default: 300)")
    parser.add_argument("--duration", type=int, help="Duration in minutes (default: run indefinitely)")
    parser.add_argument("--output", default="tank_data_hybrid.csv", help="Output CSV file")
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting NaviLink Hybrid Tank Monitor")
    logger.info(f"⏱️ Polling interval: {args.interval} seconds ({args.interval/60:.1f} minutes)")
    if args.duration:
        logger.info(f"⏳ Duration: {args.duration} minutes")
    else:
        logger.info("♾️ Duration: indefinite (until interrupted)")
    
    # Create client
    client = NaviLinkClient()
    
    # Create monitor
    monitor = HybridTankMonitor(client, args.output)
    
    # Setup and run
    if await monitor.setup(args.email, args.password):
        await monitor.run_monitoring(args.interval, args.duration)
    else:
        logger.error("💥 Failed to setup monitoring")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        logger.info("🛑 Program interrupted by user")
        exit(0)
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        exit(1)