"""
NaviLink Python Library

A production-ready Python library for communicating with the Navien NaviLink service.
Provides both REST API access and AWS IoT Core MQTT real-time communication capabilities
with a focus on heat pump water heater monitoring and data collection.

Status: Production Ready ✅
Primary Use Case: Long-term tank monitoring with DHW (Domestic Hot Water) charge level tracking  
Testing: Validated with Navien NWP500 Heat Pump Water Heater
"""

from .client import NaviLinkClient
from .device import NaviLinkDevice
from .auth import NaviLinkAuth
from .mqtt import NaviLinkMQTT
from .config import NaviLinkConfig, ReconnectConfig, MQTTConfig, HTTPConfig
from .models import DeviceInfo, DeviceStatus, DeviceFeatures
from .exceptions import (
    NaviLinkError,
    AuthenticationError,
    DeviceError,
    CommunicationError,
    APIError,
    WebSocketError,
    MQTTError,
    DeviceOfflineError,
)

__version__ = "1.0.0"
__author__ = "Emmanuel Jarvis"

__all__ = [
    # Core Classes
    "NaviLinkClient",
    "NaviLinkDevice", 
    "NaviLinkAuth",
    "NaviLinkMQTT",
    
    # Configuration
    "NaviLinkConfig",
    "ReconnectConfig", 
    "MQTTConfig",
    "HTTPConfig",
    
    # Data Models
    "DeviceInfo",
    "DeviceStatus", 
    "DeviceFeatures",
    
    # Exceptions
    "NaviLinkError",
    "AuthenticationError",
    "DeviceError",
    "CommunicationError",
    "APIError",
    "WebSocketError", 
    "MQTTError",
    "DeviceOfflineError",
]