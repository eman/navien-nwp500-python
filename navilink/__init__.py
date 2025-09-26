"""
NaviLink Python Library

A Python library for communicating with the Navien NaviLink service.
Provides both REST API access and WebSocket/MQTT real-time communication capabilities.
"""

from .client import NaviLinkClient
from .device import NaviLinkDevice
from .auth import NaviLinkAuth
from .mqtt import NaviLinkMQTT
from .models import DeviceInfo, DeviceStatus, DeviceFeatures
from .exceptions import (
    NaviLinkError,
    AuthenticationError,
    DeviceError,
    CommunicationError,
)

__version__ = "0.1.0"
__author__ = "Emmanuel Jarvis"

__all__ = [
    "NaviLinkClient",
    "NaviLinkDevice", 
    "NaviLinkAuth",
    "NaviLinkMQTT",
    "DeviceInfo",
    "DeviceStatus",
    "DeviceFeatures",
    "NaviLinkError",
    "AuthenticationError",
    "DeviceError",
    "CommunicationError",
]