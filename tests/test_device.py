"""
Unit tests for NaviLinkDevice functionality.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from navilink import NaviLinkDevice
from navilink.exceptions import DeviceError, DeviceOfflineError


class TestNaviLinkDevice:
    """Test cases for NaviLinkDevice."""
    
    def test_device_initialization(self, mock_client, mock_device_info):
        """Test device initialization."""
        device = NaviLinkDevice(client=mock_client, device_info=mock_device_info)
        
        assert device.client == mock_client
        assert device.device_info == mock_device_info
        assert device.device_id == "TEST123456"
        assert device.mac_address == "AA:BB:CC:DD:EE:FF"
    
    @pytest.mark.asyncio
    async def test_get_connectivity_status(self, mock_device):
        """Test device connectivity status check."""
        # Mock successful connectivity response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "result": "success",
            "data": {
                "device_connected": 1,
                "last_seen": "2024-01-01T12:00:00Z"
            }
        }
        
        mock_device.client._session.get.return_value.__aenter__.return_value = mock_response
        
        connectivity = await mock_device.get_connectivity_status()
        
        assert connectivity["device_connected"] == 1
        assert "last_seen" in connectivity
    
    @pytest.mark.asyncio
    async def test_get_device_info(self, mock_device):
        """Test device info retrieval."""
        # Mock device info response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "result": "success", 
            "data": {
                "device_id": "TEST123456",
                "firmware_version": "1.2.3",
                "features": ["DHW", "HEATING", "REMOTE_CONTROL"]
            }
        }
        
        mock_device.client._session.post.return_value.__aenter__.return_value = mock_response
        
        info = await mock_device.get_device_info()
        
        assert info["device_id"] == "TEST123456"
        assert info["firmware_version"] == "1.2.3"
        assert "DHW" in info["features"]
    
    @pytest.mark.asyncio
    async def test_set_temperature(self, mock_device):
        """Test temperature setting."""
        # Mock successful temperature set response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "result": "success",
            "message": "Temperature updated"
        }
        
        with patch.object(mock_device, '_send_command') as mock_send:
            mock_send.return_value = True
            
            result = await mock_device.set_temperature(120)
            
            assert result is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_temperature_invalid_range(self, mock_device):
        """Test temperature setting with invalid range."""
        with pytest.raises(ValueError, match="Temperature must be"):
            await mock_device.set_temperature(200)  # Too hot
            
        with pytest.raises(ValueError, match="Temperature must be"):
            await mock_device.set_temperature(50)   # Too cold
    
    @pytest.mark.asyncio
    async def test_set_dhw_mode(self, mock_device):
        """Test DHW mode setting."""
        with patch.object(mock_device, '_send_command') as mock_send:
            mock_send.return_value = True
            
            result = await mock_device.set_dhw_mode(1)  # Heat pump mode
            
            assert result is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_device_offline_error(self, mock_device):
        """Test handling of offline device."""
        # Mock device as offline
        mock_device.device_info.device_connected = 0
        
        with pytest.raises(DeviceOfflineError, match="Device TEST123456 is offline"):
            await mock_device._check_online_status()
    
    @pytest.mark.asyncio 
    async def test_get_mqtt_connection(self, mock_device):
        """Test MQTT connection creation."""
        with patch('navilink.device.NaviLinkMQTT') as mock_mqtt_class:
            mock_mqtt = AsyncMock()
            mock_mqtt_class.return_value = mock_mqtt
            
            mqtt_conn = await mock_device.get_mqtt_connection()
            
            assert mqtt_conn == mock_mqtt
            mock_mqtt_class.assert_called_once()
    
    def test_device_properties(self, mock_device):
        """Test device property access."""
        assert mock_device.device_id == "TEST123456"
        assert mock_device.device_name == "NWP500 Test"
        assert mock_device.model_name == "NWP500"
        assert mock_device.mac_address == "AA:BB:CC:DD:EE:FF"
    
    def test_device_repr(self, mock_device):
        """Test device string representation."""
        repr_str = repr(mock_device)
        
        assert "NaviLinkDevice" in repr_str
        assert "TEST123456" in repr_str
        assert "NWP500 Test" in repr_str
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_device):
        """Test device error handling."""
        # Mock API error response
        mock_response = AsyncMock()
        mock_response.status = 400
        mock_response.json.return_value = {
            "result": "error",
            "message": "Invalid command"
        }
        
        mock_device.client._session.post.return_value.__aenter__.return_value = mock_response
        
        with pytest.raises(DeviceError, match="Invalid command"):
            await mock_device.get_device_info()
    
    @pytest.mark.asyncio
    async def test_command_validation(self, mock_device):
        """Test command parameter validation."""
        # Test DHW mode validation
        with pytest.raises(ValueError, match="Invalid DHW mode"):
            await mock_device.set_dhw_mode(99)  # Invalid mode
    
    @pytest.mark.asyncio
    async def test_device_status_parsing(self, mock_device, mock_device_status):
        """Test device status data parsing."""
        # Mock status response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "result": "success",
            "data": mock_device_status
        }
        
        mock_device.client._session.get.return_value.__aenter__.return_value = mock_response
        
        with patch.object(mock_device, '_parse_status_data') as mock_parse:
            mock_parse.return_value = mock_device_status
            
            status = await mock_device.get_status()
            
            assert status is not None
            mock_parse.assert_called_once()