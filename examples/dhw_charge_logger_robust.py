#!/usr/bin/env python3
"""
Robust DHW Charge Level Logger with Device Connectivity Handling

This version handles devices that may be offline or intermittently responsive.
Includes aggressive retry logic and fallback strategies.
"""

import asyncio
import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from navilink import NaviLinkClient
from navilink.models import DeviceStatus

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dhw_logger_robust.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RobustDHWDataLogger:
    """Robust data logger that handles offline/unresponsive devices."""
    
    def __init__(self, csv_file: str = "dhw_charge_data_robust.csv"):
        self.csv_file = Path(csv_file)
        self.data_points = []
        self.running = False
        self.connection_attempts = 0
        self.successful_reads = 0
        self.failed_reads = 0
        
        # Create CSV with headers if it doesn't exist
        if not self.csv_file.exists():
            self._create_csv_headers()
    
    def _create_csv_headers(self):
        """Create CSV file with headers for device status logging."""
        headers = [
            # Timestamp and metadata
            'timestamp', 'iso_timestamp', 'connection_attempt', 'read_success',
            
            # Device connectivity info
            'device_connected', 'device_online_status', 'mqtt_connected',
            
            # Core metrics (when available)
            'dhw_charge_percentage', 'dhw_temperature', 'dhw_temperature_setting',
            'operation_mode', 'current_heat_use', 'heatpump_use', 'electric_use',
            'current_inst_power', 'outside_temperature', 'error_code',
            
            # Status flags
            'data_source', 'response_time_ms', 'notes'
        ]
        
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        
        logger.info(f"📊 Created robust CSV file: {self.csv_file}")
    
    def log_connection_attempt(self, device, success: bool, response_time: float = 0, notes: str = ""):
        """Log connection attempt regardless of data availability."""
        now = datetime.now(timezone.utc)
        self.connection_attempts += 1
        
        if success:
            self.successful_reads += 1
        else:
            self.failed_reads += 1
        
        # Create data point with available information
        data_point = {
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'iso_timestamp': now.isoformat(),
            'connection_attempt': self.connection_attempts,
            'read_success': success,
            
            # Device connectivity 
            'device_connected': getattr(device, 'connected', 'unknown'),
            'device_online_status': getattr(device, 'is_connected', False),
            'mqtt_connected': device._mqtt.is_connected if device._mqtt else False,
            
            # Initialize data fields
            'dhw_charge_percentage': 0,
            'dhw_temperature': 0,
            'dhw_temperature_setting': 0,
            'operation_mode': 0,
            'current_heat_use': 0,
            'heatpump_use': 0,
            'electric_use': 0,
            'current_inst_power': 0,
            'outside_temperature': 0,
            'error_code': 0,
            
            # Metadata
            'data_source': 'connection_attempt',
            'response_time_ms': int(response_time * 1000),
            'notes': notes
        }
        
        # Store and write
        self.data_points.append(data_point)
        
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data_point.keys())
            writer.writerow(data_point)
        
        # Log status
        status_emoji = "✅" if success else "❌"
        logger.info(f"{status_emoji} Attempt #{self.connection_attempts}: "
                   f"Success={success} | Connected={data_point['device_connected']} | "
                   f"MQTT={data_point['mqtt_connected']} | {notes}")
    
    def log_successful_data(self, device, status: DeviceStatus, response_time: float = 0):
        """Log successful data retrieval."""
        now = datetime.now(timezone.utc)
        self.connection_attempts += 1
        self.successful_reads += 1
        
        data_point = {
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'iso_timestamp': now.isoformat(),
            'connection_attempt': self.connection_attempts,
            'read_success': True,
            
            # Device connectivity
            'device_connected': getattr(device, 'connected', 'unknown'),
            'device_online_status': getattr(device, 'is_connected', False),
            'mqtt_connected': device._mqtt.is_connected if device._mqtt else False,
            
            # Actual status data
            'dhw_charge_percentage': status.dhw_charge_per,
            'dhw_temperature': status.dhw_temperature,
            'dhw_temperature_setting': status.dhw_temperature_setting,
            'operation_mode': status.operation_mode,
            'current_heat_use': status.current_heat_use,
            'heatpump_use': status.heatpump_use,
            'electric_use': status.electric_use,
            'current_inst_power': status.current_inst_power,
            'outside_temperature': status.outside_temperature,
            'error_code': status.error_code,
            
            # Metadata
            'data_source': 'mqtt_response',
            'response_time_ms': int(response_time * 1000),
            'notes': f"DHW: {status.dhw_charge_per}%, Temp: {status.dhw_temperature}°F"
        }
        
        self.data_points.append(data_point)
        
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data_point.keys())
            writer.writerow(data_point)
        
        # Celebrate successful data!
        logger.info(f"🎉 SUCCESS #{self.successful_reads}: "
                   f"DHW: {status.dhw_charge_per}% | Temp: {status.dhw_temperature}°F | "
                   f"Mode: {status.operation_mode} | Power: {status.current_inst_power}W")

