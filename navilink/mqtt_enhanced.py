"""
Enhanced MQTT client based on AWS IoT SDK v2 best practices.
Adds better lifecycle management and error handling to our existing approach.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable
import uuid
import websockets
import ssl
from enum import Enum

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    """MQTT connection state following AWS IoT SDK patterns."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    STOPPED = "stopped"

class LifecycleEvent(Enum):
    """Lifecycle events following AWS IoT SDK patterns."""
    CONNECTION_ATTEMPT = "connection_attempt"
    CONNECTION_SUCCESS = "connection_success"
    CONNECTION_FAILURE = "connection_failure" 
    DISCONNECT = "disconnect"
    STOPPED = "stopped"

class EnhancedMQTTClient:
    """Enhanced MQTT client with AWS IoT SDK v2 inspired lifecycle management."""
    
    def __init__(self, device_mac: str, endpoint: str, user_info: dict, aws_credentials: dict):
        self.device_mac = device_mac
        self.endpoint = endpoint
        self.user_info = user_info
        self.aws_credentials = aws_credentials
        
        # Connection state
        self.state = ConnectionState.DISCONNECTED
        self.websocket = None
        self._connected = False
        self._reconnect_task = None
        self._stopped = False
        
        # Lifecycle callbacks
        self.lifecycle_callbacks: Dict[LifecycleEvent, List[Callable]] = {
            event: [] for event in LifecycleEvent
        }
        
        # Message handling
        self.message_callbacks = []
        self.pending_commands = {}
        self.command_timeout = 30.0
        
        # Statistics (following AWS best practices)
        self.stats = {
            'connection_attempts': 0,
            'successful_connections': 0,
            'failed_connections': 0,
            'messages_published': 0,
            'messages_received': 0,
            'last_connection_attempt': None,
            'last_successful_connection': None,
            'current_connection_duration': 0
        }
        
        # Reconnection logic
        self.reconnect_delay = 1.0  # Start with 1 second
        self.max_reconnect_delay = 300.0  # Max 5 minutes
        self.reconnect_backoff_factor = 2.0

    def add_lifecycle_callback(self, event: LifecycleEvent, callback: Callable):
        """Add callback for lifecycle events."""
        self.lifecycle_callbacks[event].append(callback)
    
    def _emit_lifecycle_event(self, event: LifecycleEvent, data: Dict[str, Any] = None):
        """Emit lifecycle event to all registered callbacks."""
        event_data = {
            'event': event,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'state': self.state,
            'stats': self.stats.copy(),
            **(data or {})
        }
        
        logger.info(f"🔄 Lifecycle Event: {event.value} - {event_data.get('reason', '')}")
        
        for callback in self.lifecycle_callbacks[event]:
            try:
                # Follow AWS best practice - don't block in callbacks
                asyncio.create_task(self._safe_callback(callback, event_data))
            except Exception as e:
                logger.error(f"❌ Lifecycle callback error: {e}")
    
    async def _safe_callback(self, callback: Callable, data: Dict[str, Any]):
        """Safely execute callback without blocking main thread."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(data)
            else:
                callback(data)
        except Exception as e:
            logger.error(f"❌ Callback execution error: {e}")
    
    async def start(self):
        """Start the MQTT client (following AWS IoT SDK naming)."""
        if self.state != ConnectionState.DISCONNECTED:
            logger.warning("Client already started or starting")
            return
        
        self._stopped = False
        await self._attempt_connection()
    
    async def stop(self):
        """Stop the MQTT client (following AWS IoT SDK naming)."""
        logger.info("🛑 Stopping MQTT client...")
        self._stopped = True
        
        # Cancel reconnect task
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None
        
        # Close websocket
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.state = ConnectionState.STOPPED
        self._connected = False
        
        self._emit_lifecycle_event(LifecycleEvent.STOPPED)
        logger.info("✅ MQTT client stopped")
    
    async def _attempt_connection(self):
        """Attempt connection with lifecycle event management."""
        if self._stopped:
            return
        
        self.state = ConnectionState.CONNECTING
        self.stats['connection_attempts'] += 1
        self.stats['last_connection_attempt'] = datetime.now(timezone.utc).isoformat()
        
        connection_start = time.time()
        
        self._emit_lifecycle_event(LifecycleEvent.CONNECTION_ATTEMPT, {
            'attempt_number': self.stats['connection_attempts'],
            'endpoint': self.endpoint
        })
        
        try:
            # Import and use existing connection logic
            from .aws_iot_websocket import generate_websocket_url
            
            websocket_url = generate_websocket_url(
                self.endpoint, 
                self.aws_credentials['AccessKeyId'],
                self.aws_credentials['SecretAccessKey'], 
                self.aws_credentials['SessionToken'],
                f"navilink-client-{uuid.uuid4()}",
                "us-east-1"
            )
            
            # Create SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Connect
            self.websocket = await websockets.connect(
                websocket_url,
                ssl=ssl_context,
                extra_headers={
                    'Sec-WebSocket-Protocol': 'mqtt'
                }
            )
            
            # Send MQTT CONNECT packet
            connect_packet = self._create_connect_packet()
            await self.websocket.send(connect_packet)
            
            # Wait for CONNACK
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
            if not self._handle_connack(response):
                raise Exception("CONNACK failed")
            
            # Success!
            connection_duration = time.time() - connection_start
            self.state = ConnectionState.CONNECTED
            self._connected = True
            self.stats['successful_connections'] += 1
            self.stats['last_successful_connection'] = datetime.now(timezone.utc).isoformat()
            
            # Reset reconnect delay on successful connection
            self.reconnect_delay = 1.0
            
            self._emit_lifecycle_event(LifecycleEvent.CONNECTION_SUCCESS, {
                'connection_duration_ms': int(connection_duration * 1000),
                'endpoint': self.endpoint
            })
            
            # Start message handling
            asyncio.create_task(self._message_loop())
            
        except Exception as e:
            # Connection failed
            connection_duration = time.time() - connection_start
            self.state = ConnectionState.DISCONNECTED
            self._connected = False
            self.stats['failed_connections'] += 1
            
            self._emit_lifecycle_event(LifecycleEvent.CONNECTION_FAILURE, {
                'error': str(e),
                'connection_duration_ms': int(connection_duration * 1000),
                'will_retry': not self._stopped
            })
            
            # Schedule reconnect if not stopped
            if not self._stopped:
                await self._schedule_reconnect()
    
    async def _schedule_reconnect(self):
        """Schedule reconnection with exponential backoff."""
        if self._stopped:
            return
        
        self.state = ConnectionState.RECONNECTING
        
        logger.info(f"⏰ Scheduling reconnect in {self.reconnect_delay}s...")
        
        self._reconnect_task = asyncio.create_task(
            asyncio.sleep(self.reconnect_delay)
        )
        
        try:
            await self._reconnect_task
            # Exponential backoff
            self.reconnect_delay = min(
                self.reconnect_delay * self.reconnect_backoff_factor,
                self.max_reconnect_delay
            )
            await self._attempt_connection()
        except asyncio.CancelledError:
            pass
    
    async def _message_loop(self):
        """Handle incoming messages with proper error handling."""
        try:
            while self._connected and not self._stopped and self.websocket:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    self.stats['messages_received'] += 1
                    
                    # Process message
                    await self._handle_message(message)
                    
                except asyncio.TimeoutError:
                    # Normal timeout for checking stop condition
                    continue
                except websockets.exceptions.ConnectionClosed as e:
                    logger.warning(f"🔌 WebSocket connection closed: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"❌ Message loop error: {e}")
        finally:
            # Connection lost
            if self._connected:
                self._connected = False
                self.state = ConnectionState.DISCONNECTED
                
                self._emit_lifecycle_event(LifecycleEvent.DISCONNECT, {
                    'reason': 'message_loop_ended'
                })
                
                # Auto-reconnect if not stopped
                if not self._stopped:
                    await self._schedule_reconnect()
    
    def _create_connect_packet(self) -> bytes:
        """Create MQTT CONNECT packet."""
        # Use existing logic from mqtt.py
        from .mqtt_protocol import create_connect_packet
        client_id = f"navilink-{self.device_mac}-{int(time.time())}"
        return create_connect_packet(client_id)
    
    def _handle_connack(self, response: bytes) -> bool:
        """Handle CONNACK packet."""
        # Use existing logic from mqtt.py
        from .mqtt_protocol import parse_connack
        return parse_connack(response)
    
    async def _handle_message(self, message: bytes):
        """Handle incoming MQTT message."""
        # Use existing message parsing logic
        from .mqtt_protocol import parse_mqtt_message
        
        try:
            parsed = parse_mqtt_message(message)
            if parsed:
                # Notify callbacks (non-blocking)
                for callback in self.message_callbacks:
                    asyncio.create_task(self._safe_callback(callback, parsed))
        except Exception as e:
            logger.error(f"❌ Message parsing error: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self.state == ConnectionState.CONNECTED
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get connection statistics."""
        stats = self.stats.copy()
        stats['current_state'] = self.state.value
        stats['is_connected'] = self.is_connected
        
        if self.stats['last_successful_connection']:
            # Calculate connection duration
            last_conn = datetime.fromisoformat(self.stats['last_successful_connection'].replace('Z', '+00:00'))
            duration = (datetime.now(timezone.utc) - last_conn).total_seconds()
            stats['current_connection_duration'] = duration if self.is_connected else 0
        
        return stats

