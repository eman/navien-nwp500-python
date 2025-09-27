"""
AWS IoT WebSocket connection helper using the AWS IoT SDK v2 with MQTT5.
"""

import asyncio
import json
import logging
import ssl
import uuid
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass

try:
    # Try MQTT5 first, fall back to MQTT3 if not available
    try:
        from awsiot import mqtt5_client_builder
        from awscrt.mqtt5 import Client as Mqtt5Client, QoS, PublishPacket, SubscribePacket
        MQTT5_AVAILABLE = True
    except ImportError:
        MQTT5_AVAILABLE = False
        
    # Always import MQTT3 as fallback
    from awsiot import mqtt_connection_builder
    from awscrt import io, mqtt, auth, http
    from awscrt.io import LogLevel
    from awscrt.mqtt import QoS as Mqtt3QoS
    
except ImportError:
    raise ImportError("AWS IoT SDK not available. Install with: pip install awsiotsdk>=1.21.0")

logger = logging.getLogger(__name__)

@dataclass
class ConnectionState:
    """Track connection state and events."""
    connected: bool = False
    connect_future: Optional[asyncio.Future] = None
    disconnect_future: Optional[asyncio.Future] = None
    stopped_future: Optional[asyncio.Future] = None

class AWSIoTWebSocketConnection:
    """Enhanced AWS IoT WebSocket connection with fallback to MQTT3 if MQTT5 unavailable."""
    
    def __init__(
        self,
        endpoint: str,
        access_key_id: str,
        secret_access_key: str,
        session_token: str,
        client_id: str,
        region: str = "us-east-1"
    ):
        """
        Initialize AWS IoT WebSocket connection.
        
        Args:
            endpoint: AWS IoT endpoint (without wss:// prefix)
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key  
            session_token: AWS session token
            client_id: MQTT client ID
            region: AWS region
        """
        self.endpoint = endpoint
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.session_token = session_token
        self.client_id = client_id
        self.region = region
        
        # Use MQTT3 by default until MQTT5 is fully stable
        # Set use_mqtt5 = True to enable MQTT5 (experimental)
        self.use_mqtt5 = False  # Disabled by default for stability
        logger.info(f"Using {'MQTT5 (experimental)' if self.use_mqtt5 else 'MQTT3 (stable)'} client")
        
        self.client = None
        self.connection = None  # For MQTT3 compatibility
        self.state = ConnectionState()
        self.message_callback: Optional[Callable] = None
        
        # Store subscription and publish futures for tracking
        self.subscription_futures = {}
        self.publish_futures = {}
        
        # Set up event loop group - reuse for efficiency
        self.event_loop_group = io.EventLoopGroup(1)
        self.host_resolver = io.DefaultHostResolver(self.event_loop_group)
        self.client_bootstrap = io.ClientBootstrap(self.event_loop_group, self.host_resolver)

    async def connect(self) -> bool:
        """
        Connect to AWS IoT using WebSocket with MQTT5 or MQTT3 fallback.
        
        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to AWS IoT endpoint: {self.endpoint}")
            
            # Create credentials provider
            credentials_provider = auth.AwsCredentialsProvider.new_static(
                access_key_id=self.access_key_id,
                secret_access_key=self.secret_access_key,
                session_token=self.session_token
            )
            
            if self.use_mqtt5 and MQTT5_AVAILABLE:
                return await self._connect_mqtt5(credentials_provider)
            else:
                return await self._connect_mqtt3(credentials_provider)
                
        except Exception as e:
            logger.error(f"Failed to connect to AWS IoT: {e}")
            self.state.connected = False
            raise

    async def _connect_mqtt5(self, credentials_provider):
        """Connect using MQTT5 client with full features."""
        try:
            logger.info("🚀 Establishing MQTT5 connection...")
            
            # Set up connection future
            self.state.connect_future = asyncio.Future()
            
            # Build MQTT5 client with WebSocket connection
            self.client = mqtt5_client_builder.websockets_with_default_aws_signing(
                endpoint=self.endpoint,
                client_bootstrap=self.client_bootstrap,
                region=self.region,
                credentials_provider=credentials_provider,
                client_id=self.client_id,
                clean_start=True,  # MQTT5 uses clean_start instead of clean_session
                session_expiry_interval_sec=0,  # No session persistence
                keep_alive_interval_sec=300,  # 5 minutes
                ping_timeout_ms=10000,  # 10 seconds
                connack_timeout_ms=60000,  # 60 seconds for connection ack
                ack_timeout_ms=30000  # 30 seconds for publish ack
            )
            
            # Set up MQTT5 lifecycle callbacks
            def on_connection_success(connack_packet):
                logger.info("✅ MQTT5 connection successful")
                self.state.connected = True
                if not self.state.connect_future.done():
                    self.state.connect_future.set_result(True)
            
            def on_connection_failure(connack_packet):
                reason = getattr(connack_packet, 'reason_code', 'Unknown')
                logger.error(f"❌ MQTT5 connection failed: {reason}")
                self.state.connected = False
                if not self.state.connect_future.done():
                    self.state.connect_future.set_exception(Exception(f"MQTT5 connection failed: {reason}"))
            
            def on_disconnection(disconnect_packet):
                reason = getattr(disconnect_packet, 'reason_code', 'Unknown')
                logger.warning(f"🔌 MQTT5 disconnected: {reason}")
                self.state.connected = False
            
            def on_stopped(stop_data):
                logger.info("🛑 MQTT5 client stopped")
                self.state.connected = False
                if self.state.stopped_future and not self.state.stopped_future.done():
                    self.state.stopped_future.set_result(True)
            
            def on_message_received(publish_packet):
                """Handle incoming MQTT5 messages."""
                try:
                    topic = publish_packet.topic
                    payload = publish_packet.payload
                    
                    if self.message_callback:
                        self.message_callback(topic, payload)
                    
                    logger.debug(f"📨 Received MQTT5 message on {topic}: {len(payload)} bytes")
                    
                except Exception as e:
                    logger.error(f"Error processing MQTT5 message: {e}")
            
            # Configure lifecycle callbacks
            self.client.on_connection_success = on_connection_success
            self.client.on_connection_failure = on_connection_failure
            self.client.on_disconnection = on_disconnection
            self.client.on_stopped = on_stopped
            self.client.on_publish_received = on_message_received
            
            # Start the client
            logger.info("🔌 Starting MQTT5 client...")
            self.client.start()
            
            # Wait for connection with timeout
            try:
                await asyncio.wait_for(self.state.connect_future, timeout=60.0)
                logger.info("🎉 MQTT5 connection established successfully!")
                return True
                
            except asyncio.TimeoutError:
                logger.error("❌ MQTT5 connection timeout")
                self.state.connected = False
                raise Exception("MQTT5 connection timeout")
                
        except Exception as e:
            logger.warning(f"❌ MQTT5 connection failed: {e}, falling back to MQTT3")
            # Fall back to MQTT3 on any MQTT5 failure
            self.use_mqtt5 = False
            return await self._connect_mqtt3(credentials_provider)
    
    async def _connect_mqtt3(self, credentials_provider):
        """Connect using MQTT3 client with enhanced features."""
        # Set up connection future
        self.state.connect_future = asyncio.Future()
        
        # Build the WebSocket connection with enhanced settings
        self.connection = mqtt_connection_builder.websockets_with_default_aws_signing(
            endpoint=self.endpoint,
            client_bootstrap=self.client_bootstrap,
            region=self.region,
            credentials_provider=credentials_provider,
            client_id=self.client_id,
            clean_session=True,
            keep_alive_secs=300,  # 5 minutes
            ping_timeout_ms=10000  # 10 seconds
        )
        
        # Set up enhanced connection callbacks
        def on_connection_interrupted(connection, error, **kwargs):
            logger.warning(f"Connection interrupted: {error}")
            self.state.connected = False
            
        def on_connection_resumed(connection, return_code, session_present, **kwargs):
            logger.info("Connection resumed")
            self.state.connected = True
            
        def on_connect(connection, return_code, session_present, **kwargs):
            if return_code == mqtt.ConnectReturnCode.ACCEPTED:
                logger.info("✅ Successfully connected to AWS IoT with enhanced MQTT3")
                self.state.connected = True
                if not self.state.connect_future.done():
                    self.state.connect_future.set_result(True)
            else:
                logger.error(f"❌ Failed to connect: {return_code}")
                self.state.connected = False
                if not self.state.connect_future.done():
                    self.state.connect_future.set_exception(Exception(f"Connect failed: {return_code}"))
                    
        # Set callbacks
        self.connection.on_connection_interrupted = on_connection_interrupted
        self.connection.on_connection_resumed = on_connection_resumed
        
        # Connect
        connect_future = self.connection.connect()
        
        # Convert to asyncio future
        def done_callback(future):
            try:
                result = future.result()
                on_connect(self.connection, mqtt.ConnectReturnCode.ACCEPTED, False)
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                if not self.state.connect_future.done():
                    self.state.connect_future.set_exception(e)
                    
        connect_future.add_done_callback(done_callback)
        
        # Wait for connection
        await asyncio.wait_for(self.state.connect_future, timeout=60.0)
        return True

    async def disconnect(self):
        """Disconnect from AWS IoT."""
        if self.use_mqtt5 and self.client:
            await self._disconnect_mqtt5()
        elif self.connection and self.state.connected:
            await self._disconnect_mqtt3()
            
        self.state.connected = False
        self.connection = None
        self.client = None
    
    async def _disconnect_mqtt5(self):
        """Disconnect using MQTT5 client."""
        if self.client and self.state.connected:
            logger.info("🔌 Disconnecting from AWS IoT (MQTT5)...")
            
            self.state.stopped_future = asyncio.Future()
            
            try:
                # Stop the MQTT5 client
                stop_task = self.client.stop()
                
                # Wait for graceful shutdown
                await asyncio.wait_for(self.state.stopped_future, timeout=10.0)
                logger.info("✅ MQTT5 client stopped gracefully")
                
            except asyncio.TimeoutError:
                logger.warning("⚠️ MQTT5 disconnect timeout")
            except Exception as e:
                logger.error(f"❌ MQTT5 disconnect error: {e}")
    
    async def _disconnect_mqtt3(self):
        """Disconnect using MQTT3 client."""
        logger.info("🔌 Disconnecting from AWS IoT (MQTT3)...")
        
        self.state.disconnect_future = asyncio.Future()
        
        def on_disconnect(connection, **kwargs):
            logger.info("✅ MQTT3 disconnected from AWS IoT")
            self.state.connected = False
            if not self.state.disconnect_future.done():
                self.state.disconnect_future.set_result(True)
                
        disconnect_future = self.connection.disconnect()
        
        def done_callback(future):
            try:
                future.result()
                on_disconnect(self.connection)
            except Exception as e:
                logger.error(f"Disconnect error: {e}")
                if not self.state.disconnect_future.done():
                    self.state.disconnect_future.set_exception(e)
                    
        disconnect_future.add_done_callback(done_callback)
        
        try:
            await asyncio.wait_for(self.state.disconnect_future, timeout=10.0)
        except asyncio.TimeoutError:
            logger.warning("⚠️ MQTT3 disconnect timeout")
                
    async def subscribe(self, topic: str, qos: int = 1, callback: Optional[Callable] = None) -> bool:
        """
        Subscribe to a topic using MQTT5 or MQTT3 with enhanced error handling.
        
        Args:
            topic: MQTT topic to subscribe to
            qos: Quality of Service level (0, 1, or 2)
            callback: Optional per-topic message callback function
            
        Returns:
            True if subscription successful
        """
        if not self.is_connected:
            raise Exception("Not connected to AWS IoT")
            
        logger.debug(f"Subscribing to topic: {topic}")
        
        if self.use_mqtt5 and self.client:
            return await self._subscribe_mqtt5(topic, qos, callback)
        else:
            return await self._subscribe_mqtt3(topic, qos, callback)
    
    async def _subscribe_mqtt5(self, topic: str, qos: int = 1, callback: Optional[Callable] = None) -> bool:
        """Subscribe using MQTT5 client."""
        subscribe_future = asyncio.Future()
        
        # Set up per-topic callback if provided
        if callback:
            # Store callback for this topic
            self.subscription_futures[topic] = callback
        
        def on_suback(suback_packet):
            logger.debug(f"✅ MQTT5 subscribed to {topic}")
            if not subscribe_future.done():
                subscribe_future.set_result(True)
        
        def on_subfail(suback_packet):
            reason = getattr(suback_packet, 'reason_codes', ['Unknown'])[0]
            logger.error(f"❌ MQTT5 subscription failed: {reason}")
            if not subscribe_future.done():
                subscribe_future.set_exception(Exception(f"Subscription failed: {reason}"))
        
        try:
            # Convert QoS to MQTT5 enum
            mqtt5_qos = QoS.AT_LEAST_ONCE if qos == 1 else QoS.AT_MOST_ONCE
            
            # Create subscription packet
            subscribe_packet = SubscribePacket(
                topic_filters=[(topic, mqtt5_qos)]
            )
            
            # Subscribe with MQTT5
            subscribe_task = self.client.subscribe(
                subscribe_packet=subscribe_packet,
                on_suback=on_suback
            )
            
            # Wait for subscription to complete
            await asyncio.wait_for(subscribe_future, timeout=10.0)
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ MQTT5 subscription to {topic} timed out")
            return False
        except Exception as e:
            logger.error(f"❌ MQTT5 subscription to {topic} failed: {e}")
            return False
    
    async def _subscribe_mqtt3(self, topic: str, qos: int = 1, callback: Optional[Callable] = None) -> bool:
        """Subscribe using MQTT3 client."""
        # Set up subscription future
        subscribe_future = asyncio.Future()
        
        def on_message(topic, payload, dup, qos, retain, **kwargs):
            try:
                if callback:
                    callback(topic, payload)
                elif self.message_callback:
                    self.message_callback(topic, payload)
            except Exception as e:
                logger.error(f"Error in message callback: {e}")
        
        def on_suback(topic, qos, **kwargs):
            logger.debug(f"✅ MQTT3 subscribed to {topic} with QoS {qos}")
            if not subscribe_future.done():
                subscribe_future.set_result(True)
                
        # Subscribe using MQTT3
        qos_level = Mqtt3QoS.AT_LEAST_ONCE if qos == 1 else Mqtt3QoS.AT_MOST_ONCE
        sub_future, packet_id = self.connection.subscribe(
            topic=topic,
            qos=qos_level,
            callback=on_message
        )
        
        def done_callback(future):
            try:
                future.result()
                on_suback(topic, qos)
            except Exception as e:
                logger.error(f"Subscription failed: {e}")
                if not subscribe_future.done():
                    subscribe_future.set_exception(e)
                    
        sub_future.add_done_callback(done_callback)
        
        try:
            await asyncio.wait_for(subscribe_future, timeout=10.0)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ MQTT3 subscription to {topic} timed out")
            return False
        except Exception as e:
            logger.error(f"❌ MQTT3 subscription to {topic} failed: {e}")
            return False
    
    async def publish(self, topic: str, payload: bytes, qos: int = 1) -> bool:
        """
        Publish a message to a topic using MQTT5 or MQTT3 with enhanced error handling.
        
        Args:
            topic: MQTT topic
            payload: Message payload
            qos: Quality of Service level (0, 1, or 2)
            
        Returns:
            True if publish successful
        """
        if not self.is_connected:
            raise Exception("Not connected to AWS IoT")
            
        logger.debug(f"Publishing to topic: {topic} (payload size: {len(payload)} bytes)")
        
        if self.use_mqtt5 and self.client:
            return await self._publish_mqtt5(topic, payload, qos)
        else:
            return await self._publish_mqtt3(topic, payload, qos)
    
    async def _publish_mqtt5(self, topic: str, payload: bytes, qos: int = 1) -> bool:
        """Publish using MQTT5 client."""
        # For QoS 0, we don't wait for acknowledgment
        if qos == 0:
            try:
                publish_packet = PublishPacket(
                    topic=topic,
                    payload=payload,
                    qos=QoS.AT_MOST_ONCE
                )
                self.client.publish(publish_packet)
                return True
            except Exception as e:
                logger.error(f"Failed to publish to {topic}: {e}")
                return False
        
        # For QoS 1+, set up publish future and wait for completion
        publish_future = asyncio.Future()
        
        def on_puback(puback_packet):
            logger.debug(f"✅ MQTT5 publish acknowledged for {topic}")
            if not publish_future.done():
                publish_future.set_result(True)
        
        def on_pubfail(puback_packet):
            reason = getattr(puback_packet, 'reason_code', 'Unknown')
            logger.error(f"❌ MQTT5 publish failed: {reason}")
            if not publish_future.done():
                publish_future.set_exception(Exception(f"Publish failed: {reason}"))
        
        try:
            # Convert QoS to MQTT5 enum
            mqtt5_qos = QoS.AT_LEAST_ONCE if qos == 1 else QoS.AT_MOST_ONCE
            
            # Create publish packet
            publish_packet = PublishPacket(
                topic=topic,
                payload=payload,
                qos=mqtt5_qos
            )
            
            # Publish with MQTT5
            publish_task = self.client.publish(
                publish_packet=publish_packet,
                on_puback=on_puback
            )
            
            # Wait for publish acknowledgment
            await asyncio.wait_for(publish_future, timeout=10.0)
            return True
            
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ MQTT5 publish to {topic} timed out")
            return False
        except Exception as e:
            logger.error(f"❌ MQTT5 publish to {topic} failed: {e}")
            return False
    
    async def _publish_mqtt3(self, topic: str, payload: bytes, qos: int = 1) -> bool:
        """Publish using MQTT3 client."""
        # For QoS 0, we don't wait for acknowledgment
        if qos == 0:
            try:
                qos_level = Mqtt3QoS.AT_MOST_ONCE
                pub_future, packet_id = self.connection.publish(
                    topic=topic,
                    payload=payload,
                    qos=qos_level
                )
                return True
            except Exception as e:
                logger.error(f"Failed to publish to {topic}: {e}")
                return False
        
        # For QoS 1+, set up publish future and wait for completion
        publish_future = asyncio.Future()
        
        def on_puback(**kwargs):
            if not publish_future.done():
                publish_future.set_result(True)
                
        # Publish using MQTT3
        qos_level = Mqtt3QoS.AT_LEAST_ONCE if qos == 1 else Mqtt3QoS.AT_MOST_ONCE
        pub_future, packet_id = self.connection.publish(
            topic=topic,
            payload=payload,
            qos=qos_level
        )
        
        def done_callback(future):
            try:
                future.result()
                on_puback()
            except Exception as e:
                logger.error(f"Publish failed: {e}")
                if not publish_future.done():
                    publish_future.set_exception(e)
                    
        pub_future.add_done_callback(done_callback)
        
        try:
            await asyncio.wait_for(publish_future, timeout=10.0)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ MQTT3 publish to {topic} timed out")
            return False
        except Exception as e:
            logger.error(f"❌ MQTT3 publish to {topic} failed: {e}")
            return False
    
    def set_message_callback(self, callback: Callable):
        """
        Set a global message callback.
        
        Args:
            callback: Function to call for all received messages
        """
        self.message_callback = callback

    async def send_control_command(self, control_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send control command to device.
        
        Args:
            control_data: Control command parameters including command, mode, param
            
        Returns:
            Command response from device
            
        Raises:
            Exception: If control command fails
        """
        if not self.is_connected:
            raise Exception("Not connected to MQTT")
            
        logger.info(f"📤 Sending control command: {control_data['command']}")
        
        # Generate unique session ID
        session_id = str(int(asyncio.get_event_loop().time() * 1000))
        client_id = f"{uuid.uuid4()}"
        
        # Build control message structure based on HAR analysis
        control_message = {
            "clientID": client_id,
            "protocolVersion": 2,
            "request": {
                "additionalValue": self.device.additional_value,
                "command": control_data["command"],
                "deviceType": self.device.device_type,
                "macAddress": self.device.mac_address,
                "mode": control_data["mode"],
                "param": control_data["param"],
                "paramStr": control_data.get("paramStr", "")
            },
            "requestTopic": f"cmd/{self.device.device_type}/navilink-{self.device.mac_address}/ctrl",
            "responseTopic": f"cmd/{self.device.device_type}/{self.device.home_seq}/{self.device._client.user_id}/{client_id}/res",
            "sessionID": session_id
        }
        
        # Convert to binary message (similar to status commands)
        json_payload = json.dumps(control_message).encode('utf-8')
        
        # Control topic
        control_topic = f"cmd/{self.device.device_type}/navilink-{self.device.mac_address}/ctrl"
        
        # Subscribe to response topic first
        response_topic = control_message["responseTopic"]
        response_future = asyncio.Future()
        
        def control_response_callback(topic, payload, dup, qos, retain, **kwargs):
            try:
                response_data = json.loads(payload.decode('utf-8'))
                if not response_future.done():
                    response_future.set_result(response_data)
            except Exception as e:
                if not response_future.done():
                    response_future.set_exception(e)
        
        # Subscribe to response
        await self._subscribe(response_topic, control_response_callback, qos=1)
        
        try:
            # Send control command
            success = await self._publish(control_topic, json_payload, qos=0)
            
            if not success:
                raise Exception("Failed to publish control command")
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(response_future, timeout=30.0)
                logger.info(f"✅ Control command response received")
                return response
                
            except asyncio.TimeoutError:
                logger.warning("⚠️ Control command response timeout")
                return {"success": True, "message": "Command sent, no response received"}
                
        finally:
            # Unsubscribe from response topic
            try:
                await self._unsubscribe(response_topic)
            except:
                pass
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to AWS IoT."""
        return self.state.connected and (self.connection is not None or self.client is not None)