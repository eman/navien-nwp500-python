"""
Navien NWP500 Python Library

A Python library for communicating with Navien NWP500
Heat Pump Water Heaters
via the NaviLink service. Provides both REST API access and AWS IoT Core MQTT real-time
communication capabilities with a focus on heat pump water heater
monitoring and data collection.

Primary Use Case: Long-term tank monitoring with DHW (Domestic Hot Water) charge level tracking
Testing: Validated with Navien NWP500 Heat Pump Water Heater
"""

from .auth import NaviLinkAuth
from .client import NaviLinkClient
from .config import HTTPConfig, MQTTConfig, NaviLinkConfig, ReconnectConfig
from .device import NaviLinkDevice
from .exceptions import (
    APIError,
    AuthenticationError,
    CommunicationError,
    DeviceError,
    DeviceOfflineError,
    MQTTError,
    NaviLinkError,
    WebSocketError,
)

# Home Assistant Compatible Interface
from .ha_compat import NavienClient
from .models import (
    DeviceFeatures, 
    DeviceInfo, 
    DeviceStatus,
    calibrate_temperature_from_raw,
    calibrate_temperature_to_raw,
    convert_ambient_temperature,
    convert_celsius_to_fahrenheit,
    TEMPERATURE_CALIBRATION_OFFSET,
)
from .mqtt import NaviLinkMQTT

# Dynamic version from setuptools-scm
try:
    from ._version import __version__
except ImportError:
    # Fallback version for installations without git metadata (e.g., GitHub archive)
    __version__ = "1.4.0"

__author__ = "Emmanuel Levijarvi"

__all__ = [
    # Core Classes
    "NaviLinkClient",
    "NaviLinkDevice",
    "NaviLinkAuth",
    "NaviLinkMQTT",
    # Home Assistant Compatible Interface
    "NavienClient",
    # Configuration
    "NaviLinkConfig",
    "ReconnectConfig",
    "MQTTConfig",
    "HTTPConfig",
    # Data Models
    "DeviceInfo",
    "DeviceStatus", 
    "DeviceFeatures",
    # Temperature Calibration
    "calibrate_temperature_from_raw",
    "calibrate_temperature_to_raw",
    "convert_ambient_temperature",
    "convert_celsius_to_fahrenheit", 
    "TEMPERATURE_CALIBRATION_OFFSET",
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
