"""
MQTT/WebSocket communication for real-time device interaction using AWS IoT SDK v2 with MQTT5.
"""

import asyncio
import json
import logging
import time
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from .aws_iot_websocket import AWSIoTWebSocketConnection
from .config import ReconnectConfig
from .exceptions import MQTTError, WebSocketError
from .models import DeviceStatus, EnergyUsage, Reservation

if TYPE_CHECKING:
    from .client import NaviLinkClient
    from .device import NaviLinkDevice

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state enumeration."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class NaviLinkMQTT:
    """Enhanced MQTT handler with MQTT5 support, connection monitoring, and resilience."""

    # AWS IoT endpoint from navien_nwp500_api
    IOT_ENDPOINT = "a1t30mldyslmuq-ats.iot.us-east-1.amazonaws.com"

    # MQTT command constants from navien_nwp500_api analysis
    CMD_GET_DEVICE_INFO = 16777217  # Get channel info (setup)
    CMD_GET_STATUS = 16777219  # Get device status (from HAR file)
    CMD_GET_RESERVATIONS = 16777222  # Get reservations

    def __init__(
        self,
        client: "NaviLinkClient",
        device: "NaviLinkDevice",
        session: Optional[aiohttp.ClientSession] = None,
        reconnect_config: Optional[ReconnectConfig] = None,
    ):
        """
        Initialize enhanced MQTT connection handler.

        Args:
            client: Parent NaviLinkClient instance
            device: NaviLinkDevice instance
            session: Optional (unused, kept for compatibility)
            reconnect_config: Configuration for reconnection behavior
        """
        self._client = client
        self._device = device

        # Connection management
        self._aws_connection: Optional[AWSIoTWebSocketConnection] = None
        self._connection_state = ConnectionState.DISCONNECTED
        self._reconnect_config = reconnect_config or ReconnectConfig()
        self._retry_count = 0
        self._monitoring = False
        self._polling_task: Optional[asyncio.Task] = None
        self._connection_monitor_task: Optional[asyncio.Task] = None

        # Use UUID as client ID like navilink_api
        from .utils import generate_session_id

        self._session_id = generate_session_id()

        # Message handling
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._status_callback: Optional[Callable[[DeviceStatus], None]] = None

        # Enhanced metrics and monitoring
        self._message_count = 0
        self._last_message_time = 0
        self._connection_start_time = 0
        self._statistics = {
            "messages_received": 0,
            "messages_sent": 0,
            "reconnection_count": 0,
            "uptime_seconds": 0,
        }

        # Topic patterns from navien_nwp500_api analysis
        self._command_topic_base = (
            f"cmd/{self._device.device_type}/navilink-{self._device.mac_address}"
        )
        self._response_topic_base = f"cmd/{self._device.device_type}/{self._get_group_id()}/{self._get_user_id()}/{self._session_id}/res"

    def _get_group_id(self) -> str:
        """Get user group ID."""
        # From navilink_api analysis, this appears to be the homeSeq from device info
        if hasattr(self._device, "home_seq") and self._device.home_seq:
            return str(self._device.home_seq)
        return "25004"  # Default from HAR analysis

    def _get_user_id(self) -> str:
        """Get user ID."""
        user_info = self._client.user_info
        if user_info and user_info.user_id:
            return user_info.user_id
        return "36283"  # Default from HAR analysis

    @property
    def connection_state(self) -> ConnectionState:
        """Get current connection state."""
        return self._connection_state

    @property
    def statistics(self) -> Dict[str, Any]:
        """Get connection and message statistics."""
        stats = self._statistics.copy()
        if self._connection_start_time > 0:
            stats["uptime_seconds"] = time.time() - self._connection_start_time
        return stats

    async def connect(self, enable_auto_reconnect: bool = True):
        """
        Connect to MQTT via AWS IoT WebSocket with enhanced error handling.

        Args:
            enable_auto_reconnect: Whether to enable automatic reconnection on failures

        Raises:
            WebSocketError: If connection fails
        """
        try:
            self._connection_state = ConnectionState.CONNECTING

            # Get authentication info
            user_info = self._client.user_info
            if not user_info:
                raise WebSocketError("Not authenticated")

            # Get AWS credentials from auth
            aws_creds = self._client._auth.aws_credentials
            if not aws_creds:
                raise WebSocketError("No AWS credentials available")

            logger.info(f"🔌 Connecting to AWS IoT via WebSocket (MQTT5)...")

            # Create AWS IoT WebSocket connection with MQTT5
            self._aws_connection = AWSIoTWebSocketConnection(
                endpoint=self.IOT_ENDPOINT,
                access_key_id=aws_creds["accessKeyId"],
                secret_access_key=aws_creds["secretKey"],
                session_token=aws_creds["sessionToken"],
                client_id=self._session_id,
                region="us-east-1",
            )

            # Set up message callback
            self._aws_connection.set_message_callback(self._on_message)

            # Connect with retry logic
            await self._connect_with_retry()

            # Subscribe to response topics
            await self._subscribe_to_topics()

            # Mark as connected and start monitoring
            self._connection_state = ConnectionState.CONNECTED
            self._connection_start_time = time.time()
            self._retry_count = 0  # Reset retry count on successful connection

            # Start connection monitoring if auto-reconnect is enabled
            if enable_auto_reconnect:
                self._connection_monitor_task = asyncio.create_task(
                    self._connection_monitor()
                )

            logger.info(
                f"✅ Connected to AWS IoT for device {self._device.mac_address}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to connect to AWS IoT: {e}")
            self._connection_state = ConnectionState.FAILED
            raise WebSocketError(f"Failed to connect to MQTT: {e}")

    async def _connect_with_retry(self):
        """Connect with exponential backoff retry logic."""
        while self._retry_count < self._reconnect_config.max_retries:
            try:
                await self._aws_connection.connect()
                return  # Success

            except Exception as e:
                self._retry_count += 1

                if self._retry_count >= self._reconnect_config.max_retries:
                    logger.error(
                        f"❌ Max connection retries ({self._reconnect_config.max_retries}) exceeded"
                    )
                    raise

                # Calculate backoff delay with jitter
                delay = min(
                    self._reconnect_config.initial_delay
                    * (
                        self._reconnect_config.backoff_multiplier
                        ** (self._retry_count - 1)
                    ),
                    self._reconnect_config.max_delay,
                )

                if self._reconnect_config.jitter:
                    import random

                    delay *= 0.5 + random.random() * 0.5  # Add ±50% jitter

                logger.warning(
                    f"⏳ Connection attempt {self._retry_count} failed: {e}. Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)

    async def _connection_monitor(self):
        """Monitor connection health and auto-reconnect if needed."""
        while self._connection_state not in [
            ConnectionState.DISCONNECTED,
            ConnectionState.FAILED,
        ]:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Check if connection is still alive
                if not self._aws_connection or not self._aws_connection.is_connected:
                    logger.warning("🔌 Connection lost, attempting to reconnect...")
                    self._connection_state = ConnectionState.RECONNECTING
                    self._statistics["reconnection_count"] += 1

                    # Attempt reconnection
                    try:
                        await self._connect_with_retry()
                        await self._subscribe_to_topics()
                        self._connection_state = ConnectionState.CONNECTED
                        logger.info("✅ Reconnection successful")

                    except Exception as e:
                        logger.error(f"❌ Reconnection failed: {e}")
                        self._connection_state = ConnectionState.FAILED
                        break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")

    async def disconnect(self):
        """Disconnect from AWS IoT WebSocket."""
        # Stop monitoring first
        if self._monitoring:
            await self.stop_monitoring()

        # Stop connection monitoring
        if self._connection_monitor_task:
            self._connection_monitor_task.cancel()
            try:
                await self._connection_monitor_task
            except asyncio.CancelledError:
                pass
            self._connection_monitor_task = None

        self._connection_state = ConnectionState.DISCONNECTED

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

        logger.info(
            f"🔌 Disconnected from AWS IoT for device {self._device.mac_address}"
        )

    def _on_message(self, topic: str, payload: bytes):
        """
        Handle incoming MQTT message with enhanced logging and metrics.

        Args:
            topic: MQTT topic
            payload: Message payload
        """
        try:
            # Update statistics
            self._statistics["messages_received"] += 1
            self._last_message_time = time.time()

            # Parse JSON payload
            message_text = payload.decode("utf-8")
            message_data = json.loads(message_text)

            logger.info(f"📨 Received message on topic: {topic}")
            logger.debug(f"📨 Message content: {message_text}")

            # Handle response messages
            if "/res/" in topic or self._response_topic_base in topic:
                # Always use synchronous handling for now since we're in a callback
                # The AWS IoT SDK callback runs in a different thread context
                self._handle_device_response_sync(topic, message_data)
            else:
                logger.debug(f"📨 Non-response message: {topic}")

        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
            logger.debug(f"Raw message: {payload}")

    async def _subscribe_to_topics(self):
        """Subscribe to device response topics based on HAR file analysis."""
        # Topics from HAR file - responses come to these patterns
        topics = [
            f"{self._command_topic_base}/res",  # Main device response topic
            f"{self._response_topic_base}",  # User-specific response topic
            f"{self._response_topic_base}/did",  # Device info responses
            f"{self._response_topic_base}/st",  # Status responses
        ]

        successful_subscriptions = 0
        for topic in topics:
            try:
                # Retry subscription with backoff
                success = await self._subscribe_with_retry(topic, qos=1)
                if success:
                    logger.debug(f"✅ Subscribed to: {topic}")
                    successful_subscriptions += 1
                else:
                    logger.warning(f"⚠️ Failed to subscribe to: {topic}")
            except Exception as e:
                logger.warning(f"⚠️ Subscription error for {topic}: {e}")

        logger.info(
            f"📡 Successfully subscribed to {successful_subscriptions}/{len(topics)} topics"
        )

        if successful_subscriptions == 0:
            raise MQTTError("Failed to subscribe to any topics")

    async def _subscribe_with_retry(
        self, topic: str, qos: int = 1, max_retries: int = 3
    ) -> bool:
        """Subscribe with retry logic."""
        for attempt in range(max_retries):
            try:
                success = await self._aws_connection.subscribe(topic, qos=qos)
                if success:
                    return True

                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff

            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2**attempt)

        return False

    def _handle_device_response_sync(self, topic: str, message_data: Dict[str, Any]):
        """
        Handle device response message synchronously.

        Args:
            topic: MQTT topic
            message_data: Parsed message data
        """
        try:
            session_id = message_data.get("sessionID")
            response_data = message_data.get("response", {})

            logger.debug(f"📨 Processing response for session: {session_id}")
            logger.info(
                f"🔍 MQTT Response Data: {json.dumps(message_data, indent=2)[:500]}..."
            )
            logger.debug(
                f"📨 Response data keys: {list(response_data.keys()) if response_data else 'No response data'}"
            )

            # Update statistics
            self._statistics["messages_received"] += 1

            # Check if this is a status update we can extract data from
            if response_data:
                self._extract_and_log_status_data(response_data)

            if session_id and session_id in self._pending_responses:
                logger.info(f"✅ Response received for session {session_id}")

                # Get the future and set the result
                future = self._pending_responses.pop(session_id)
                if not future.done():
                    try:
                        # Try to use the event loop if available
                        loop = asyncio.get_running_loop()
                        loop.call_soon_threadsafe(future.set_result, message_data)
                    except RuntimeError:
                        # No event loop, set result directly (this is safe for futures)
                        logger.debug("Setting future result directly (no event loop)")
                        try:
                            future.set_result(message_data)
                        except Exception as fe:
                            logger.error(f"Failed to set future result: {fe}")
            else:
                logger.debug(
                    f"📨 Unmatched response session: {session_id} (pending: {list(self._pending_responses.keys())})"
                )

        except Exception as e:
            logger.error(f"❌ Error in sync response handler: {e}")

    def _extract_and_log_status_data(self, response_data: Dict[str, Any]):
        """Extract and log interesting status data from MQTT responses."""
        try:
            # Look for various data patterns we've seen in HAR files
            interesting_fields = [
                "dhwTemperature",
                "dhwTemperatureSetting",
                "dhwCharge",
                "operationMode",
                "heatPumpStatus",
                "elementStatus",
                "outsideTemperature",
                "errorCode",
                "subErrorCode",
                "channelStatus",
                "status",
            ]

            found_data = {}
            for field in interesting_fields:
                if field in response_data:
                    found_data[field] = response_data[field]

            if found_data:
                logger.info(f"📊 Status Data Found: {json.dumps(found_data, indent=2)}")

                # Specifically look for DHW charge (tank level)
                if "dhwCharge" in found_data:
                    logger.info(f"🔋 Tank Charge Level: {found_data['dhwCharge']}%")

                if "operationMode" in found_data:
                    logger.info(f"⚙️ Operation Mode: {found_data['operationMode']}")

        except Exception as e:
            logger.debug(f"Error extracting status data: {e}")

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

    def _parse_channel_status(
        self, channel_data: Dict[str, Any]
    ) -> Optional[DeviceStatus]:
        """
        Parse channel status from navien_nwp500_api format with enhanced DHW data.

        Args:
            channel_data: Channel status data

        Returns:
            DeviceStatus object or None if parsing fails
        """
        try:
            # Map navilink_api channel format to our DeviceStatus format
            # DHW charge percentage is in the channel data
            dhw_charge_percent = channel_data.get("dhwChargePercent", 0)

            # Operation mode mapping for heat pump water heater
            power_status = channel_data.get("powerStatus", False)
            heat_pump_status = channel_data.get("heatPumpStatus", False)
            resistance_status = channel_data.get("resistanceHeaterStatus", False)

            # Map operation mode based on active components
            if not power_status:
                operation_mode = 0  # Standby
            elif heat_pump_status and resistance_status:
                operation_mode = 3  # Heat Pump + Resistive Element
            elif resistance_status:
                operation_mode = 2  # Resistive Element Only
            elif heat_pump_status:
                operation_mode = 1  # Heat Pump Only
            else:
                operation_mode = 0  # Default to standby

            return DeviceStatus(
                command=0,  # Not in channel status
                outside_temperature=channel_data.get("outsideTemp", 0),
                special_function_status=0,
                did_reload=0,
                error_code=channel_data.get("errorCodePrimary", 0),
                sub_error_code=channel_data.get("errorCodeSecondary", 0),
                operation_mode=operation_mode,
                operation_busy=1 if channel_data.get("heating", False) else 0,
                freeze_protection_use=(
                    1 if channel_data.get("freezeProtection", False) else 0
                ),
                dhw_use=1 if channel_data.get("onDemandUseFlag") else 0,
                dhw_use_sustained=0,
                dhw_temperature=channel_data.get("avgOutletTemp", 0),
                dhw_temperature_setting=channel_data.get("DHWSettingTemp", 0),
                dhw_charge_per=dhw_charge_percent,  # Use correct field name from model
                program_reservation_use=0,
                smart_diagnostic=0,
                fault_status1=0,
                fault_status2=0,
                wifi_rssi=channel_data.get("wifiRssi", 0),
                eco_use=1 if channel_data.get("ecoMode", False) else 0,
                dhw_target_temperature_setting=channel_data.get("DHWSettingTemp", 0),
                heat_pump_status=1 if heat_pump_status else 0,
                resistance_heater_status=1 if resistance_status else 0,
                defrost_mode=1 if channel_data.get("defrostMode", False) else 0,
                # Set remaining fields to default values
                **{
                    field: 0
                    for field in DeviceStatus.__dataclass_fields__
                    if field
                    not in [
                        "command",
                        "outside_temperature",
                        "special_function_status",
                        "did_reload",
                        "error_code",
                        "sub_error_code",
                        "operation_mode",
                        "operation_busy",
                        "freeze_protection_use",
                        "dhw_use",
                        "dhw_use_sustained",
                        "dhw_temperature",
                        "dhw_temperature_setting",
                        "dhw_charge_per",
                        "program_reservation_use",
                        "smart_diagnostic",
                        "fault_status1",
                        "fault_status2",
                        "wifi_rssi",
                        "eco_use",
                        "dhw_target_temperature_setting",
                        "heat_pump_status",
                        "resistance_heater_status",
                        "defrost_mode",
                    ]
                },
            )
        except Exception as e:
            logger.error(f"Error parsing channel status: {e}")
            logger.debug(f"Channel data: {channel_data}")
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
            # Expecting status data directly (cleaned up debug messages)
            status_data = data.get(
                "status", data
            )  # Handle both nested and direct status

            # Create DeviceStatus with available fields and proper field mapping
            device_status = DeviceStatus(
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
                dhw_target_temperature_setting=status_data.get(
                    "dhwTargetTemperatureSetting", 0
                ),
                # Key fields we're interested in for monitoring
                dhw_charge_per=status_data.get(
                    "dhwChargePer", 0
                ),  # Tank charge percentage
                tank_upper_temperature=status_data.get("tankUpperTemperature", 0),
                tank_lower_temperature=status_data.get("tankLowerTemperature", 0),
                discharge_temperature=status_data.get("dischargeTemperature", 0),
                suction_temperature=status_data.get("suctionTemperature", 0),
                evaporator_temperature=status_data.get("evaporatorTemperature", 0),
                ambient_temperature=status_data.get("ambientTemperature", 0),
                target_super_heat=status_data.get("targetSuperHeat", 0),
                comp_use=status_data.get("compUse", 0),  # Heat pump compressor
                eev_use=status_data.get("eevUse", 0),
                eva_fan_use=status_data.get("evaFanUse", 0),
                current_inst_power=status_data.get("currentInstPower", 0),
                shut_off_valve_use=status_data.get("shutOffValveUse", 0),
                con_ovr_sensor_use=status_data.get("conOvrSensorUse", 0),
                wtr_ovr_sensor_use=status_data.get("wtrOvrSensorUse", 0),
                dr_event_status=status_data.get("drEventStatus", 0),
                vacation_day_setting=status_data.get("vacationDaySetting", 0),
                vacation_day_elapsed=status_data.get("vacationDayElapsed", 0),
                freeze_protection_temperature=status_data.get(
                    "freezeProtectionTemperature", 0
                ),
                anti_legionella_use=status_data.get("antiLegionellaUse", 0),
                anti_legionella_period=status_data.get("antiLegionellaPeriod", 0),
                anti_legionella_operation_busy=status_data.get(
                    "antiLegionellaOperationBusy", 0
                ),
                program_reservation_type=status_data.get("programReservationType", 0),
                dhw_operation_setting=status_data.get("dhwOperationSetting", 0),
                temperature_type=status_data.get("temperatureType", 0),
                temp_formula_type=status_data.get("tempFormulaType", 0),
                error_buzzer_use=status_data.get("errorBuzzerUse", 0),
                current_heat_use=status_data.get(
                    "currentHeatUse", 0
                ),  # Resistance heater
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
                heat_upper_use=status_data.get(
                    "heatUpperUse", 0
                ),  # Upper heating element
                heat_lower_use=status_data.get(
                    "heatLowerUse", 0
                ),  # Lower heating element
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
                hp_upper_on_diff_temp_setting=status_data.get(
                    "hpUpperOnDiffTempSetting", 0
                ),
                hp_upper_off_diff_temp_setting=status_data.get(
                    "hpUpperOffDiffTempSetting", 0
                ),
                hp_lower_on_diff_temp_setting=status_data.get(
                    "hpLowerOnDiffTempSetting", 0
                ),
                hp_lower_off_diff_temp_setting=status_data.get(
                    "hpLowerOffDiffTempSetting", 0
                ),
                he_upper_on_diff_temp_setting=status_data.get(
                    "heUpperOnDiffTempSetting", 0
                ),
                he_upper_off_diff_temp_setting=status_data.get(
                    "heUpperOffDiffTempSetting", 0
                ),
                he_lower_on_tdiffemp_setting=status_data.get(
                    "heLowerOnTDiffempSetting", 0
                ),
                he_lower_off_diff_temp_setting=status_data.get(
                    "heLowerOffDiffTempSetting", 0
                ),
                dr_override_status=status_data.get("drOverrideStatus", 0),
                tou_override_status=status_data.get("touOverrideStatus", 0),
                total_energy_capacity=status_data.get("totalEnergyCapacity", 0),
                available_energy_capacity=status_data.get("availableEnergyCapacity", 0),
                # Enhanced monitoring convenience fields
                heat_pump_status=status_data.get(
                    "compUse", 0
                ),  # Alias for heat pump status
                resistance_heater_status=max(
                    status_data.get("heatUpperUse", 0),
                    status_data.get("heatLowerUse", 0),
                ),  # Either element on
                defrost_mode=0,  # Would need to determine from other status fields
            )

            # Successfully created DeviceStatus object
            return device_status
        except Exception as e:
            logger.error(f"Error parsing device status: {e}")
            logger.debug(f"Status data: {status_data}")
            return None

    async def send_device_command(
        self,
        command: int,
        topic_suffix: str = "",
        response_topic_suffix: str = "",
        additional_data: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Send command to device and wait for response with enhanced error handling.

        Args:
            command: Command ID
            topic_suffix: Additional topic suffix (e.g., "/channelinfo")
            response_topic_suffix: Response topic suffix
            additional_data: Additional command parameters
            timeout: Response timeout in seconds

        Returns:
            Device response data
        """
        if self._connection_state != ConnectionState.CONNECTED:
            raise MQTTError(
                f"Not connected to MQTT (state: {self._connection_state.value})"
            )

        # Generate unique session ID for this request
        request_session_id = str(int(time.time() * 1000))

        # Build command message based on navilink_api analysis
        response_suffix = (
            response_topic_suffix or topic_suffix.split("/")[-1] if topic_suffix else ""
        )
        command_data = {
            "clientID": self._session_id,
            "protocolVersion": 2,  # From HAR file analysis
            "request": {
                "additionalValue": self._device.additional_value,
                "command": command,
                "deviceType": self._device.device_type,
                "macAddress": self._device.mac_address,
                **(additional_data or {}),
            },
            "requestTopic": f"{self._command_topic_base}/{topic_suffix}",
            "responseTopic": (
                f"{self._response_topic_base}/{response_suffix}"
                if response_suffix
                else self._response_topic_base
            ),
            "sessionID": request_session_id,
        }

        # Create JSON payload
        payload = json.dumps(command_data).encode("utf-8")

        # Create future for response
        response_future = asyncio.Future()
        self._pending_responses[request_session_id] = response_future

        # Publish via AWS IoT connection with retry
        topic = f"{self._command_topic_base}/{topic_suffix}"
        logger.info(f"📤 Sending command {command} to topic: {topic}")
        logger.debug(f"📤 Command payload: {json.dumps(command_data, indent=2)}")

        try:
            success = await self._publish_with_retry(topic, payload, qos=1)
            if not success:
                raise MQTTError(f"Failed to publish command {command}")

            self._statistics["messages_sent"] += 1
            logger.debug(f"📤 Command {command} published successfully")

            # Wait for response with timeout
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response

        except asyncio.TimeoutError:
            self._pending_responses.pop(request_session_id, None)
            raise MQTTError(f"Command timeout for command {command} after {timeout}s")
        except Exception as e:
            self._pending_responses.pop(request_session_id, None)
            raise MQTTError(f"Command {command} failed: {e}")

    async def _publish_with_retry(
        self, topic: str, payload: bytes, qos: int = 1, max_retries: int = 3
    ) -> bool:
        """Publish with retry logic."""
        for attempt in range(max_retries):
            try:
                success = await self._aws_connection.publish(topic, payload, qos=qos)
                if success:
                    return True

                if attempt < max_retries - 1:
                    logger.warning(
                        f"⚠️ Publish attempt {attempt + 1} failed, retrying..."
                    )
                    await asyncio.sleep(2**attempt)  # Exponential backoff

            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(
                    f"⚠️ Publish attempt {attempt + 1} error: {e}, retrying..."
                )
                await asyncio.sleep(2**attempt)

        return False

    async def get_channel_info(self) -> Dict[str, Any]:
        """
        Get channel information (device info).

        Returns:
            Channel info dictionary
        """
        # Based on navilink_api: status/start request -> channelinfo response
        response = await self.send_device_command(
            self.CMD_GET_DEVICE_INFO,
            "status/start",
            response_topic_suffix="channelinfo",
        )
        return response

    async def get_device_status(self) -> DeviceStatus:
        """
        Get current device status using the exact approach from HAR file.

        Returns:
            DeviceStatus object
        """
        # Use the same command and topic structure as seen in HAR file
        response = await self.send_device_command(
            self.CMD_GET_STATUS,
            "st",  # Status topic from HAR file: cmd/52/navilink-04786332fca0/st
            response_topic_suffix="",  # Response goes to main res topic
        )

        # Parse status from response based on HAR file structure (fixed path)
        # The response structure is: response -> response -> status
        if "response" in response and "status" in response["response"]:
            status = self._parse_device_status(response["response"]["status"])
        elif "response" in response:
            status = self._parse_device_status(response["response"])
        elif "status" in response:
            # Legacy/fallback path
            status = self._parse_device_status(response["status"])
        else:
            # Direct response path
            status = self._parse_device_status(response)

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
                days_of_week=rsv_data.get("daysOfWeek"),
            )
            reservations.append(reservation)

        return reservations

    async def get_energy_usage(
        self, period: str = "daily", days: int = 7
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

    async def start_monitoring(self, polling_interval: int = 15):
        """
        Start real-time monitoring loop with enhanced resilience.

        Args:
            polling_interval: Seconds between status requests (default 15)
        """
        if self._monitoring:
            logger.warning("⚠️ Monitoring already started")
            return

        if self._connection_state != ConnectionState.CONNECTED:
            logger.error("❌ Cannot start monitoring - not connected")
            return

        self._monitoring = True
        self._polling_interval = polling_interval

        # Get initial channel info like navilink_api does
        try:
            await self.get_channel_info()
            logger.info("✅ Got initial channel info")
        except Exception as e:
            logger.warning(f"⚠️ Failed to get initial channel info: {e}")

        # Start periodic polling task
        self._polling_task = asyncio.create_task(self._polling_loop())
        logger.info(f"🔄 Started monitoring with {polling_interval}s polling interval")

    async def _polling_loop(self):
        """Enhanced periodic polling loop with error recovery."""
        error_count = 0
        max_errors = 10

        while self._monitoring and self._connection_state == ConnectionState.CONNECTED:
            try:
                # Send status request like navilink_api does
                await self._poll_device_status()
                error_count = 0  # Reset error count on success

                # Wait for polling interval
                await asyncio.sleep(self._polling_interval)

            except asyncio.CancelledError:
                logger.info("🛑 Polling loop cancelled")
                break
            except Exception as e:
                error_count += 1
                logger.error(f"❌ Error in polling loop (#{error_count}): {e}")

                if error_count >= max_errors:
                    logger.error(
                        f"❌ Max polling errors ({max_errors}) reached, stopping monitoring"
                    )
                    break

                # Exponential backoff for errors
                error_delay = min(5 * (2 ** min(error_count, 5)), 60)  # Max 60s delay
                await asyncio.sleep(error_delay)

    async def _poll_device_status(self):
        """Send status request with fire-and-forget approach for continuous monitoring."""
        try:
            # Build status request like navilink_api but don't wait for response
            additional_data = {
                "status": {"channelNumber": 1, "unitNumberEnd": 1, "unitNumberStart": 1}
            }

            # Generate session ID
            request_session_id = str(int(time.time() * 1000))

            command_data = {
                "clientID": self._session_id,
                "sessionID": request_session_id,
                "deviceID": self._device.controller_id
                or self._device.mac_address,  # Use controller_id or MAC as fallback
                "command": self.CMD_GET_STATUS,
                **additional_data,
            }

            # Send fire-and-forget command for periodic polling
            topic = f"{self._command_topic_base}/status/channelstatus"
            payload = json.dumps(command_data).encode("utf-8")

            success = await self._aws_connection.publish(
                topic, payload, qos=0
            )  # QoS 0 for fire-and-forget

            if success:
                logger.debug(f"📤 Polling command sent: {self.CMD_GET_STATUS}")
                self._statistics["messages_sent"] += 1
            else:
                logger.warning(f"⚠️ Failed to send polling command")

        except Exception as e:
            logger.error(f"❌ Failed to poll device status: {e}")
            raise

    async def stop_monitoring(self):
        """Stop real-time monitoring with cleanup."""
        logger.info("🛑 Stopping monitoring...")
        self._monitoring = False

        if self._polling_task:
            self._polling_task.cancel()
            try:
                await asyncio.wait_for(self._polling_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("⚠️ Polling task did not stop gracefully")
            except asyncio.CancelledError:
                pass
            finally:
                self._polling_task = None

        logger.info("🛑 Monitoring stopped")

    def set_status_callback(self, callback: Callable[[DeviceStatus], None]):
        """
        Set callback for status updates.

        Args:
            callback: Function to call on status updates (can be async)
        """
        self._status_callback = callback

    @property
    def is_connected(self) -> bool:
        """Check if MQTT is connected."""
        return (
            self._connection_state == ConnectionState.CONNECTED
            and self._aws_connection
            and self._aws_connection.is_connected
        )

    @property
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._monitoring and self._polling_task and not self._polling_task.done()
