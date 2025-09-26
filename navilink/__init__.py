"""
Navilink - AWS IoT MQTT WebSocket Communication Library

A Python library for authenticating with AWS IoT and asynchronously receiving
MQTT messages over WebSocket connections.
"""

__version__ = "0.1.0"
__author__ = "eman"

from .client import NavilinkClient
from .exceptions import NavilinkError, AuthenticationError, ConnectionError

__all__ = [
    "NavilinkClient",
    "NavilinkError", 
    "AuthenticationError",
    "ConnectionError",
]