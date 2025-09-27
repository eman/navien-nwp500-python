#!/usr/bin/env python3
"""
DHW Charge Level Data Logger for Navien NWP500 Heat Pump Water Heater

This script continuously monitors and logs:
- DHW charge percentage (tank level)
- Operation mode (heat pump vs resistive elements)
- Temperatures and energy usage
- System status and efficiency metrics

Logs data every 5 minutes for analysis and plotting.
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
        logging.FileHandler('dhw_logger.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DHWDataLogger:
    """Data logger for DHW charge levels and heat pump operation."""
    
    def __init__(self, csv_file: str = "dhw_charge_data.csv", json_file: str = "dhw_charge_data.json"):
        self.csv_file = Path(csv_file)
        self.json_file = Path(json_file)
        self.data_points = []
        self.running = False
        
        # Create CSV with headers if it doesn't exist
        if not self.csv_file.exists():
            self._create_csv_headers()
    
    def _create_csv_headers(self):
        """Create CSV file with appropriate headers."""
        headers = [
            # Timestamp
            'timestamp', 'iso_timestamp',
            
            # Core DHW Metrics
            'dhw_charge_percentage', 'dhw_temperature', 'dhw_temperature_setting',
            'dhw_target_temperature_setting', 'dhw_use', 'dhw_use_sustained',
            
            # Operation Mode & Status
            'operation_mode', 'operation_busy', 'current_heat_use',
            'heat_upper_use', 'heat_lower_use', 'hp_operation_mode',
            
            # Temperatures
            'outside_temperature', 'current_inlet_temperature', 'dhw_temperature2',
            'freeze_protection_temperature', 'freeze_protection_use',
            
            # Heat Pump Specific
            'heatpump_use', 'electric_use', 'energy_saver_use', 'high_demand_use',
            'hp_upper_on_temp_setting', 'hp_upper_off_temp_setting',
            'hp_lower_on_temp_setting', 'hp_lower_off_temp_setting',
            
            # System Status
            'error_code', 'sub_error_code', 'fault_status1', 'fault_status2',
            'wifi_rssi', 'current_inst_power', 'eco_use',
            
            # Advanced Metrics  
            'current_dhw_flow_rate', 'cumulated_dhw_flow_rate', 'mixing_rate',
            'target_fan_rpm', 'current_fan_rpm', 'fan_pwm',
            'current_super_heat', 'eev_step', 'tou_status',
            
            # Time-based Features
            'program_reservation_use', 'vacation_day_setting', 'vacation_day_elapsed',
            'anti_legionella_use', 'anti_legionella_period', 'dr_event_status'
        ]
        
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
        
        logger.info(f"📊 Created CSV file: {self.csv_file}")
    
    def log_data_point(self, status: DeviceStatus):
        """Log a single data point from device status."""
        now = datetime.now(timezone.utc)
        
        # Extract key metrics for analysis
        data_point = {
            # Timestamp
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S UTC'),
            'iso_timestamp': now.isoformat(),
            
            # Core DHW Metrics
            'dhw_charge_percentage': status.dhw_charge_per,
            'dhw_temperature': status.dhw_temperature,
            'dhw_temperature_setting': status.dhw_temperature_setting,
            'dhw_target_temperature_setting': status.dhw_target_temperature_setting,
            'dhw_use': status.dhw_use,
            'dhw_use_sustained': status.dhw_use_sustained,
            
            # Operation Mode & Status
            'operation_mode': status.operation_mode,
            'operation_busy': status.operation_busy,
            'current_heat_use': status.current_heat_use,
            'heat_upper_use': status.heat_upper_use,
            'heat_lower_use': status.heat_lower_use,
            'hp_operation_mode': self._determine_hp_mode(status),
            
            # Temperatures
            'outside_temperature': status.outside_temperature,
            'current_inlet_temperature': status.current_inlet_temperature,
            'dhw_temperature2': status.dhw_temperature2,
            'freeze_protection_temperature': status.freeze_protection_temperature,
            'freeze_protection_use': status.freeze_protection_use,
            
            # Heat Pump Specific
            'heatpump_use': status.heatpump_use,
            'electric_use': status.electric_use,
            'energy_saver_use': status.energy_saver_use,
            'high_demand_use': status.high_demand_use,
            'hp_upper_on_temp_setting': status.hp_upper_on_temp_setting,
            'hp_upper_off_temp_setting': status.hp_upper_off_temp_setting,
            'hp_lower_on_temp_setting': status.hp_lower_on_temp_setting,
            'hp_lower_off_temp_setting': status.hp_lower_off_temp_setting,
            
            # System Status
            'error_code': status.error_code,
            'sub_error_code': status.sub_error_code,
            'fault_status1': status.fault_status1,
            'fault_status2': status.fault_status2,
            'wifi_rssi': status.wifi_rssi,
            'current_inst_power': status.current_inst_power,
            'eco_use': status.eco_use,
            
            # Advanced Metrics
            'current_dhw_flow_rate': status.current_dhw_flow_rate,
            'cumulated_dhw_flow_rate': status.cumulated_dhw_flow_rate,
            'mixing_rate': status.mixing_rate,
            'target_fan_rpm': status.target_fan_rpm,
            'current_fan_rpm': status.current_fan_rpm,
            'fan_pwm': status.fan_pwm,
            'current_super_heat': status.current_super_heat,
            'eev_step': status.eev_step,
            'tou_status': status.tou_status,
            
            # Time-based Features
            'program_reservation_use': status.program_reservation_use,
            'vacation_day_setting': status.vacation_day_setting,
            'vacation_day_elapsed': status.vacation_day_elapsed,
            'anti_legionella_use': status.anti_legionella_use,
            'anti_legionella_period': status.anti_legionella_period,
            'dr_event_status': status.dr_event_status,
        }
        
        # Store in memory
        self.data_points.append(data_point)
        
        # Write to CSV
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data_point.keys())
            writer.writerow(data_point)
        
        # Update JSON file (for easy programmatic access)
        with open(self.json_file, 'w') as f:
            json.dump(self.data_points, f, indent=2)
        
        # Log key metrics
        logger.info(f"🔋 DHW Charge: {status.dhw_charge_per}% | "
                   f"Temp: {status.dhw_temperature}°F | "
                   f"Mode: {self._describe_operation_mode(status)} | "
                   f"Power: {status.current_inst_power}W")
    
    def _determine_hp_mode(self, status: DeviceStatus) -> str:
        """Determine heat pump operation mode based on status."""
        if status.heatpump_use and status.current_heat_use:
            if status.electric_use:
                return "hybrid"  # Both HP and electric
            else:
                return "heat_pump_only"
        elif status.electric_use and status.current_heat_use:
            return "electric_only"
        elif status.current_heat_use:
            return "heating_unknown"
        else:
            return "standby"
    
    def _describe_operation_mode(self, status: DeviceStatus) -> str:
        """Create human-readable operation mode description."""
        modes = []
        
        if status.operation_busy:
            modes.append("BUSY")
        
        if status.current_heat_use:
            if status.heatpump_use:
                modes.append("HEAT_PUMP")
            if status.electric_use:
                modes.append("ELECTRIC")
        
        if status.eco_use:
            modes.append("ECO")
        
        if status.energy_saver_use:
            modes.append("ENERGY_SAVER")
        
        if status.high_demand_use:
            modes.append("HIGH_DEMAND")
        
        if not modes:
            modes.append("STANDBY")
        
        return "+".join(modes)

async def run_dhw_logger(email: str, password: str, log_interval: int = 300):
    """
    Run the DHW data logger.
    
    Args:
        email: NaviLink account email
        password: NaviLink account password  
        log_interval: Seconds between data points (default 300 = 5 minutes)
    """
    logger.info(f"🚀 Starting DHW Charge Logger (interval: {log_interval}s)")
    
    data_logger = DHWDataLogger()
    
    try:
        async with NaviLinkClient() as client:
            # Authenticate
            logger.info("🔐 Authenticating...")
            await client.authenticate(email, password)
            logger.info("✅ Authentication successful!")
            
            # Get devices and find NWP500
            devices = await client.get_devices()
            if not devices:
                logger.error("❌ No devices found!")
                return
            
            device = devices[0]  # Use first device
            logger.info(f"📱 Monitoring device: {device.name} (MAC: {device.mac_address})")
            
            # Connect to device
            logger.info("🔗 Connecting to device...")
            await device.connect()
            logger.info("✅ MQTT connection established!")
            
            # Set up status callback for real-time updates
            def on_status_update(status: DeviceStatus):
                data_logger.log_data_point(status)
            
            device.add_status_callback(on_status_update)
            
            # Start monitoring with polling
            logger.info(f"🔄 Starting monitoring (polling every {log_interval}s)...")
            await device.start_monitoring(polling_interval=log_interval)
            
            # Log initial status
            try:
                initial_status = await device.get_status()
                data_logger.log_data_point(initial_status)
                logger.info("📊 Logged initial status")
            except Exception as e:
                logger.warning(f"⚠️  Could not get initial status: {e}")
            
            # Keep running indefinitely
            logger.info("📈 Data logging active. Press Ctrl+C to stop...")
            logger.info(f"📁 Data files: {data_logger.csv_file}, {data_logger.json_file}")
            
            while True:
                await asyncio.sleep(60)  # Check every minute
                
    except KeyboardInterrupt:
        logger.info("🛑 Stopping data logger...")
    except Exception as e:
        logger.error(f"❌ Logger error: {e}")
        raise
    finally:
        logger.info(f"📊 Logged {len(data_logger.data_points)} data points")
        logger.info("✅ Data logger stopped")

def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python dhw_charge_logger.py <email> <password> [interval_seconds]")
        print("Example: python dhw_charge_logger.py user@example.com password 300")
        print("  (logs every 300 seconds = 5 minutes)")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    interval = int(sys.argv[3]) if len(sys.argv) > 3 else 300  # Default 5 minutes
    
    if interval < 60:
        print("⚠️  Warning: Intervals < 60 seconds may be too frequent for the device")
    
    try:
        asyncio.run(run_dhw_logger(email, password, interval))
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n💥 Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()