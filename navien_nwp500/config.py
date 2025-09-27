"""
Configuration management for NaviLink library.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class LogLevel(Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class MQTTProtocolVersion(Enum):
    """Supported MQTT protocol versions."""
    MQTT3 = "MQTT3"
    MQTT5 = "MQTT5"


@dataclass
class ReconnectConfig:
    """Configuration for connection reconnection behavior."""
    max_retries: int = 20
    initial_delay: float = 2.0
    max_delay: float = 120.0
    jitter: bool = True
    backoff_multiplier: float = 2.0


@dataclass
class MQTTConfig:
    """Configuration for MQTT connection."""
    protocol_version: MQTTProtocolVersion = MQTTProtocolVersion.MQTT3
    keep_alive_secs: int = 30
    ping_timeout_ms: int = 3000
    operation_timeout_secs: int = 10
    clean_session: bool = True
    reconnect_config: ReconnectConfig = field(default_factory=ReconnectConfig)


@dataclass
class HTTPConfig:
    """Configuration for HTTP client."""
    timeout: float = 30.0
    max_connections: int = 100
    max_connections_per_host: int = 10
    user_agent: str = "NaviLink-Python/1.0.0"


@dataclass
class NaviLinkConfig:
    """
    Comprehensive configuration for NaviLink client.
    
    Configuration can be provided via:
    1. Direct parameters to NaviLinkClient
    2. Environment variables (NAVILINK_*)
    3. Configuration file (future enhancement)
    """
    
    # Authentication
    email: Optional[str] = None
    password: Optional[str] = None
    
    # API Configuration
    base_url: str = "https://nlus.naviensmartcontrol.com/api/v2.1"
    websocket_url: str = "wss://nlus-iot.naviensmartcontrol.com/mqtt"
    
    # Protocol Configuration
    mqtt: MQTTConfig = field(default_factory=MQTTConfig)
    http: HTTPConfig = field(default_factory=HTTPConfig)
    
    # Logging
    log_level: LogLevel = LogLevel.INFO
    
    # Development/Debug Settings
    debug_mode: bool = False
    
    @classmethod
    def from_environment(cls, env_file: Optional[str] = None) -> 'NaviLinkConfig':
        """
        Create configuration from environment variables.
        
        Args:
            env_file: Optional path to .env file to load first
            
        Supported environment variables:
        - NAVILINK_EMAIL: User email for authentication
        - NAVILINK_PASSWORD: User password for authentication
        - NAVILINK_DEBUG: Enable debug mode (true/false)
        - NAVILINK_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        - NAVILINK_MQTT_PROTOCOL: MQTT protocol version (MQTT3, MQTT5)
        """
        # Load .env file if provided or if .env exists
        if env_file or os.path.exists(".env"):
            env_path = env_file or ".env"
            try:
                cls._load_env_file(env_path)
            except Exception as e:
                # Don't fail if .env file is invalid, just continue with system env vars
                pass
        
        config = cls()
        
        # Authentication
        config.email = os.getenv("NAVILINK_EMAIL")
        config.password = os.getenv("NAVILINK_PASSWORD")
        
        # Debug mode
        debug_env = os.getenv("NAVILINK_DEBUG", "false").lower()
        config.debug_mode = debug_env in ("true", "1", "yes", "on")
        
        # Log level
        log_level_env = os.getenv("NAVILINK_LOG_LEVEL", "INFO").upper()
        try:
            config.log_level = LogLevel(log_level_env)
        except ValueError:
            config.log_level = LogLevel.INFO
        
        # MQTT Protocol
        mqtt_protocol_env = os.getenv("NAVILINK_MQTT_PROTOCOL", "MQTT3").upper()
        try:
            config.mqtt.protocol_version = MQTTProtocolVersion(mqtt_protocol_env)
        except ValueError:
            config.mqtt.protocol_version = MQTTProtocolVersion.MQTT3
        
        return config
    
    @staticmethod
    def _load_env_file(env_file: str) -> None:
        """Load environment variables from a .env file."""
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and not os.getenv(key):  # Don't override existing env vars
                            os.environ[key] = value
        except FileNotFoundError:
            pass  # File doesn't exist, that's okay
    
    def validate(self) -> None:
        """
        Validate configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        if not self.base_url:
            raise ValueError("base_url is required")
        
        if not self.websocket_url:
            raise ValueError("websocket_url is required")
        
        if self.mqtt.reconnect_config.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        
        if self.mqtt.reconnect_config.initial_delay <= 0:
            raise ValueError("initial_delay must be > 0")
        
        if self.mqtt.reconnect_config.max_delay <= 0:
            raise ValueError("max_delay must be > 0")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        def _convert_value(value):
            if isinstance(value, Enum):
                return value.value
            elif hasattr(value, '__dict__'):
                return {k: _convert_value(v) for k, v in value.__dict__.items()}
            else:
                return value
        
        return {k: _convert_value(v) for k, v in self.__dict__.items()}