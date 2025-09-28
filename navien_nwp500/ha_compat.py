"""
Home Assistant Compatibility Interface for NaviLink Library.

This module provides a simplified interface that matches the Home Assistant
integration requirements while maintaining full compatibility with the
production-grade NaviLink library.

The interface bridges the gap between Home Assistant's expected API and the
advanced capabilities of the NaviLink library, ensuring all critical data
including dhw_charge_percent is properly exposed.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, Union

from .client import NaviLinkClient
from .config import NaviLinkConfig
from .device import NaviLinkDevice
from .exceptions import (
    AuthenticationError,
    CommunicationError,
    DeviceError,
    NaviLinkError,
)
from .models import DeviceStatus

logger = logging.getLogger(__name__)


class NavienClient:
    """
    Home Assistant compatible client for Navien water heaters.

    This class provides a simplified interface that matches the Home Assistant
    integration requirements while leveraging the full power of the production
    NaviLink library underneath.

    Example usage:
        client = NavienClient("user@example.com", "password")
        await client.authenticate()
        device_data = await client.get_device_data()
        await client.set_temperature(125.0)
        await client.set_operation_mode("heat_pump")
    """

    def __init__(self, username: str, password: str):
        """
        Initialize client with credentials.

        Args:
            username: NaviLink account email
            password: NaviLink account password
        """
        self.username = username
        self.password = password

        # Create configuration for the underlying NaviLink client
        self._config = NaviLinkConfig(
            email=username, password=password, log_level="INFO"
        )

        # Initialize the production NaviLink client
        self._client: Optional[NaviLinkClient] = None
        self._device: Optional[NaviLinkDevice] = None
        self._authenticated = False

    async def authenticate(self) -> bool:
        """
        Authenticate with Navilink service.

        Returns:
            True if authentication successful

        Raises:
            Exception with "authentication" in message for auth failures
        """
        try:
            self._client = NaviLinkClient(config=self._config)
            await self._client.authenticate(self.username, self.password)

            # Get the first device (typically only one water heater per account)
            devices = await self._client.get_devices()
            if not devices:
                raise DeviceError("No devices found in account")

            self._device = devices[0]
            self._authenticated = True

            logger.info(
                f"Successfully authenticated and found device: {self._device.name}"
            )
            return True

        except Exception as e:
            # Ensure authentication errors contain "authentication" keyword for HA
            raise Exception(f"Authentication failed: {e}")

    async def get_device_data(self) -> Dict[str, Any]:
        """
        Get current device status and sensor data.

        Returns:
            Dictionary with device data in Home Assistant compatible format

        Note: This method ensures dhw_charge_percent is included, which was
            missing from the original Home Assistant recommendations.
        """
        if not self._authenticated or not self._device:
            raise Exception("Must authenticate before getting device data")

        try:
            # Get current device status
            status = await self._device.get_status()
            if not status:
                raise Exception("Unable to retrieve device status")

            # Convert to Home Assistant compatible format
            # Following the field mappings from LIBRARY_RECOMMENDATIONS.md
            # but ensuring critical dhw_charge_percent is included
            device_data = {
                # Temperature Data (°F)
                "water_temperature": float(status.dhw_temperature),
                "set_temperature": float(status.dhw_target_temperature_setting),  # Use target setting, not current setting
                "target_temp": float(status.dhw_target_temperature_setting),
                "tank_temp": float(status.dhw_temperature),  # Primary hot water temp
                "inlet_temperature": float(status.tank_upper_temperature)
                / 10.0,  # Cold water inlet (0.1°F units)
                "outlet_temperature": float(status.dhw_temperature),  # Hot water output
                "ambient_temperature": float(status.ambient_temperature)
                / 10.0,  # System ambient (0.1°F units)
                # Power & Energy Data
                "power_consumption": float(status.current_inst_power),
                "current_power": float(status.current_inst_power),
                "power": float(status.current_inst_power),
                # Status Data - Using descriptive names for Home Assistant
                "operating_mode": self._get_operation_mode_name(status.operation_mode),
                "mode": self._get_operation_mode_name(status.operation_mode),
                "operation_mode": self._get_operation_mode_name(status.operation_mode),
                "error_code": (
                    str(status.error_code) if status.error_code != 0 else None
                ),
                "error": str(status.error_code) if status.error_code != 0 else None,
                "fault_code": (
                    str(status.error_code) if status.error_code != 0 else None
                ),
                # Component Status
                "compressor_status": self._get_component_status(status.comp_use),
                "compressor": self._get_component_status(status.comp_use),
                "heating_element_status": self._get_heater_status(
                    status.heat_upper_use, status.heat_lower_use
                ),
                "heater": self._get_heater_status(
                    status.heat_upper_use, status.heat_lower_use
                ),
                # CRITICAL: DHW Charge Percent - Missing from original recommendations
                "dhw_charge_percent": float(status.dhw_charge_per),
                "tank_charge_percent": float(status.dhw_charge_per),  # Alternative name
                "charge_level": float(status.dhw_charge_per),  # Another alternative
                # Additional useful fields for Home Assistant
                "wifi_signal_strength": status.wifi_rssi,
                "device_connected": bool(getattr(status, "device_connected", 1)),
                "dhw_demand_active": bool(status.dhw_use),
                # Raw status for advanced users
                "_raw_operation_mode": status.operation_mode,
                "_raw_error_code": status.error_code,
                "_raw_sub_error_code": status.sub_error_code,
            }

            # Optional Metadata (if available)
            try:
                device_info = await self._device.get_info()
                if device_info:
                    device_data.update(
                        {
                            "model": self._device.model or "Navien NWP500",
                            "serial_number": getattr(
                                device_info.features, "controller_serial_number", ""
                            ),
                            "firmware_version": f"{getattr(device_info.features, 'controller_sw_version', 0)}",
                        }
                    )
            except Exception as e:
                logger.warning(f"Could not retrieve device info: {e}")

            logger.debug(f"Device data retrieved: {len(device_data)} fields")
            return device_data

        except Exception as e:
            if "timeout" in str(e).lower():
                raise Exception(f"Connection timeout: {e}")
            else:
                raise Exception(f"Failed to get device data: {e}")

    async def set_temperature(self, temperature: float) -> bool:
        """
        Set target temperature.

        Args:
            temperature: Target temperature in Fahrenheit (typically 100-140°F)

        Returns:
            True if temperature set successfully
        """
        if not self._authenticated or not self._device:
            raise Exception("Must authenticate before setting temperature")

        try:
            # Validate temperature range (typical for water heaters)
            if not (80.0 <= temperature <= 140.0):
                raise ValueError(
                    f"Temperature {temperature}°F outside safe range (80-140°F)"
                )

            # Convert to integer (NaviLink expects integer temperatures)
            temp_int = int(round(temperature))

            # Use the device control method
            result = await self._device.set_temperature(temp_int)

            logger.info(f"Temperature set to {temperature}°F")
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to set temperature: {e}")
            raise Exception(f"Temperature setting failed: {e}")

    async def set_operation_mode(self, mode: str) -> bool:
        """
        Set operation mode.

        Args:
            mode: Operation mode string. Supported values:
                - "heat_pump" or "eco" -> Heat Pump Only (DHW mode 2)
                - "hybrid" -> Heat Pump + Electric (DHW mode 3)
                - "electric" -> Electric Only (DHW mode 4)
                - "energy_saver" -> Energy Saver (DHW mode 5)
                - "high_demand" -> High Demand (DHW mode 6)

        Returns:
            True if mode set successfully
        """
        if not self._authenticated or not self._device:
            raise Exception("Must authenticate before setting operation mode")

        # Map Home Assistant friendly names to NaviLink DHW modes
        mode_mapping = {
            "heat_pump": 2,
            "eco": 2,
            "hybrid": 3,
            "electric": 4,
            "energy_saver": 5,
            "high_demand": 6,
            # Alternative names
            "heat_pump_only": 2,
            "hp_only": 2,
            "electric_only": 4,
            "backup_heater": 4,
        }

        mode_lower = mode.lower()
        if mode_lower not in mode_mapping:
            valid_modes = ", ".join(sorted(mode_mapping.keys()))
            raise ValueError(f"Invalid mode '{mode}'. Valid modes: {valid_modes}")

        try:
            dhw_mode = mode_mapping[mode_lower]
            result = await self._device.set_dhw_mode(dhw_mode)

            logger.info(f"Operation mode set to {mode} (DHW mode {dhw_mode})")
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to set operation mode: {e}")
            raise Exception(f"Operation mode setting failed: {e}")

    def _get_operation_mode_name(self, mode_code: int) -> str:
        """Convert numeric operation mode to descriptive string."""
        mode_names = {
            0: "standby",
            32: "heat_pump_active",
            33: "electric_backup",
            34: "hybrid_mode",
        }
        return mode_names.get(mode_code, f"unknown_{mode_code}")

    def _get_component_status(self, status_code: int) -> str:
        """Convert component status code to string."""
        status_map = {
            0: "off",
            1: "ready",
            2: "active",
        }
        return status_map.get(status_code, f"unknown_{status_code}")

    def _get_heater_status(self, upper_status: int, lower_status: int) -> str:
        """Get heating element status from upper and lower element codes."""
        if upper_status == 2 or lower_status == 2:
            return "active"
        elif upper_status == 1 or lower_status == 1:
            return "ready"
        else:
            return "off"

    async def start_monitoring(
        self,
        callback: Optional[callable] = None,
        polling_interval: int = 300,
        use_mqtt: bool = True,
    ) -> bool:
        """
        Start real-time monitoring with periodic updates.

        Args:
            callback: Optional callback function to receive updates: callback(device_data: Dict[str, Any])
            polling_interval: Seconds between updates (default: 300 = 5 minutes)
            use_mqtt: Whether to use MQTT streaming (True) or REST polling (False)

        Returns:
            True if monitoring started successfully

        Example:
            async def on_update(data):
                print(f"Tank charge: {data['dhw_charge_percent']}%")
                print(f"Temperature: {data['water_temperature']}°F")

            await client.start_monitoring(callback=on_update, polling_interval=60)
        """
        if not self._authenticated or not self._device:
            raise Exception("Must authenticate before starting monitoring")

        try:
            if use_mqtt:
                # Get MQTT connection for real-time updates
                mqtt_conn = await self._device.get_mqtt_connection()
                await mqtt_conn.connect()

                # Set up status callback that converts to HA format
                async def mqtt_status_callback(status):
                    try:
                        # Convert raw status to HA compatible format
                        ha_data = self._convert_status_to_ha_format(status)

                        # Call user callback if provided
                        if callback:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(ha_data)
                            else:
                                callback(ha_data)

                        logger.debug("MQTT status update processed")
                    except Exception as e:
                        logger.error(f"Error in MQTT callback: {e}")

                mqtt_conn.set_status_callback(mqtt_status_callback)

                # Start MQTT monitoring
                await mqtt_conn.start_monitoring(polling_interval)
                logger.info(
                    f"Started MQTT monitoring with {polling_interval}s interval"
                )

            else:
                # Fallback to REST API polling
                self._polling_task = asyncio.create_task(
                    self._rest_polling_loop(callback, polling_interval)
                )
                logger.info(f"Started REST polling with {polling_interval}s interval")

            return True

        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            raise Exception(f"Monitoring startup failed: {e}")

    async def stop_monitoring(self) -> bool:
        """
        Stop real-time monitoring.

        Returns:
            True if monitoring stopped successfully
        """
        try:
            # Stop MQTT monitoring if active
            if self._device:
                await self._device.stop_monitoring()

            # Stop REST polling if active
            if hasattr(self, "_polling_task") and self._polling_task:
                self._polling_task.cancel()
                try:
                    await self._polling_task
                except asyncio.CancelledError:
                    pass
                self._polling_task = None

            logger.info("Monitoring stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to stop monitoring: {e}")
            return False

    def _convert_status_to_ha_format(self, status) -> Dict[str, Any]:
        """
        Convert raw DeviceStatus to Home Assistant compatible format.

        This is the same conversion logic as get_device_data() but
        optimized for real-time updates.
        """
        return {
            # Temperature Data (°F)
            "water_temperature": float(status.dhw_temperature),
            "set_temperature": float(status.dhw_target_temperature_setting),
            "target_temp": float(status.dhw_target_temperature_setting),
            "tank_temp": float(status.dhw_temperature),
            "inlet_temperature": float(status.tank_upper_temperature) / 10.0,
            "outlet_temperature": float(status.dhw_temperature),
            "ambient_temperature": float(status.ambient_temperature) / 10.0,
            # Power & Energy Data
            "power_consumption": float(status.current_inst_power),
            "current_power": float(status.current_inst_power),
            "power": float(status.current_inst_power),
            # Status Data
            "operating_mode": self._get_operation_mode_name(status.operation_mode),
            "mode": self._get_operation_mode_name(status.operation_mode),
            "operation_mode": self._get_operation_mode_name(status.operation_mode),
            "error_code": str(status.error_code) if status.error_code != 0 else None,
            "error": str(status.error_code) if status.error_code != 0 else None,
            "fault_code": str(status.error_code) if status.error_code != 0 else None,
            # Component Status
            "compressor_status": self._get_component_status(status.comp_use),
            "compressor": self._get_component_status(status.comp_use),
            "heating_element_status": self._get_heater_status(
                status.heat_upper_use, status.heat_lower_use
            ),
            "heater": self._get_heater_status(
                status.heat_upper_use, status.heat_lower_use
            ),
            # CRITICAL: DHW Charge Percent
            "dhw_charge_percent": float(status.dhw_charge_per),
            "tank_charge_percent": float(status.dhw_charge_per),
            "charge_level": float(status.dhw_charge_per),
            # Additional fields
            "wifi_signal_strength": status.wifi_rssi,
            "device_connected": bool(getattr(status, "device_connected", 1)),
            "dhw_demand_active": bool(status.dhw_use),
            # Timestamp for real-time updates
            "last_update": time.time(),
            "timestamp": datetime.now().isoformat(),
            # Raw status for debugging
            "_raw_operation_mode": status.operation_mode,
            "_raw_error_code": status.error_code,
        }

    async def _rest_polling_loop(self, callback: callable, interval: int):
        """
        REST API polling loop for when MQTT is not available.
        """
        try:
            while True:
                try:
                    # Get device data via REST API
                    ha_data = await self.get_device_data()

                    # Call user callback if provided
                    if callback:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(ha_data)
                        else:
                            callback(ha_data)

                    # Wait for next interval
                    await asyncio.sleep(interval)

                except asyncio.CancelledError:
                    logger.info("REST polling cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in REST polling: {e}")
                    await asyncio.sleep(interval)  # Continue polling on error

        except asyncio.CancelledError:
            logger.info("REST polling loop cancelled")

    async def close(self):
        """Close client and cleanup resources."""
        # Stop monitoring first
        await self.stop_monitoring()

        if self._client:
            await self._client.close()
        self._authenticated = False
        logger.info("NavienClient closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
