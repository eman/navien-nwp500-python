"""
Main client class for AWS IoT MQTT WebSocket communication.
"""

import asyncio
import json
import logging
from typing import Callable, Optional, Dict, Any
from concurrent.futures import Future

from awsiot import mqtt_connection_builder
from awscrt import mqtt, io
import boto3

from .exceptions import NavilinkError, AuthenticationError, ConnectionError


logger = logging.getLogger(__name__)


class NavilinkClient:
    """
    AWS IoT MQTT WebSocket client for asynchronous message handling.
    
    This client provides methods to authenticate with AWS IoT using credentials
    and receive MQTT messages asynchronously over WebSocket connections.
    """
    
    def __init__(
        self,
        endpoint: str,
        region: str = "us-east-1",
        client_id: Optional[str] = None,
    ):
        """
        Initialize the Navilink client.
        
        Args:
            endpoint: AWS IoT Core endpoint URL
            region: AWS region (default: us-east-1)
            client_id: MQTT client ID (auto-generated if not provided)
        """
        self.endpoint = endpoint
        self.region = region
        self.client_id = client_id or f"navilink-{id(self)}"
        
        self._connection: Optional[mqtt.Connection] = None
        self._event_loop_group: Optional[io.EventLoopGroup] = None
        self._host_resolver: Optional[io.DefaultHostResolver] = None
        self._client_bootstrap: Optional[io.ClientBootstrap] = None
        self._is_connected = False
        self._message_handlers: Dict[str, Callable] = {}
        
        logger.info(f"NavilinkClient initialized with endpoint: {endpoint}")
    
    async def connect_with_credentials(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_session_token: Optional[str] = None,
    ) -> None:
        """
        Connect to AWS IoT using AWS credentials over WebSocket.
        
        Args:
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key  
            aws_session_token: AWS session token (optional, for temporary credentials)
            
        Raises:
            AuthenticationError: If authentication fails
            ConnectionError: If connection fails
        """
        try:
            logger.info("Connecting to AWS IoT with credentials...")
            
            # Create event loop group and client bootstrap
            self._event_loop_group = io.EventLoopGroup(1)
            self._host_resolver = io.DefaultHostResolver(self._event_loop_group)
            self._client_bootstrap = io.ClientBootstrap(
                self._event_loop_group, self._host_resolver
            )
            
            # Create WebSocket connection using credentials
            self._connection = mqtt_connection_builder.websockets_with_default_aws_signing(
                endpoint=self.endpoint,
                client_bootstrap=self._client_bootstrap,
                region=self.region,
                credentials_provider=self._create_credentials_provider(
                    aws_access_key_id, aws_secret_access_key, aws_session_token
                ),
                client_id=self.client_id,
                clean_session=False,
                keep_alive_secs=30,
            )
            
            # Set up connection callbacks
            self._connection.on_connection_interrupted = self._on_connection_interrupted
            self._connection.on_connection_resumed = self._on_connection_resumed
            
            # Connect
            connect_future = self._connection.connect()
            await self._wait_for_future(connect_future)
            
            self._is_connected = True
            logger.info("Successfully connected to AWS IoT")
            
        except Exception as e:
            logger.error(f"Failed to connect to AWS IoT: {e}")
            if "authentication" in str(e).lower() or "credentials" in str(e).lower():
                raise AuthenticationError(f"Authentication failed: {e}")
            else:
                raise ConnectionError(f"Connection failed: {e}")
    
    def _create_credentials_provider(
        self,
        access_key_id: str,
        secret_access_key: str,
        session_token: Optional[str] = None,
    ):
        """Create AWS credentials provider."""
        from awscrt.auth import AwsCredentials, AwsCredentialsProvider
        
        credentials = AwsCredentials(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=session_token,
        )
        
        return AwsCredentialsProvider.new_static(credentials)
    
    async def subscribe(
        self,
        topic: str,
        qos: mqtt.QoS = mqtt.QoS.AT_LEAST_ONCE,
        callback: Optional[Callable[[str, bytes], None]] = None,
    ) -> None:
        """
        Subscribe to an MQTT topic.
        
        Args:
            topic: MQTT topic to subscribe to
            qos: Quality of Service level
            callback: Optional callback function for message handling
            
        Raises:
            ConnectionError: If not connected to AWS IoT
            NavilinkError: If subscription fails
        """
        if not self._is_connected or not self._connection:
            raise ConnectionError("Not connected to AWS IoT")
        
        try:
            logger.info(f"Subscribing to topic: {topic}")
            
            # Store callback for this topic
            if callback:
                self._message_handlers[topic] = callback
            
            # Subscribe to topic
            subscribe_future, packet_id = self._connection.subscribe(
                topic=topic,
                qos=qos,
                callback=self._on_message_received,
            )
            
            await self._wait_for_future(subscribe_future)
            logger.info(f"Successfully subscribed to topic: {topic}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to topic {topic}: {e}")
            raise NavilinkError(f"Subscription failed: {e}")
    
    async def publish(
        self,
        topic: str,
        payload: bytes,
        qos: mqtt.QoS = mqtt.QoS.AT_LEAST_ONCE,
    ) -> None:
        """
        Publish a message to an MQTT topic.
        
        Args:
            topic: MQTT topic to publish to
            payload: Message payload as bytes
            qos: Quality of Service level
            
        Raises:
            ConnectionError: If not connected to AWS IoT
            NavilinkError: If publish fails
        """
        if not self._is_connected or not self._connection:
            raise ConnectionError("Not connected to AWS IoT")
        
        try:
            logger.info(f"Publishing to topic: {topic}")
            
            publish_future, packet_id = self._connection.publish(
                topic=topic,
                payload=payload,
                qos=qos,
            )
            
            await self._wait_for_future(publish_future)
            logger.info(f"Successfully published to topic: {topic}")
            
        except Exception as e:
            logger.error(f"Failed to publish to topic {topic}: {e}")
            raise NavilinkError(f"Publish failed: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from AWS IoT."""
        if self._connection and self._is_connected:
            try:
                logger.info("Disconnecting from AWS IoT...")
                disconnect_future = self._connection.disconnect()
                await self._wait_for_future(disconnect_future)
                self._is_connected = False
                logger.info("Successfully disconnected from AWS IoT")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
    
    def _on_connection_interrupted(self, connection, error, **kwargs):
        """Handle connection interruption."""
        logger.warning(f"Connection interrupted: {error}")
        self._is_connected = False
    
    def _on_connection_resumed(self, connection, return_code, session_present, **kwargs):
        """Handle connection resumption."""
        logger.info(f"Connection resumed: {return_code}, session_present: {session_present}")
        self._is_connected = True
    
    def _on_message_received(self, topic: str, payload: bytes, dup: bool, qos: mqtt.QoS, retain: bool, **kwargs):
        """Handle received MQTT messages."""
        logger.info(f"Message received on topic: {topic}")
        
        # Call topic-specific handler if available
        if topic in self._message_handlers:
            try:
                self._message_handlers[topic](topic, payload)
            except Exception as e:
                logger.error(f"Error in message handler for topic {topic}: {e}")
    
    async def _wait_for_future(self, future: Future, timeout: float = 10.0):
        """Wait for a future to complete with timeout."""
        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, future.result), timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            raise NavilinkError(f"Operation timed out after {timeout} seconds")
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected to AWS IoT."""
        return self._is_connected
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()