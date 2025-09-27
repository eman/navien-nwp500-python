"""
Custom exceptions for the NaviLink library.
"""

class NaviLinkError(Exception):
    """Base exception for all NaviLink errors."""
    pass

class AuthenticationError(NaviLinkError):
    """Raised when authentication fails."""
    pass

class DeviceError(NaviLinkError):
    """Raised when device operations fail."""
    pass

class CommunicationError(NaviLinkError):
    """Raised when communication with the service fails."""
    pass

class DeviceOfflineError(DeviceError):
    """Raised when a device is offline or unreachable."""
    pass

class InvalidCredentialsError(AuthenticationError):
    """Raised when provided credentials are invalid."""
    pass

class TokenExpiredError(AuthenticationError):
    """Raised when authentication token has expired."""
    pass

class APIError(CommunicationError):
    """Raised when API returns an error response."""
    
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response

class WebSocketError(CommunicationError):
    """Raised when WebSocket communication fails."""
    pass

class MQTTError(CommunicationError):
    """Raised when MQTT communication fails."""
    pass