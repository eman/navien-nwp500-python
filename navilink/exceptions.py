"""
Custom exceptions for the Navilink library.
"""


class NavilinkError(Exception):
    """Base exception class for all Navilink-related errors."""
    pass


class AuthenticationError(NavilinkError):
    """Raised when AWS IoT authentication fails."""
    pass


class ConnectionError(NavilinkError):
    """Raised when connection to AWS IoT fails."""
    pass


class MessageError(NavilinkError):
    """Raised when there's an issue with MQTT message handling."""
    pass