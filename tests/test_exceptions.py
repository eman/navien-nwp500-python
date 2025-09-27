"""
Unit tests for custom exceptions.
"""
import pytest

from navien_nwp500.exceptions import (
    APIError,
    AuthenticationError,
    CommunicationError,
    DeviceError,
    DeviceOfflineError,
    MQTTError,
    NaviLinkError,
    WebSocketError,
)


class TestExceptions:
    """Test cases for custom exceptions."""
    
    def test_base_navien_nwp500_error(self):
        """Test base NaviLinkError."""
        error = NaviLinkError("Base error message")
        
        assert str(error) == "Base error message"
        assert isinstance(error, Exception)
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Invalid credentials")
        
        assert str(error) == "Invalid credentials"
        assert isinstance(error, NaviLinkError)
    
    def test_authentication_error_with_details(self):
        """Test AuthenticationError with additional details."""
        details = {"email": "test@example.com", "error_code": 401}
        error = AuthenticationError("Login failed", details=details)
        
        assert str(error) == "Login failed"
        assert error.details == details
    
    def test_device_error(self):
        """Test DeviceError."""
        error = DeviceError("Device command failed", device_id="TEST123")
        
        assert str(error) == "Device command failed"
        assert error.device_id == "TEST123"
        assert isinstance(error, NaviLinkError)
    
    def test_device_offline_error(self):
        """Test DeviceOfflineError."""
        error = DeviceOfflineError("Device is offline", device_id="TEST123")
        
        assert str(error) == "Device is offline"
        assert error.device_id == "TEST123"
        assert isinstance(error, DeviceError)
    
    def test_communication_error(self):
        """Test CommunicationError."""
        error = CommunicationError("Network timeout")
        
        assert str(error) == "Network timeout"
        assert isinstance(error, NaviLinkError)
    
    def test_api_error(self):
        """Test APIError."""
        error = APIError("Server error", status_code=500)
        
        assert str(error) == "Server error"
        assert error.status_code == 500
        assert isinstance(error, NaviLinkError)
    
    def test_api_error_with_response(self):
        """Test APIError with response data."""
        response_data = {"error": "validation_failed", "details": "Invalid input"}
        error = APIError("Validation failed", status_code=400, response=response_data)
        
        assert str(error) == "Validation failed"
        assert error.status_code == 400
        assert error.response == response_data
    
    def test_websocket_error(self):
        """Test WebSocketError."""
        error = WebSocketError("Connection closed unexpectedly")
        
        assert str(error) == "Connection closed unexpectedly"
        assert isinstance(error, CommunicationError)
    
    def test_mqtt_error(self):
        """Test MQTTError."""
        error = MQTTError("MQTT publish failed", topic="device/status")
        
        assert str(error) == "MQTT publish failed"
        assert error.topic == "device/status"
        assert isinstance(error, CommunicationError)
    
    def test_exception_chaining(self):
        """Test exception chaining with cause."""
        original_error = ConnectionError("Network unreachable")
        
        try:
            raise CommunicationError("Failed to connect") from original_error
        except CommunicationError as e:
            assert str(e) == "Failed to connect"
            assert e.__cause__ is original_error
    
    def test_exception_inheritance_hierarchy(self):
        """Test exception inheritance hierarchy."""
        # Test that all specific errors inherit from NaviLinkError
        auth_error = AuthenticationError("Auth failed")
        device_error = DeviceError("Device failed")
        comm_error = CommunicationError("Comm failed")
        api_error = APIError("API failed")
        ws_error = WebSocketError("WS failed") 
        mqtt_error = MQTTError("MQTT failed")
        offline_error = DeviceOfflineError("Device offline")
        
        # All should be instances of NaviLinkError
        assert isinstance(auth_error, NaviLinkError)
        assert isinstance(device_error, NaviLinkError)
        assert isinstance(comm_error, NaviLinkError)
        assert isinstance(api_error, NaviLinkError)
        assert isinstance(ws_error, NaviLinkError)
        assert isinstance(mqtt_error, NaviLinkError)
        assert isinstance(offline_error, NaviLinkError)
        
        # Specific inheritance relationships
        assert isinstance(ws_error, CommunicationError)
        assert isinstance(mqtt_error, CommunicationError)
        assert isinstance(offline_error, DeviceError)
    
    def test_error_with_empty_message(self):
        """Test exception with empty message."""
        error = NaviLinkError("")
        assert str(error) == ""
    
    def test_error_repr(self):
        """Test exception representation."""
        error = DeviceError("Test error", device_id="DEV123")
        repr_str = repr(error)
        
        assert "DeviceError" in repr_str
        assert "Test error" in repr_str