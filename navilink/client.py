"""
Main client for NaviLink API interactions.
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
import aiohttp

from .auth import NaviLinkAuth
from .device import NaviLinkDevice
from .exceptions import CommunicationError, APIError, AuthenticationError
from .models import UserInfo, DeviceInfo, TOUInfo

logger = logging.getLogger(__name__)

class NaviLinkClient:
    """Main client for interacting with NaviLink service."""
    
    BASE_URL = "https://nlus.naviensmartcontrol.com/api/v2.1"
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize NaviLink client.
        
        Args:
            session: Optional aiohttp session to use for requests
        """
        self._session = session
        self._owns_session = session is None
        self._auth = None  # Initialize later when session is available
        self._devices: List[NaviLinkDevice] = []
        
    async def _ensure_session(self):
        """Ensure we have a valid session."""
        if not self._session:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
            
        if not self._auth:
            self._auth = NaviLinkAuth(self._session)
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Close all device connections
        for device in self._devices:
            try:
                await device.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting device {device.mac_address}: {e}")
                
        if self._owns_session and self._session:
            await self._session.close()
            
    async def authenticate(self, email: str, password: str) -> UserInfo:
        """
        Authenticate with NaviLink service.
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            UserInfo object with authentication details
        """
        await self._ensure_session()
        return await self._auth.authenticate(email, password)
    
    async def close(self):
        """Close the client and cleanup resources."""
        # Close all device connections
        for device in self._devices:
            try:
                await device.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting device {device.mac_address}: {e}")
                
        if self._owns_session and self._session:
            await self._session.close()
    
    async def get_devices(self, refresh: bool = False) -> List[NaviLinkDevice]:
        """
        Get list of user's devices.
        
        Args:
            refresh: If True, refresh device list from server
            
        Returns:
            List of NaviLinkDevice objects
            
        Raises:
            AuthenticationError: If not authenticated
            APIError: If API request fails
        """
        await self._ensure_session()
        
        if not refresh and self._devices:
            return self._devices
            
        await self._auth.ensure_authenticated()
        
        try:
            # Prepare request body based on HAR analysis
            request_body = {
                "offset": 0,
                "count": 20,
                "userId": self._auth.user_info.email
            }
            
            async with self._session.post(  # Changed from GET to POST
                f"{self.BASE_URL}/device/list",
                headers=self._auth.get_auth_headers(),
                json=request_body
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise APIError(
                        f"Failed to get device list: {response.status}",
                        status_code=response.status,
                        response={"error": error_text}
                    )
                    
                data = await response.json()
                logger.debug(f"Got device list response: {data}")
                
                # Parse device list from response based on HAR analysis
                device_list = data.get("data", [])
                logger.debug(f"Found {len(device_list)} devices in response")
                
                self._devices = []
                for device_entry in device_list:
                    device_info = device_entry.get("deviceInfo", {})
                    location = device_entry.get("location", {})
                    
                    # Create device with parsed data
                    device_data = {
                        "macAddress": device_info.get("macAddress"),
                        "additionalValue": device_info.get("additionalValue"),
                        "deviceType": device_info.get("deviceType", 52),
                        "name": device_info.get("deviceName", "Unknown Device"),
                        "homeSeq": device_info.get("homeSeq"),
                        "connected": device_info.get("connected"),
                        "location": location
                    }
                    
                    device = NaviLinkDevice(
                        client=self,
                        device_data=device_data,
                        session=self._session
                    )
                    self._devices.append(device)
                    
                return self._devices
                
        except aiohttp.ClientError as e:
            raise CommunicationError(f"Network error getting device list: {e}")
        except Exception as e:
            if isinstance(e, (AuthenticationError, APIError, CommunicationError)):
                raise
            raise CommunicationError(f"Unexpected error getting device list: {e}")
    
    async def get_device_info(self, mac_address: str) -> Optional[DeviceInfo]:
        """
        Get detailed information for a specific device.
        
        Args:
            mac_address: Device MAC address
            
        Returns:
            DeviceInfo object or None if not found
        """
        await self._ensure_session()
        await self._auth.ensure_authenticated()
        
        try:
            # Prepare request body based on HAR analysis
            request_body = {
                "macAddress": mac_address,
                "additionalValue": "",  # Will be populated from device data if available
                "userId": self._auth.user_info.email
            }
            
            async with self._session.post(  # Changed from GET to POST
                f"{self.BASE_URL}/device/info",
                headers=self._auth.get_auth_headers(),
                json=request_body
            ) as response:
                if response.status == 404:
                    return None
                elif response.status != 200:
                    error_text = await response.text()
                    raise APIError(
                        f"Failed to get device info: {response.status}",
                        status_code=response.status,
                        response={"error": error_text}
                    )
                    
                data = await response.json()
                logger.debug(f"Got device info for {mac_address}")
                
                # Parse device info from response
                return self._parse_device_info(data)
                
        except aiohttp.ClientError as e:
            raise CommunicationError(f"Network error getting device info: {e}")
        except Exception as e:
            if isinstance(e, (AuthenticationError, APIError, CommunicationError)):
                raise
            raise CommunicationError(f"Unexpected error getting device info: {e}")
    
    async def get_device_firmware_info(self, mac_address: str) -> Dict[str, Any]:
        """
        Get firmware information for a specific device.
        
        Args:
            mac_address: Device MAC address
            
        Returns:
            Firmware information dictionary
        """
        await self._auth.ensure_authenticated()
        
        try:
            params = {"macAddress": mac_address}
            
            async with self._session.get(
                f"{self.BASE_URL}/device/firmware/info",
                headers=self._auth.get_auth_headers(),
                params=params
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise APIError(
                        f"Failed to get firmware info: {response.status}",
                        status_code=response.status,
                        response={"error": error_text}
                    )
                    
                data = await response.json()
                logger.debug(f"Got firmware info for {mac_address}")
                return data
                
        except aiohttp.ClientError as e:
            raise CommunicationError(f"Network error getting firmware info: {e}")
        except Exception as e:
            if isinstance(e, (AuthenticationError, APIError, CommunicationError)):
                raise
            raise CommunicationError(f"Unexpected error getting firmware info: {e}")
    
    async def get_tou_info(
        self, 
        additional_value: str, 
        controller_id: str, 
        mac_address: str
    ) -> TOUInfo:
        """
        Get Time of Use (TOU) information for a device.
        
        Args:
            additional_value: Device additional value
            controller_id: Controller ID 
            mac_address: Device MAC address
            
        Returns:
            TOUInfo object with TOU data
        """
        await self._auth.ensure_authenticated()
        user_info = self._auth.user_info
        
        try:
            params = {
                "additionalValue": additional_value,
                "controllerId": controller_id,
                "macAddress": mac_address,
                "userId": user_info.email,
                "userType": user_info.user_type
            }
            
            async with self._session.get(
                f"{self.BASE_URL}/device/tou",
                headers=self._auth.get_auth_headers(),
                params=params
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise APIError(
                        f"Failed to get TOU info: {response.status}",
                        status_code=response.status,
                        response={"error": error_text}
                    )
                    
                data = await response.json()
                logger.debug(f"Got TOU info for {mac_address}")
                
                return TOUInfo(
                    status=data.get("status"),
                    schedule=data.get("schedule"),
                    rates=data.get("rates")
                )
                
        except aiohttp.ClientError as e:
            raise CommunicationError(f"Network error getting TOU info: {e}")
        except Exception as e:
            if isinstance(e, (AuthenticationError, APIError, CommunicationError)):
                raise
            raise CommunicationError(f"Unexpected error getting TOU info: {e}")
    
    async def update_push_token(self, push_token: str) -> bool:
        """
        Update push notification token.
        
        Args:
            push_token: Push notification token
            
        Returns:
            True if successful
        """
        await self._auth.ensure_authenticated()
        
        try:
            async with self._session.post(
                f"{self.BASE_URL}/app/update-push-token",
                headers=self._auth.get_auth_headers(),
                json={"pushToken": push_token}
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise APIError(
                        f"Failed to update push token: {response.status}",
                        status_code=response.status,
                        response={"error": error_text}
                    )
                    
                logger.debug("Push token updated successfully")
                return True
                
        except aiohttp.ClientError as e:
            raise CommunicationError(f"Network error updating push token: {e}")
        except Exception as e:
            if isinstance(e, (AuthenticationError, APIError, CommunicationError)):
                raise
            raise CommunicationError(f"Unexpected error updating push token: {e}")
    
    def _parse_device_info(self, data: Dict[str, Any]) -> DeviceInfo:
        """
        Parse device information from API response.
        
        Args:
            data: Raw device info from API
            
        Returns:
            DeviceInfo object
        """
        # This will be implemented based on actual API response structure
        # For now, return a basic DeviceInfo with available data
        from .models import DeviceFeatures
        
        # Create empty features for now - will be populated based on actual response
        features = DeviceFeatures(
            country_code=0,
            model_type_code=0,
            control_type_code=0,
            volume_code=0,
            controller_sw_version=0,
            panel_sw_version=0,
            wifi_sw_version=0,
            controller_sw_code=0,
            panel_sw_code=0,
            wifi_sw_code=0,
            controller_serial_number="",
            power_use=0,
            holiday_use=0,
            program_reservation_use=0,
            dhw_use=0,
            dhw_temperature_setting_use=0,
            dhw_temperature_min=0,
            dhw_temperature_max=0,
            smart_diagnostic_use=0,
            wifi_rssi_use=0,
            temperature_type=0,
            temp_formula_type=0,
            energy_usage_use=0,
            freeze_protection_use=0,
            freeze_protection_temp_min=0,
            freeze_protection_temp_max=0,
            mixing_value_use=0,
            dr_setting_use=0,
            anti_legionella_setting_use=0,
            hpwh_use=0,
            dhw_refill_use=0,
            eco_use=0,
            electric_use=0,
            heatpump_use=0,
            energy_saver_use=0,
            high_demand_use=0
        )
        
        return DeviceInfo(
            device_type=data.get("deviceType", 0),
            mac_address=data.get("macAddress", ""),
            additional_value=data.get("additionalValue", ""),
            controller_serial_number=data.get("controllerSerialNumber", ""),
            features=features
        )
    
    @property
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._auth.is_authenticated()
        
    @property
    def user_info(self) -> Optional[UserInfo]:
        """Get current user information."""
        return self._auth.user_info