"""
MQTT/WebSocket communication for real-time device interaction.
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
    """Handles MQTT over WebSocket communication with NaviLink devices."""
    
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
        
        # Use device MAC address as part of client ID like navilink_api
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
            
            logger.debug(f"Received message on topic {topic}: {message_text[:100]}...")
            
            # Handle response messages
            if "/res/" in topic:
                asyncio.create_task(self._handle_device_response(topic, message_data))
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
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
    
    async def _send_mqtt_connect(self):
        """Send MQTT CONNECT packet."""
        # Based on navilink_api analysis - use different username format
        client_id = self._session_id
        username = "?SDK=Android&Version=2.16.12"  # Updated version string
        
        connect_packet = self._mqtt_protocol.create_connect_packet(
            client_id=client_id,
            username=username,
            clean_session=True,
            keep_alive=300  # 5 minutes
        )
        
        logger.debug(f"Sending CONNECT packet: {connect_packet.hex()}")
        await self._websocket.send(connect_packet)
    
    async def _wait_for_connack(self):
        """Wait for MQTT CONNACK response."""
        try:
            # Wait for CONNACK with timeout
            data = await asyncio.wait_for(self._websocket.recv(), timeout=10.0)
            
            if isinstance(data, str):
                data = data.encode()
            
            message = self._mqtt_protocol.parse_packet(data)
            
            if message.packet_type == MQTTPacketType.CONNACK:
                connack = self._mqtt_protocol.parse_connack(message.payload)
                if connack["return_code"] == 0:
                    logger.info("MQTT connection accepted")
                else:
                    raise MQTTError(f"MQTT connection refused: {connack['return_code_name']}")
            else:
                raise MQTTError(f"Expected CONNACK, got packet type {message.packet_type}")
                
        except asyncio.TimeoutError:
            raise MQTTError("Timeout waiting for CONNACK")
    
    async def _subscribe_to_topics(self):
        """Subscribe to device response topics."""
        # Based on navilink_api analysis, subscribe to different topics
        topics = [
            f"{self._command_topic_base}/res/channelinfo",
            f"{self._response_topic_base}/channelinfo", 
            f"{self._command_topic_base}/res/channelstatus",
            f"{self._response_topic_base}/channelstatus",
            f"{self._command_topic_base}/res/controlfail",
            f"{self._command_topic_base}/connection",
            "evt/+/mobile/event/disconnect-mqtt"
        ]
        
        for topic in topics:
            subscribe_packet = self._mqtt_protocol.create_subscribe_packet(topic, qos=1)
            logger.debug(f"Subscribing to: {topic}")
            await self._websocket.send(subscribe_packet)
            
            # Wait for SUBACK
            await self._wait_for_suback()
    
    async def _wait_for_suback(self):
        """Wait for SUBSCRIBE acknowledgment."""
        try:
            data = await asyncio.wait_for(self._websocket.recv(), timeout=5.0)
            
            if isinstance(data, str):
                data = data.encode()
            
            message = self._mqtt_protocol.parse_packet(data)
            
            if message.packet_type == MQTTPacketType.SUBACK:
                suback = self._mqtt_protocol.parse_suback(message.payload)
                logger.debug(f"SUBACK received for packet {suback['packet_id']}")
            else:
                logger.warning(f"Expected SUBACK, got packet type {message.packet_type}")
                
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for SUBACK")
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages."""
        try:
            async for message in self._websocket:
                try:
                    if isinstance(message, str):
                        message = message.encode()
                    
                    mqtt_message = self._mqtt_protocol.parse_packet(message)
                    await self._handle_mqtt_message(mqtt_message)
                    
                except Exception as e:
                    logger.error(f"Error processing MQTT message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("MQTT WebSocket connection closed")
            self._connected = False
        except Exception as e:
            logger.error(f"Error in MQTT message handler: {e}")
            self._connected = False
    
    async def _handle_mqtt_message(self, message):
        """
        Handle parsed MQTT message.
        
        Args:
            message: Parsed MQTTMessage object
        """
        if message.packet_type == MQTTPacketType.PUBLISH:
            publish_data = self._mqtt_protocol.parse_publish(message.flags, message.payload)
            topic = publish_data["topic"]
            payload = publish_data["payload"]
            
            logger.debug(f"Received PUBLISH on topic: {topic}")
            
            # Send PUBACK if QoS > 0
            if publish_data["qos"] > 0 and publish_data["packet_id"]:
                puback_packet = struct.pack('!BBH', 0x40, 0x02, publish_data["packet_id"])
                await self._websocket.send(puback_packet)
            
            # Handle response messages
            if "/res" in topic:
                await self._handle_device_response(topic, payload)
            
        elif message.packet_type == MQTTPacketType.PUBACK:
            logger.debug("PUBACK received")
            
        elif message.packet_type == MQTTPacketType.PINGRESP:
            logger.debug("PINGRESP received")
            
        else:
            logger.debug(f"Unhandled MQTT packet type: {message.packet_type}")
    
    async def _handle_device_response(self, topic: str, payload: bytes):
        """
        Handle device response message.
        
        Args:
            topic: MQTT topic
            payload: Message payload
        """
        try:
            # Parse JSON response
            response_text = payload.decode('utf-8')
            response_data = json.loads(response_text)
            
            logger.debug(f"Device response: {response_text[:100]}...")
            
            # Extract session ID to match with pending requests
            session_id = response_data.get("sessionID")
            
            # Complete pending future if exists
            if session_id in self._pending_responses:
                future = self._pending_responses.pop(session_id)
                if not future.done():
                    future.set_result(response_data.get("response", {}))
            
            # Handle status updates
            if "status" in response_data.get("response", {}):
                await self._handle_status_update(response_data["response"])
                
        except Exception as e:
            logger.error(f"Error parsing device response: {e}")
    
    async def _handle_status_update(self, response_data: Dict[str, Any]):
        """
        Handle status update message.
        
        Args:
            response_data: Status update data
        """
        try:
            status = self._parse_device_status(response_data)
            if status and self._status_callback:
                if asyncio.iscoroutinefunction(self._status_callback):
                    await self._status_callback(status)
                else:
                    self._status_callback(status)
        except Exception as e:
            logger.error(f"Error handling status update: {e}")
    
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
        topic_suffix: str = "",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send command to device and wait for response.
        
        Args:
            command: Command ID
            topic_suffix: Additional topic suffix (e.g., "/did")
            additional_data: Additional command parameters
            
        Returns:
            Device response data
        """
        if not self._connected:
            raise MQTTError("Not connected to MQTT")
        
        # Generate unique session ID for this request
        request_session_id = str(int(time.time() * 1000))
        
        # Build command message based on HAR analysis
        command_data = {
            "clientID": self._session_id,
            "protocolVersion": 2,
            "request": {
                "additionalValue": self._device.additional_value,
                "command": command,
                "deviceType": self._device.device_type,
                "macAddress": self._device.mac_address,
                **(additional_data or {})
            },
            "requestTopic": f"{self._command_topic_base}{topic_suffix}",
            "responseTopic": f"{self._response_topic_base}{topic_suffix}",
            "sessionID": request_session_id
        }
        
        # Create JSON payload
        payload = json.dumps(command_data).encode('utf-8')
        
        # Create MQTT PUBLISH packet
        topic = f"{self._command_topic_base}{topic_suffix}"
        publish_packet = self._mqtt_protocol.create_publish_packet(
            topic=topic,
            payload=payload,
            qos=1
        )
        
        # Create future for response
        response_future = asyncio.Future()
        self._pending_responses[request_session_id] = response_future
        
        logger.debug(f"Sending command {command} to topic: {topic}")
        
        # Send command
        await self._websocket.send(publish_packet)
        
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
    
    async def get_device_info(self) -> Dict[str, Any]:
        """
        Get detailed device information.
        
        Returns:
            Device info dictionary
        """
        response = await self.send_device_command(self.CMD_GET_DEVICE_INFO, "/did")
        return response
    
    async def get_reservations(self) -> List[Reservation]:
        """
        Get device reservations.
        
        Returns:
            List of Reservation objects
        """
        response = await self.send_device_command(self.CMD_GET_RESERVATIONS, "/rsv/rd")
        
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
        # TODO: Implement energy usage commands based on HAR analysis
        # This requires analyzing the energy usage query commands
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