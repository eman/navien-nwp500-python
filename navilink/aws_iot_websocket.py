"""
AWS IoT WebSocket connection helper using the AWS IoT SDK.
"""

import asyncio
import json
import logging
import ssl
from typing import Callable, Optional

try:
    from awsiot import mqtt_connection_builder
    from awscrt import io, mqtt, auth, http
    from awscrt.io import LogLevel
    from awscrt.mqtt import QoS  # Import QoS enum
except ImportError:
    raise ImportError("AWS IoT SDK not available. Install with: pip install awsiotsdk")

logger = logging.getLogger(__name__)

class AWSIoTWebSocketConnection:
    """Wrapper for AWS IoT WebSocket connection using the official SDK."""
    
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
        
        self.connection: Optional[mqtt.Connection] = None
        self.connected = False
        self.message_callback: Optional[Callable] = None
        
        # Connection events
        self.connect_future = None
        self.disconnect_future = None
        
    async def connect(self) -> bool:
        """
        Connect to AWS IoT using WebSocket.
        
        Returns:
            True if connection successful
        """
        try:
            # Set up the event loop group and host resolver
            event_loop_group = io.EventLoopGroup(1)
            host_resolver = io.DefaultHostResolver(event_loop_group)
            client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
            
            # Create credentials provider
            credentials_provider = auth.AwsCredentialsProvider.new_static(
                access_key_id=self.access_key_id,
                secret_access_key=self.secret_access_key,
                session_token=self.session_token
            )
            
            # Build the WebSocket connection
            self.connection = mqtt_connection_builder.websockets_with_default_aws_signing(
                endpoint=self.endpoint,
                client_bootstrap=client_bootstrap,
                region=self.region,
                credentials_provider=credentials_provider,
                client_id=self.client_id,
                clean_session=True,
                keep_alive_secs=300
            )
            
            logger.info(f"Connecting to AWS IoT endpoint: {self.endpoint}")
            
            # Set up connection callbacks
            self.connect_future = asyncio.Future()
            
            def on_connection_interrupted(connection, error, **kwargs):
                logger.warning(f"Connection interrupted: {error}")
                self.connected = False
                
            def on_connection_resumed(connection, return_code, session_present, **kwargs):
                logger.info("Connection resumed")
                self.connected = True
                
            def on_connect(connection, return_code, session_present, **kwargs):
                if return_code == mqtt.ConnectReturnCode.ACCEPTED:
                    logger.info("Connected to AWS IoT successfully")
                    self.connected = True
                    if not self.connect_future.done():
                        self.connect_future.set_result(True)
                else:
                    logger.error(f"Failed to connect: {return_code}")
                    self.connected = False
                    if not self.connect_future.done():
                        self.connect_future.set_exception(Exception(f"Connect failed: {return_code}"))
                        
            # Set callbacks
            self.connection.on_connection_interrupted = on_connection_interrupted
            self.connection.on_connection_resumed = on_connection_resumed
            
            # Connect
            connect_future = self.connection.connect()
            
            # Convert to asyncio future
            loop = asyncio.get_event_loop()
            
            def done_callback(future):
                try:
                    result = future.result()
                    on_connect(self.connection, mqtt.ConnectReturnCode.ACCEPTED, False)
                except Exception as e:
                    logger.error(f"Connection failed: {e}")
                    if not self.connect_future.done():
                        self.connect_future.set_exception(e)
                        
            connect_future.add_done_callback(done_callback)
            
            # Wait for connection
            await asyncio.wait_for(self.connect_future, timeout=30.0)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to AWS IoT: {e}")
            self.connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from AWS IoT."""
        if self.connection and self.connected:
            logger.info("Disconnecting from AWS IoT")
            
            self.disconnect_future = asyncio.Future()
            
            def on_disconnect(connection, **kwargs):
                logger.info("Disconnected from AWS IoT")
                self.connected = False
                if not self.disconnect_future.done():
                    self.disconnect_future.set_result(True)
                    
            disconnect_future = self.connection.disconnect()
            
            def done_callback(future):
                try:
                    future.result()
                    on_disconnect(self.connection)
                except Exception as e:
                    logger.error(f"Disconnect error: {e}")
                    if not self.disconnect_future.done():
                        self.disconnect_future.set_exception(e)
                        
            disconnect_future.add_done_callback(done_callback)
            
            try:
                await asyncio.wait_for(self.disconnect_future, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Disconnect timeout")
                
    async def subscribe(self, topic: str, qos: int = 1, callback: Optional[Callable] = None) -> bool:
        """
        Subscribe to a topic.
        
        Args:
            topic: MQTT topic to subscribe to
            qos: Quality of Service level
            callback: Message callback function
            
        Returns:
            True if subscription successful
        """
        if not self.connection or not self.connected:
            raise Exception("Not connected to AWS IoT")
            
        logger.debug(f"Subscribing to topic: {topic}")
        
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
            logger.debug(f"Subscribed to {topic} with QoS {qos}")
            if not subscribe_future.done():
                subscribe_future.set_result(True)
                
        # Subscribe
        qos_level = QoS.AT_LEAST_ONCE if qos == 1 else QoS.AT_MOST_ONCE
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
            await asyncio.wait_for(subscribe_future, timeout=5.0)  # Reduced timeout
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Subscription to {topic} timed out")
            return False
    
    async def publish(self, topic: str, payload: bytes, qos: int = 1) -> bool:
        """
        Publish a message to a topic.
        
        Args:
            topic: MQTT topic
            payload: Message payload
            qos: Quality of Service level
            
        Returns:
            True if publish successful
        """
        if not self.connection or not self.connected:
            raise Exception("Not connected to AWS IoT")
            
        logger.debug(f"Publishing to topic: {topic}")
        
        publish_future = asyncio.Future()
        
        def on_puback(**kwargs):
            if not publish_future.done():
                publish_future.set_result(True)
                
        # Publish
        qos_level = QoS.AT_LEAST_ONCE if qos == 1 else QoS.AT_MOST_ONCE
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
            await asyncio.wait_for(publish_future, timeout=5.0)  # Reduced timeout
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Publish to {topic} timed out")
            return False
    
    def set_message_callback(self, callback: Callable):
        """Set a global message callback."""
        self.message_callback = callback
    
    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self.connected