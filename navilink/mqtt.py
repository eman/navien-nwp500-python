"""
MQTT/WebSocket communication for real-time device interaction.
"""

import asyncio
import base64
import json
import logging
from typing import Dict, Any, Optional, Callable, List
import websockets
import aiohttp

from .models import DeviceStatus, Reservation, EnergyUsage
from .exceptions import WebSocketError, MQTTError, CommunicationError
from .utils import generate_session_id, create_websocket_url, parse_device_response

logger = logging.getLogger(__name__)

class NaviLinkMQTT:
    """Handles MQTT over WebSocket communication with NaviLink devices."""
    
    WS_BASE_URL = "wss://nlus-iot.naviensmartcontrol.com/mqtt"
    
    # MQTT command constants from HAR analysis
    CMD_GET_DEVICE_INFO = 16777217  # Get device information (DID)
    CMD_GET_STATUS = 16777219       # Get device status
    CMD_GET_RESERVATIONS = 16777222 # Get reservations
    
    def __init__(
        self,
        client: 'NaviLinkClient',
        device: 'NaviLinkDevice',
        session: Optional[aiohttp.ClientSession] = None
    ):
        """
        Initialize MQTT connection handler.
        
        Args:
            client: Parent NaviLinkClient instance
            device: NaviLinkDevice instance
            session: Optional aiohttp session
        """
        self._client = client
        self._device = device
        self._session = session
        
        self._websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._connected = False
        self._monitoring = False
        self._session_id = generate_session_id()
        
        # Message handling
        self._message_id = 1
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._status_callback: Optional[Callable[[DeviceStatus], None]] = None
        
        # Topic patterns
        self._command_topic = f"cmd/{self._device.device_type}/navilink-{self._device.mac_address}/st"
        self._response_topic_base = f"cmd/{self._device.device_type}/{self._get_group_id()}/{self._get_user_id()}/{self._session_id}/res"
        
    def _get_group_id(self) -> str:
        """Get user group ID."""
        # From HAR analysis, this appears to be the homeSeq from device info
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
        Connect to MQTT WebSocket.
        
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
            
            # Create signed WebSocket URL
            ws_url = create_websocket_url(
                base_url=self.WS_BASE_URL,
                access_key=aws_creds["accessKeyId"],
                secret_key=aws_creds["secretKey"],
                session_token=aws_creds["sessionToken"]
            )
            
            logger.info(f"Generated WebSocket URL: {ws_url[:100]}...")
            logger.debug(f"Full WebSocket URL: {ws_url}")
            logger.info(f"Using Access Key: {aws_creds['accessKeyId'][:10]}...")
            logger.info(f"Session Token length: {len(aws_creds['sessionToken'])}")
            
            logger.debug(f"Connecting to WebSocket: {ws_url[:100]}...")
            
            # Connect to WebSocket
            self._websocket = await websockets.connect(
                ws_url,
                subprotocols=["mqtt"],
                additional_headers={
                    "User-Agent": "NaviLink-Python/0.1.0"
                }
            )
            
            # Send MQTT CONNECT packet
            await self._send_mqtt_connect()
            
            # Start message handling loop
            asyncio.create_task(self._message_handler())
            
            # Subscribe to response topics
            await self._subscribe_to_topics()
            
            self._connected = True
            logger.info(f"Connected to MQTT for device {self._device.mac_address}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            self._connected = False
            raise WebSocketError(f"Failed to connect to MQTT: {e}")
    
    async def disconnect(self):
        """Disconnect from MQTT WebSocket."""
        self._monitoring = False
        self._connected = False
        
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
            
        # Cancel any pending responses
        for future in self._pending_responses.values():
            if not future.done():
                future.cancel()
        self._pending_responses.clear()
        
        logger.info(f"Disconnected from MQTT for device {self._device.mac_address}")
    
    async def _send_mqtt_connect(self):
        """Send MQTT CONNECT packet."""
        # Based on HAR analysis, create MQTT CONNECT packet
        client_id = f"{self._session_id}"
        
        # MQTT CONNECT packet structure (simplified)
        # This is a basic implementation - may need refinement based on actual protocol
        connect_packet = {
            "type": "connect",
            "clientId": client_id,
            "keepalive": 60,
            "username": f"?SDK=Android&Version=2.22.0",
            "clean": True
        }
        
        # Convert to binary MQTT format (simplified)
        # In a full implementation, this would create proper MQTT binary packets
        await self._send_raw_message(json.dumps(connect_packet))
    
    async def _subscribe_to_topics(self):
        """Subscribe to device response topics."""
        topics = [
            f"{self._response_topic_base}",
            f"{self._response_topic_base}/did", 
            f"{self._response_topic_base}/rsv/rd",
            f"{self._response_topic_base}/energy-usage-daily-query/rd",
            f"{self._response_topic_base}/energy-usage-monthly-query/rd",
            f"{self._response_topic_base}/recirc-rsv/rd"
        ]
        
        for i, topic in enumerate(topics, 1):
            subscribe_msg = {
                "type": "subscribe",
                "messageId": i,
                "topic": topic,
                "qos": 1
            }
            await self._send_raw_message(json.dumps(subscribe_msg))
    
    async def _send_raw_message(self, message: str):
        """Send raw message to WebSocket."""
        if not self._websocket:
            raise MQTTError("Not connected to WebSocket")
            
        # Encode message as base64 for binary transport
        encoded = base64.b64encode(message.encode()).decode()
        await self._websocket.send(encoded)
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages."""
        try:
            async for message in self._websocket:
                try:
                    # Decode message
                    if isinstance(message, bytes):
                        decoded = base64.b64decode(message).decode()
                    else:
                        decoded = message
                        
                    # Parse JSON message
                    try:
                        data = json.loads(decoded)
                    except json.JSONDecodeError:
                        logger.debug(f"Non-JSON message received: {decoded}")
                        continue
                    
                    await self._handle_message(data)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
            self._connected = False
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            self._connected = False
    
    async def _handle_message(self, data: Dict[str, Any]):
        """
        Handle parsed message data.
        
        Args:
            data: Parsed message data
        """
        message_type = data.get("type")
        
        if message_type == "publish":
            topic = data.get("topic", "")
            payload = data.get("payload", {})
            
            # Handle different message types based on topic
            if "/res" in topic and "response" in payload:
                await self._handle_device_response(payload)
            elif "/st" in topic:
                await self._handle_status_update(payload)
                
        elif message_type == "suback":
            logger.debug("Subscription acknowledged")
            
        elif message_type == "connack":
            logger.debug("Connection acknowledged")
    
    async def _handle_device_response(self, payload: Dict[str, Any]):
        """
        Handle device response message.
        
        Args:
            payload: Message payload
        """
        session_id = payload.get("sessionID")
        response_data = payload.get("response", {})
        
        # Complete pending future if exists
        if session_id in self._pending_responses:
            future = self._pending_responses.pop(session_id)
            if not future.done():
                future.set_result(response_data)
    
    async def _handle_status_update(self, payload: Dict[str, Any]):
        """
        Handle status update message.
        
        Args:
            payload: Status update payload
        """
        try:
            status = self._parse_device_status(payload)
            if status and self._status_callback:
                self._status_callback(status)
        except Exception as e:
            logger.error(f"Error parsing status update: {e}")
    
    def _parse_device_status(self, data: Dict[str, Any]) -> Optional[DeviceStatus]:
        """
        Parse device status from response data.
        
        Args:
            data: Raw status data
            
        Returns:
            DeviceStatus object or None if parsing fails
        """
        try:
            status_data = data.get("status", {})
            
            # Create DeviceStatus with available fields
            # Many fields default to 0 if not present
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
                tank_upper_temperature=status_data.get("tankUpperTemperature", 0),
                tank_lower_temperature=status_data.get("tankLowerTemperature", 0),
                discharge_temperature=status_data.get("dischargeTemperature", 0),
                suction_temperature=status_data.get("suctionTemperature", 0),
                evaporator_temperature=status_data.get("evaporatorTemperature", 0),
                ambient_temperature=status_data.get("ambientTemperature", 0),
                target_super_heat=status_data.get("targetSuperHeat", 0),
                comp_use=status_data.get("compUse", 0),
                eev_use=status_data.get("eevUse", 0),
                eva_fan_use=status_data.get("evaFanUse", 0),
                current_inst_power=status_data.get("currentInstPower", 0),
                shut_off_valve_use=status_data.get("shutOffValveUse", 0),
                con_ovr_sensor_use=status_data.get("conOvrSensorUse", 0),
                wtr_ovr_sensor_use=status_data.get("wtrOvrSensorUse", 0),
                dhw_charge_per=status_data.get("dhwChargePer", 0),
                dr_event_status=status_data.get("drEventStatus", 0),
                vacation_day_setting=status_data.get("vacationDaySetting", 0),
                vacation_day_elapsed=status_data.get("vacationDayElapsed", 0),
                freeze_protection_temperature=status_data.get("freezeProtectionTemperature", 0),
                anti_legionella_use=status_data.get("antiLegionellaUse", 0),
                anti_legionella_period=status_data.get("antiLegionellaPeriod", 0),
                anti_legionella_operation_busy=status_data.get("antiLegionellaOperationBusy", 0),
                program_reservation_type=status_data.get("programReservationType", 0),
                dhw_operation_setting=status_data.get("dhwOperationSetting", 0),
                temperature_type=status_data.get("temperatureType", 0),
                temp_formula_type=status_data.get("tempFormulaType", 0),
                error_buzzer_use=status_data.get("errorBuzzerUse", 0),
                current_heat_use=status_data.get("currentHeatUse", 0),
                current_inlet_temperature=status_data.get("currentInletTemperature", 0),
                current_statenum=status_data.get("currentStatenum", 0),
                target_fan_rpm=status_data.get("targetFanRpm", 0),
                current_fan_rpm=status_data.get("currentFanRpm", 0),
                fan_pwm=status_data.get("fanPwm", 0),
                dhw_temperature2=status_data.get("dhwTemperature2", 0),
                current_dhw_flow_rate=status_data.get("currentDhwFlowRate", 0),
                mixing_rate=status_data.get("mixingRate", 0),
                eev_step=status_data.get("eevStep", 0),
                current_super_heat=status_data.get("currentSuperHeat", 0),
                heat_upper_use=status_data.get("heatUpperUse", 0),
                heat_lower_use=status_data.get("heatLowerUse", 0),
                scald_use=status_data.get("scaldUse", 0),
                air_filter_alarm_use=status_data.get("airFilterAlarmUse", 0),
                air_filter_alarm_period=status_data.get("airFilterAlarmPeriod", 0),
                air_filter_alarm_elapsed=status_data.get("airFilterAlarmElapsed", 0),
                cumulated_op_time_eva_fan=status_data.get("cumulatedOpTimeEvaFan", 0),
                cumulated_dhw_flow_rate=status_data.get("cumulatedDhwFlowRate", 0),
                tou_status=status_data.get("touStatus", 0),
                hp_upper_on_temp_setting=status_data.get("hpUpperOnTempSetting", 0),
                hp_upper_off_temp_setting=status_data.get("hpUpperOffTempSetting", 0),
                hp_lower_on_temp_setting=status_data.get("hpLowerOnTempSetting", 0),
                hp_lower_off_temp_setting=status_data.get("hpLowerOffTempSetting", 0),
                he_upper_on_temp_setting=status_data.get("heUpperOnTempSetting", 0),
                he_upper_off_temp_setting=status_data.get("heUpperOffTempSetting", 0),
                he_lower_on_temp_setting=status_data.get("heLowerOnTempSetting", 0),
                he_lower_off_temp_setting=status_data.get("heLowerOffTempSetting", 0),
                hp_upper_on_diff_temp_setting=status_data.get("hpUpperOnDiffTempSetting", 0),
                hp_upper_off_diff_temp_setting=status_data.get("hpUpperOffDiffTempSetting", 0),
                hp_lower_on_diff_temp_setting=status_data.get("hpLowerOnDiffTempSetting", 0),
                hp_lower_off_diff_temp_setting=status_data.get("hpLowerOffDiffTempSetting", 0),
                he_upper_on_diff_temp_setting=status_data.get("heUpperOnDiffTempSetting", 0),
                he_upper_off_diff_temp_setting=status_data.get("heUpperOffDiffTempSetting", 0),
                he_lower_on_tdiffemp_setting=status_data.get("heLowerOnTDiffempSetting", 0),
                he_lower_off_diff_temp_setting=status_data.get("heLowerOffDiffTempSetting", 0),
                dr_override_status=status_data.get("drOverrideStatus", 0),
                tou_override_status=status_data.get("touOverrideStatus", 0),
                total_energy_capacity=status_data.get("totalEnergyCapacity", 0),
                available_energy_capacity=status_data.get("availableEnergyCapacity", 0)
            )
        except Exception as e:
            logger.error(f"Error parsing device status: {e}")
            return None
    
    async def send_device_command(
        self, 
        command: int, 
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send command to device and wait for response.
        
        Args:
            command: Command ID
            additional_data: Additional command parameters
            
        Returns:
            Device response data
        """
        if not self._connected:
            raise MQTTError("Not connected to MQTT")
            
        # Generate unique session ID for this request
        request_session_id = f"{int(asyncio.get_event_loop().time() * 1000)}"
        
        # Build command message
        message = {
            "clientID": self._session_id,
            "protocolVersion": 2,
            "request": {
                "additionalValue": self._device.additional_value,
                "command": command,
                "deviceType": self._device.device_type,
                "macAddress": self._device.mac_address,
                **(additional_data or {})
            },
            "requestTopic": f"{self._command_topic}",
            "responseTopic": f"{self._response_topic_base}",
            "sessionID": request_session_id
        }
        
        # Create future for response
        response_future = asyncio.Future()
        self._pending_responses[request_session_id] = response_future
        
        # Send command
        command_json = json.dumps(message)
        await self._send_raw_message(command_json)
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            self._pending_responses.pop(request_session_id, None)
            raise MQTTError(f"Command timeout for command {command}")
    
    async def get_device_status(self) -> DeviceStatus:
        """
        Get current device status.
        
        Returns:
            DeviceStatus object
        """
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
        response = await self.send_device_command(self.CMD_GET_RESERVATIONS)
        
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
        # TODO: Implement energy usage command
        # This requires analyzing the energy usage query commands from HAR
        return []
    
    async def start_monitoring(self):
        """Start real-time monitoring loop."""
        self._monitoring = True
        
        # Request initial status
        try:
            await self.get_device_status()
        except Exception as e:
            logger.warning(f"Failed to get initial status: {e}")
    
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
        return self._connected and self._websocket and not self._websocket.closed