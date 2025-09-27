"""
NaviLink device representation and control.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List
import aiohttp

from .mqtt import NaviLinkMQTT
from .models import DeviceInfo, DeviceStatus, Reservation, EnergyUsage
from .exceptions import DeviceError, CommunicationError
from .utils import normalize_mac_address, validate_mac_address

logger = logging.getLogger(__name__)

class NaviLinkDevice:
    """Represents a NaviLink device (e.g., water heater)."""
    
    def __init__(
        self, 
        client: 'NaviLinkClient',
        device_data: Dict[str, Any],
        session: Optional[aiohttp.ClientSession] = None
    ):
        """
        Initialize device.
        
        Args:
            client: Parent NaviLinkClient instance
            device_data: Device data from API response
            session: Optional aiohttp session
        """
        self._client = client
        self._session = session
        self._mqtt: Optional[NaviLinkMQTT] = None
        
        # Parse device data
        self.device_type = device_data.get("deviceType", 52)  # Default to water heater
        self.mac_address = normalize_mac_address(device_data.get("macAddress", ""))
        self.additional_value = device_data.get("additionalValue", "")
        self.controller_id = device_data.get("controllerId", "")  # May not be in list response
        self.name = device_data.get("name", f"Device {self.mac_address}")
        self.model = device_data.get("model", "")
        self.home_seq = device_data.get("homeSeq")
        self.connected = device_data.get("connected")
        self.location = device_data.get("location", {})
        
        # Validate MAC address
        if not validate_mac_address(self.mac_address):
            raise DeviceError(f"Invalid MAC address: {self.mac_address}")
        
        # Device state
        self._device_info: Optional[DeviceInfo] = None
        self._last_status: Optional[DeviceStatus] = None
        self._status_callbacks: List[Callable[[DeviceStatus], None]] = []
        self._connected = False
        
    async def connect(self) -> bool:
        """
        Connect to device for real-time communication.
        
        Returns:
            True if connection successful
            
        Raises:
            CommunicationError: If connection fails
        """
        if self._connected and self._mqtt:
            return True
            
        try:
            self._mqtt = NaviLinkMQTT(
                client=self._client,
                device=self,
                session=self._session
            )
            
            await self._mqtt.connect()
            
            # Set up status update callback
            self._mqtt.set_status_callback(self._on_status_update)
            
            self._connected = True
            logger.info(f"Connected to device {self.mac_address}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to device {self.mac_address}: {e}")
            self._connected = False
            raise CommunicationError(f"Failed to connect to device: {e}")
    
    async def disconnect(self):
        """Disconnect from device."""
        if self._mqtt:
            await self._mqtt.disconnect()
            self._mqtt = None
        self._connected = False
        logger.info(f"Disconnected from device {self.mac_address}")
    
    async def get_info(self) -> DeviceInfo:
        """
        Get detailed device information.
        
        Returns:
            DeviceInfo object with device details
        """
        if not self._device_info:
            self._device_info = await self._client.get_device_info(self.mac_address)
            
        if not self._device_info:
            raise DeviceError(f"Could not get device info for {self.mac_address}")
            
        return self._device_info
    
    async def get_status(self, use_cache: bool = True) -> DeviceStatus:
        """
        Get current device status.
        
        Args:
            use_cache: If True, return cached status if available and recent
            
        Returns:
            DeviceStatus object with current device state
            
        Raises:
            DeviceError: If status cannot be retrieved
        """
        if use_cache and self._last_status:
            return self._last_status
            
        if not self._connected:
            await self.connect()
            
        try:
            # Get current device status via MQTT
            status = await self._mqtt.get_device_status()
            self._last_status = status
            return status
            
        except Exception as e:
            logger.error(f"Failed to get status for device {self.mac_address}: {e}")
            raise DeviceError(f"Failed to get device status: {e}")
    
    async def set_temperature(self, temperature: int) -> bool:
        """
        Set target water temperature.
        
        Args:
            temperature: Target temperature in device's configured units
            
        Returns:
            True if command sent successfully
            
        Raises:
            DeviceError: If command fails
        """
        if not self._connected:
            await self.connect()
            
        try:
            # TODO: Implement temperature setting command
            # This will require analyzing the MQTT command structure
            logger.info(f"Setting temperature to {temperature} for device {self.mac_address}")
            
            # For now, just log the attempt
            return True
            
        except Exception as e:
            logger.error(f"Failed to set temperature for device {self.mac_address}: {e}")
            raise DeviceError(f"Failed to set temperature: {e}")
    
    async def get_reservations(self) -> List[Reservation]:
        """
        Get device reservations/schedules.
        
        Returns:
            List of Reservation objects
        """
        if not self._connected:
            await self.connect()
            
        try:
            reservations = await self._mqtt.get_reservations()
            return reservations
            
        except Exception as e:
            logger.error(f"Failed to get reservations for device {self.mac_address}: {e}")
            raise DeviceError(f"Failed to get reservations: {e}")
    
    async def get_energy_usage(
        self, 
        period: str = "daily",
        days: int = 7
    ) -> List[EnergyUsage]:
        """
        Get energy usage data.
        
        Args:
            period: Period type ("daily", "monthly")
            days: Number of days/months to retrieve
            
        Returns:
            List of EnergyUsage objects
        """
        if not self._connected:
            await self.connect()
            
        try:
            usage_data = await self._mqtt.get_energy_usage(period, days)
            return usage_data
            
        except Exception as e:
            logger.error(f"Failed to get energy usage for device {self.mac_address}: {e}")
            raise DeviceError(f"Failed to get energy usage: {e}")
    
    def add_status_callback(self, callback: Callable[[DeviceStatus], None]):
        """
        Add callback for status updates.
        
        Args:
            callback: Function to call when status updates are received
        """
        self._status_callbacks.append(callback)
    
    def remove_status_callback(self, callback: Callable[[DeviceStatus], None]):
        """
        Remove status callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)
    
    async def get_mqtt_connection(self, reconnect_config: Optional = None):
        """
        Get the MQTT connection for this device, creating it if needed.
        
        Args:
            reconnect_config: Optional ReconnectConfig for enhanced connection behavior
            
        Returns:
            NaviLinkMQTT instance
        """
        if not self._mqtt:
            # Import here to avoid circular imports
            from .mqtt import NaviLinkMQTT
            self._mqtt = NaviLinkMQTT(self._client, self, reconnect_config=reconnect_config)
        elif reconnect_config and hasattr(self._mqtt, '_reconnect_config'):
            # Update reconnect config if provided
            self._mqtt._reconnect_config = reconnect_config
            
        return self._mqtt
    
    async def start_monitoring(
        self, 
        callback: Optional[Callable[[DeviceStatus], None]] = None,
        polling_interval: int = 15
    ):
        """
        Start real-time monitoring of device status.
        
        Args:
            callback: Optional callback for status updates
            polling_interval: Seconds between status polls (default 15)
        """
        if not self._connected:
            await self.connect()
            
        if callback:
            self.add_status_callback(callback)
            
        # Start monitoring loop with polling interval
        await self._mqtt.start_monitoring(polling_interval)
        logger.info(f"Started monitoring device {self.mac_address} with {polling_interval}s interval")
    
    async def stop_monitoring(self):
        """Stop real-time monitoring."""
        if self._mqtt:
            await self._mqtt.stop_monitoring()
        logger.info(f"Stopped monitoring device {self.mac_address}")
    
    def _on_status_update(self, status: DeviceStatus):
        """
        Handle status updates from MQTT.
        
        Args:
            status: Updated device status
        """
        self._last_status = status
        
        # Call all registered callbacks
        for callback in self._status_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(status))
                else:
                    callback(status)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if device is connected for real-time communication."""
        return self._connected and self._mqtt and self._mqtt.is_connected
    
    @property
    def last_status(self) -> Optional[DeviceStatus]:
        """Get the last received device status."""
        return self._last_status
    
    def __str__(self) -> str:
        return f"NaviLinkDevice(mac={self.mac_address}, name={self.name})"
    
    def __repr__(self) -> str:
        return (f"NaviLinkDevice(mac_address='{self.mac_address}', "
                f"name='{self.name}', device_type={self.device_type})")