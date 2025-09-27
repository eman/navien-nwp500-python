"""
MQTT/WebSocket communication for real-time device interaction using AWS IoT SDK.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, Callable, List

from .aws_iot_websocket import AWSIoTWebSocketConnection
from .models import DeviceStatus, Reservation, EnergyUsage
from .exceptions import WebSocketError, MQTTError, CommunicationError

logger = logging.getLogger(__name__)

class NaviLinkMQTT:
    """Handles MQTT over WebSocket communication with NaviLink devices using AWS IoT SDK."""
    
    # AWS IoT endpoint from navilink_api
    IOT_ENDPOINT = "a1t30mldyslmuq-ats.iot.us-east-1.amazonaws.com"
    
    # MQTT command constants from HAR analysis
    CMD_GET_DEVICE_INFO = 16777217  # Get device information (DID)
    CMD_GET_STATUS = 16777219       # Get device status
    CMD_GET_RESERVATIONS = 16777222 # Get reservations
    
    def __init__(
        self,
        client: 'NaviLinkClient',
        device: 'NaviLinkDevice',
        session: Optional = None
    ):
        """
        Initialize MQTT connection handler.
        
        Args:
            client: Parent NaviLinkClient instance
            device: NaviLinkDevice instance
            session: Optional (unused, kept for compatibility)
        """
        self._client = client
        self._device = device
        
        self._aws_connection: Optional[AWSIoTWebSocketConnection] = None
        self._connected = False
        self._monitoring = False
        
        # Use UUID as client ID like navilink_api
        from .utils import generate_session_id
        self._session_id = generate_session_id()
        
        # Message handling
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._status_callback: Optional[Callable[[DeviceStatus], None]] = None
        
        # Topic patterns from navilink_api analysis
        self._command_topic_base = f"cmd/{self._device.device_type}/navilink-{self._device.mac_address}"
        self._response_topic_base = f"cmd/{self._device.device_type}/{self._get_group_id()}/{self._get_user_id()}/{self._session_id}/res"
        
    def _get_group_id(self) -> str:
        """Get user group ID."""
        # From navilink_api analysis, this appears to be the homeSeq from device info
        if hasattr(self._device, 'home_seq') and self._device.home_seq:
            return str(self._device.home_seq)
        return "25004"  # Default from HAR analysis
    
    def _get_user_id(self) -> str:
        """Get user ID."""
        user_info = self._client.user_info
        if user_info and user_info.user_id:
            return user_info.user_id
        return "36283"  # Default from HAR analysis
    
    async def connect(self):
        """
        Connect to MQTT via AWS IoT WebSocket.
        
        Raises:
            WebSocketError: If connection fails
        """
        try:
            # Get authentication info
            user_info = self._client.user_info
            if not user_info:
                raise WebSocketError("Not authenticated")
            
            # Get AWS credentials from auth
            aws_creds = self._client._auth.aws_credentials
            if not aws_creds:
                raise WebSocketError("No AWS credentials available")
            
            logger.info("Connecting to AWS IoT via WebSocket...")
            
            # Create AWS IoT WebSocket connection
            self._aws_connection = AWSIoTWebSocketConnection(
                endpoint=self.IOT_ENDPOINT,
                access_key_id=aws_creds["accessKeyId"],
                secret_access_key=aws_creds["secretKey"],
                session_token=aws_creds["sessionToken"],
                client_id=self._session_id,
                region="us-east-1"
            )
            
            # Set up message callback
            self._aws_connection.set_message_callback(self._on_message)
            
            # Connect
            await self._aws_connection.connect()
            
            # Subscribe to response topics
            await self._subscribe_to_topics()
            
            self._connected = True
            logger.info(f"Connected to AWS IoT for device {self._device.mac_address}")
            
        except Exception as e:
            logger.error(f"Failed to connect to AWS IoT: {e}")
            self._connected = False
            raise WebSocketError(f"Failed to connect to MQTT: {e}")
    
    async def disconnect(self):
        """Disconnect from AWS IoT WebSocket."""
        self._monitoring = False
        self._connected = False
        
        if self._aws_connection:
            try:
                await self._aws_connection.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting AWS IoT: {e}")
            finally:
                self._aws_connection = None
            
        # Cancel any pending responses
        for future in self._pending_responses.values():
            if not future.done():
                future.cancel()
        self._pending_responses.clear()
        
        logger.info(f"Disconnected from AWS IoT for device {self._device.mac_address}")
    
    def _on_message(self, topic: str, payload: bytes):
        """
        Handle incoming MQTT message.
        
        Args:
            topic: MQTT topic
            payload: Message payload
        """
        try:
            # Parse JSON payload
            message_text = payload.decode('utf-8')
            message_data = json.loads(message_text)
            
            logger.info(f"📨 Received message on topic: {topic}")
            logger.info(f"📨 Message content: {message_text}")
            
            # Handle response messages
            if "/res/" in topic:
                asyncio.create_task(self._handle_device_response(topic, message_data))
            else:
                logger.info(f"📨 Non-response message: {topic}")
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            logger.info(f"Raw message: {payload}")
    
    async def _subscribe_to_topics(self):
        """Subscribe to device response topics."""
        # Based on navilink_api analysis, subscribe to different topics
        topics = [
            f"{self._command_topic_base}/res/channelinfo",
            f"{self._response_topic_base}/channelinfo", 
            f"{self._command_topic_base}/res/channelstatus",
            f"{self._response_topic_base}/channelstatus"
        ]
        
        successful_subscriptions = 0
        for topic in topics:
            try:
                success = await self._aws_connection.subscribe(topic, qos=1)
                if success:
                    logger.debug(f"Subscribed to: {topic}")
                    successful_subscriptions += 1
                else:
                    logger.debug(f"Subscription timeout for: {topic}")
            except Exception as e:
                logger.debug(f"Failed to subscribe to {topic}: {e}")
        
        logger.info(f"Successfully subscribed to {successful_subscriptions}/{len(topics)} topics")
    
    async def _handle_device_response(self, topic: str, message_data: Dict[str, Any]):
        """
        Handle device response message.
        
        Args:
            topic: MQTT topic
            message_data: Parsed message data
        """
        try:
            session_id = message_data.get("sessionID")
            response_data = message_data.get("response", {})
            
            logger.debug(f"Device response for session {session_id}")
            
            # Complete pending future if exists
            if session_id in self._pending_responses:
                future = self._pending_responses.pop(session_id)
                if not future.done():
                    future.set_result(response_data)
            
            # Handle status updates
            if "status" in response_data or "channelStatus" in response_data:
                await self._handle_status_update(response_data)
                
        except Exception as e:
            logger.error(f"Error parsing device response: {e}")
    
    async def _handle_status_update(self, response_data: Dict[str, Any]):
        """
        Handle status update message.
        
        Args:
            response_data: Status update data
        """
        try:
            # Parse based on navilink_api format which has channelStatus
            if "channelStatus" in response_data:
                channel_status = response_data["channelStatus"].get("channel", {})
                status = self._parse_channel_status(channel_status)
            else:
                status = self._parse_device_status(response_data)
                
            if status and self._status_callback:
                if asyncio.iscoroutinefunction(self._status_callback):
                    await self._status_callback(status)
                else:
                    self._status_callback(status)
        except Exception as e:
            logger.error(f"Error handling status update: {e}")
    
    def _parse_channel_status(self, channel_data: Dict[str, Any]) -> Optional[DeviceStatus]:
        """
        Parse channel status from navilink_api format.
        
        Args:
            channel_data: Channel status data
            
        Returns:
            DeviceStatus object or None if parsing fails
        """
        try:
            # Map navilink_api channel format to our DeviceStatus format
            return DeviceStatus(
                command=0,  # Not in channel status
                outside_temperature=0,  # Not in channel status
                special_function_status=0,
                did_reload=0,
                error_code=channel_data.get("errorCodePrimary", 0),
                sub_error_code=channel_data.get("errorCodeSecondary", 0),
                operation_mode=1 if channel_data.get("powerStatus") else 0,
                operation_busy=0,
                freeze_protection_use=0,
                dhw_use=1 if channel_data.get("onDemandUseFlag") else 0,
                dhw_use_sustained=0,
                dhw_temperature=channel_data.get("avgOutletTemp", 0),
                dhw_temperature_setting=channel_data.get("DHWSettingTemp", 0),
                program_reservation_use=0,
                smart_diagnostic=0,
                fault_status1=0,
                fault_status2=0,
                wifi_rssi=0,  # Not in channel status
                eco_use=0,
                dhw_target_temperature_setting=channel_data.get("DHWSettingTemp", 0),
                # Set remaining fields to default values
                **{field: 0 for field in DeviceStatus.__dataclass_fields__ 
                   if field not in ['command', 'outside_temperature', 'special_function_status',
                                   'did_reload', 'error_code', 'sub_error_code', 'operation_mode',
                                   'operation_busy', 'freeze_protection_use', 'dhw_use',
                                   'dhw_use_sustained', 'dhw_temperature', 'dhw_temperature_setting',
                                   'program_reservation_use', 'smart_diagnostic', 'fault_status1',
                                   'fault_status2', 'wifi_rssi', 'eco_use', 'dhw_target_temperature_setting']}
            )
        except Exception as e:
            logger.error(f"Error parsing channel status: {e}")
            return None
    
    def _parse_device_status(self, data: Dict[str, Any]) -> Optional[DeviceStatus]:
        """
        Parse device status from original HAR format.
        
        Args:
            data: Raw status data
            
        Returns:
            DeviceStatus object or None if parsing fails
        """
        try:
            status_data = data.get("status", {})
            
            # Create DeviceStatus with available fields
            return DeviceStatus(
                command=status_data.get("command", 0),
                outside_temperature=status_data.get("outsideTemperature", 0),
                special_function_status=status_data.get("specialFunctionStatus", 0),
                did_reload=status_data.get("didReload", 0),
                error_code=status_data.get("errorCode", 0),
                sub_error_code=status_data.get("subErrorCode", 0),
                operation_mode=status_data.get("operationMode", 0),
                operation_busy=status_data.get("operationBusy", 0),
                freeze_protection_use=status_data.get("freezeProtectionUse", 0),
                dhw_use=status_data.get("dhwUse", 0),
                dhw_use_sustained=status_data.get("dhwUseSustained", 0),
                dhw_temperature=status_data.get("dhwTemperature", 0),
                dhw_temperature_setting=status_data.get("dhwTemperatureSetting", 0),
                program_reservation_use=status_data.get("programReservationUse", 0),
                smart_diagnostic=status_data.get("smartDiagnostic", 0),
                fault_status1=status_data.get("faultStatus1", 0),
                fault_status2=status_data.get("faultStatus2", 0),
                wifi_rssi=status_data.get("wifiRssi", 0),
                eco_use=status_data.get("ecoUse", 0),
                dhw_target_temperature_setting=status_data.get("dhwTargetTemperatureSetting", 0),
                # Set remaining fields with defaults from status_data
                **{field: status_data.get(field, 0) for field in DeviceStatus.__dataclass_fields__ 
                   if field not in ['command', 'outside_temperature', 'special_function_status',
                                   'did_reload', 'error_code', 'sub_error_code', 'operation_mode',
                                   'operation_busy', 'freeze_protection_use', 'dhw_use',
                                   'dhw_use_sustained', 'dhw_temperature', 'dhw_temperature_setting',
                                   'program_reservation_use', 'smart_diagnostic', 'fault_status1',
                                   'fault_status2', 'wifi_rssi', 'eco_use', 'dhw_target_temperature_setting']}
            )
        except Exception as e:
            logger.error(f"Error parsing device status: {e}")
            return None
    
    async def send_device_command(
        self, 
        command: int, 
        topic_suffix: str = "",
        response_topic_suffix: str = "",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send command to device and wait for response.
        
        Args:
            command: Command ID
            topic_suffix: Additional topic suffix (e.g., "/channelinfo")
            additional_data: Additional command parameters
            
        Returns:
            Device response data
        """
        if not self._connected:
            raise MQTTError("Not connected to MQTT")
        
        # Generate unique session ID for this request
        request_session_id = str(int(time.time() * 1000))
        
        # Build command message based on navilink_api analysis
        response_suffix = response_topic_suffix or topic_suffix.split('/')[-1] if topic_suffix else ""
        command_data = {
            "clientID": self._session_id,
            "protocolVersion": 1,  # Based on navilink_api
            "request": {
                "additionalValue": self._device.additional_value,
                "command": command,
                "deviceType": self._device.device_type,
                "macAddress": self._device.mac_address,
                **(additional_data or {})
            },
            "requestTopic": f"{self._command_topic_base}/{topic_suffix}",
            "responseTopic": f"{self._response_topic_base}/{response_suffix}" if response_suffix else self._response_topic_base,
            "sessionID": request_session_id
        }
        
        # Create JSON payload
        payload = json.dumps(command_data).encode('utf-8')
        
        # Create future for response
        response_future = asyncio.Future()
        self._pending_responses[request_session_id] = response_future
        
        # Publish via AWS IoT connection
        topic = f"{self._command_topic_base}/{topic_suffix}"
        logger.info(f"📤 Sending command {command} to topic: {topic}")
        logger.info(f"📤 Command payload: {json.dumps(command_data, indent=2)}")
        
        success = await self._aws_connection.publish(topic, payload, qos=1)
        if not success:
            raise MQTTError(f"Failed to publish command {command}")
        
        logger.info(f"📤 Command {command} published successfully")
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            self._pending_responses.pop(request_session_id, None)
            raise MQTTError(f"Command timeout for command {command}")
    
    async def get_channel_info(self) -> Dict[str, Any]:
        """
        Get channel information (device info).
        
        Returns:
            Channel info dictionary
        """
        # Based on navilink_api: status/start request -> channelinfo response
        response = await self.send_device_command(self.CMD_GET_DEVICE_INFO, "status/start", response_topic_suffix="channelinfo")
        return response
    
    async def get_device_status(self) -> DeviceStatus:
        """
        Get current device status.
        
        Returns:
            DeviceStatus object
        """
        # Try channel status first (navilink_api approach)
        try:
            response = await self.send_device_command(16777220, "status/channelstatus", 
                                                    {"status": {"channelNumber": 1, "unitNumberEnd": 1, "unitNumberStart": 1}})
            if "channelStatus" in response:
                status = self._parse_channel_status(response["channelStatus"].get("channel", {}))
            else:
                status = self._parse_device_status({"status": response})
        except Exception:
            # Fall back to original status command
            response = await self.send_device_command(self.CMD_GET_STATUS)
            status = self._parse_device_status({"status": response})
        
        if not status:
            raise MQTTError("Failed to parse device status")
            
        return status
    
    async def get_reservations(self) -> List[Reservation]:
        """
        Get device reservations.
        
        Returns:
            List of Reservation objects
        """
        response = await self.send_device_command(self.CMD_GET_RESERVATIONS, "rsv/rd")
        
        # Parse reservations from response
        reservations = []
        for rsv_data in response.get("reservation", []):
            reservation = Reservation(
                id=rsv_data.get("id"),
                start_time=rsv_data.get("startTime"),
                end_time=rsv_data.get("endTime"),
                temperature=rsv_data.get("temperature"),
                enabled=rsv_data.get("enabled"),
                recurring=rsv_data.get("recurring"),
                days_of_week=rsv_data.get("daysOfWeek")
            )
            reservations.append(reservation)
            
        return reservations
    
    async def get_energy_usage(
        self, 
        period: str = "daily", 
        days: int = 7
    ) -> List[EnergyUsage]:
        """
        Get energy usage data.
        
        Args:
            period: Period type ("daily", "monthly")  
            days: Number of periods to retrieve
            
        Returns:
            List of EnergyUsage objects
        """
        # TODO: Implement energy usage commands based on navilink_api analysis
        return []
    
    async def start_monitoring(self):
        """Start real-time monitoring loop."""
        self._monitoring = True
        
        # Request initial channel info like navilink_api does
        try:
            await self.get_channel_info()
        except Exception as e:
            logger.warning(f"Failed to get initial channel info: {e}")
    
    async def stop_monitoring(self):
        """Stop real-time monitoring."""
        self._monitoring = False
    
    def set_status_callback(self, callback: Callable[[DeviceStatus], None]):
        """
        Set callback for status updates.
        
        Args:
            callback: Function to call on status updates
        """
        self._status_callback = callback
    
    @property
    def is_connected(self) -> bool:
        """Check if MQTT is connected."""
        return self._connected and self._aws_connection and self._aws_connection.is_connected