async def robust_dhw_monitoring(email: str, password: str, check_interval: int = 120):
    """
    Robust DHW monitoring that handles connectivity issues.
    
    Args:
        email: NaviLink account email
        password: NaviLink account password
        check_interval: Seconds between connection attempts (default 120 = 2 minutes)
    """
    logger.info(f"🚀 Starting Robust DHW Monitor (check every {check_interval}s)")
    
    data_logger = RobustDHWDataLogger()
    client = None
    device = None
    
    try:
        while True:
            start_time = asyncio.get_event_loop().time()
            
            try:
                # Initialize client if needed
                if not client:
                    logger.info("🔐 Initializing client and authenticating...")
                    client = NaviLinkClient()
                    await client.authenticate(email, password)
                    logger.info("✅ Authentication successful!")
                    
                    devices = await client.get_devices()
                    device = devices[0]
                    logger.info(f"📱 Monitoring device: {device.name} (MAC: {device.mac_address})")
                
                # Try to connect to device
                logger.info("🔗 Attempting device connection...")
                
                if not device.is_connected:
                    await device.connect()
                
                connection_time = asyncio.get_event_loop().time() - start_time
                
                # Try to get status with timeout
                logger.info("📊 Requesting device status...")
                status_start = asyncio.get_event_loop().time()
                
                try:
                    # Try with shorter timeout
                    status = await asyncio.wait_for(device.get_status(), timeout=30.0)
                    status_time = asyncio.get_event_loop().time() - status_start
                    
                    # SUCCESS! Log the data
                    data_logger.log_successful_data(device, status, status_time)
                    
                except asyncio.TimeoutError:
                    data_logger.log_connection_attempt(
                        device, False, connection_time, 
                        "Status request timeout (30s)"
                    )
                except Exception as e:
                    data_logger.log_connection_attempt(
                        device, False, connection_time,
                        f"Status error: {str(e)[:50]}"
                    )
                
            except Exception as e:
                # Log connection failure
                if device:
                    data_logger.log_connection_attempt(
                        device, False, 0, 
                        f"Connection failed: {str(e)[:50]}"
                    )
                else:
                    logger.error(f"❌ Critical error: {e}")
                
                # Reset client on major failures
                if client:
                    try:
                        await client.close()
                    except:
                        pass
                    client = None
                    device = None
            
            # Report statistics
            success_rate = (data_logger.successful_reads / data_logger.connection_attempts * 100) if data_logger.connection_attempts > 0 else 0
            logger.info(f"📈 Stats: {data_logger.successful_reads}/{data_logger.connection_attempts} successful ({success_rate:.1f}%)")
            
            # Wait for next check
            logger.info(f"⏰ Waiting {check_interval}s until next check...")
            await asyncio.sleep(check_interval)
                
    except KeyboardInterrupt:
        logger.info("🛑 Stopping robust monitor...")
    except Exception as e:
        logger.error(f"❌ Monitor error: {e}")
        raise
    finally:
        if device and device.is_connected:
            await device.disconnect()
        if client:
            await client.close()
        
        logger.info(f"📊 Final Stats: {data_logger.successful_reads} successful reads out of {data_logger.connection_attempts} attempts")
        logger.info("✅ Robust monitor stopped")

def main():
    """Main entry point for robust monitoring."""
    if len(sys.argv) < 3:
        print("Usage: python dhw_charge_logger_robust.py <email> <password> [check_interval_seconds]")
        print("Example: python dhw_charge_logger_robust.py user@example.com password 120")
        print("  (checks every 120 seconds = 2 minutes)")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    interval = int(sys.argv[3]) if len(sys.argv) > 3 else 120  # Default 2 minutes
    
    if interval < 30:
        print("⚠️  Warning: Intervals < 30 seconds may be too aggressive")
    
    try:
        asyncio.run(robust_dhw_monitoring(email, password, interval))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n💥 Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()