# Example usage with lifecycle monitoring
async def create_enhanced_mqtt_client(device_mac: str, endpoint: str, user_info: dict, aws_credentials: dict):
    """Create enhanced MQTT client with lifecycle monitoring."""
    
    client = EnhancedMQTTClient(device_mac, endpoint, user_info, aws_credentials)
    
    # Add lifecycle event handlers for debugging
    async def on_connection_attempt(data):
        logger.info(f"🔄 Connection attempt #{data['attempt_number']}")
    
    async def on_connection_success(data):
        logger.info(f"✅ Connected successfully in {data['connection_duration_ms']}ms")
    
    async def on_connection_failure(data):
        logger.error(f"❌ Connection failed: {data['error']}")
        if data['will_retry']:
            logger.info("🔄 Will retry connection...")
    
    async def on_disconnect(data):
        logger.warning(f"🔌 Disconnected: {data['reason']}")
    
    client.add_lifecycle_callback(LifecycleEvent.CONNECTION_ATTEMPT, on_connection_attempt)
    client.add_lifecycle_callback(LifecycleEvent.CONNECTION_SUCCESS, on_connection_success)
    client.add_lifecycle_callback(LifecycleEvent.CONNECTION_FAILURE, on_connection_failure)
    client.add_lifecycle_callback(LifecycleEvent.DISCONNECT, on_disconnect)
    
    return client