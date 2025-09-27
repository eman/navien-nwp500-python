"""
Unit tests for data models and parsing functionality.
"""

import pytest

from navien_nwp500.exceptions import NaviLinkError
from navien_nwp500.models import DeviceFeatures, DeviceInfo, DeviceStatus


class TestDeviceInfo:
    """Test cases for DeviceInfo model."""

    def test_device_info_creation(self, mock_device_data):
        """Test DeviceInfo creation from valid data."""
        device_info = DeviceInfo(**mock_device_data)

        assert device_info.device_id == "TEST123456"
        assert device_info.device_type == 52
        assert device_info.mac_address == "AA:BB:CC:DD:EE:FF"
        assert device_info.device_name == "NWP500 Test"
        assert device_info.model_name == "NWP500"
        assert device_info.is_online is True  # device_connected == 1

    def test_device_info_offline(self, mock_device_data):
        """Test DeviceInfo with offline device."""
        mock_device_data["device_connected"] = 0
        device_info = DeviceInfo(**mock_device_data)

        assert device_info.is_online is False

    def test_device_info_repr(self, mock_device_data):
        """Test DeviceInfo string representation."""
        device_info = DeviceInfo(**mock_device_data)
        repr_str = repr(device_info)

        assert "TEST123456" in repr_str
        assert "NWP500 Test" in repr_str


class TestDeviceStatus:
    """Test cases for DeviceStatus model."""

    def test_device_status_creation(self, mock_device_status):
        """Test DeviceStatus creation from valid data."""
        status = DeviceStatus(**mock_device_status)

        assert status.dhw_charge_per == 95
        assert status.dhw_temperature == 121
        assert status.operation_mode == 32
        assert status.current_inst_power == 466
        assert status.error_code == 0

    def test_temperature_conversions(self, mock_device_status):
        """Test temperature field conversions."""
        status = DeviceStatus(**mock_device_status)

        # Test 0.1°F conversion fields
        assert status.tank_upper_temp_fahrenheit == 60.5
        assert status.tank_lower_temp_fahrenheit == 61.1
        assert status.discharge_temp_fahrenheit == 76.1
        assert status.ambient_temp_fahrenheit == 23.8

    def test_is_heating_property(self, mock_device_status):
        """Test is_heating property logic."""
        status = DeviceStatus(**mock_device_status)

        # Mode 32 with high power should indicate heating
        assert status.is_heating is True

        # Test standby mode
        mock_device_status["operation_mode"] = 0
        mock_device_status["current_inst_power"] = 1
        status = DeviceStatus(**mock_device_status)
        assert status.is_heating is False

    def test_is_heat_pump_active(self, mock_device_status):
        """Test heat pump detection logic."""
        status = DeviceStatus(**mock_device_status)

        # comp_use=2 and eva_fan_use=2 should indicate heat pump active
        assert status.is_heat_pump_active is True

        # Test inactive heat pump
        mock_device_status["comp_use"] = 0
        mock_device_status["eva_fan_use"] = 0
        status = DeviceStatus(**mock_device_status)
        assert status.is_heat_pump_active is False

    def test_has_error_property(self, mock_device_status):
        """Test error detection."""
        status = DeviceStatus(**mock_device_status)
        assert status.has_error is False

        # Test with error
        mock_device_status["error_code"] = 5
        status = DeviceStatus(**mock_device_status)
        assert status.has_error is True

    def test_power_efficiency_calculation(self, mock_device_status):
        """Test power efficiency calculations."""
        status = DeviceStatus(**mock_device_status)

        # Heat pump mode should be efficient (< 1000W typically)
        assert status.current_inst_power < 1000
        assert status.operation_mode == 32  # Heat pump mode

    def test_status_repr(self, mock_device_status):
        """Test DeviceStatus string representation."""
        status = DeviceStatus(**mock_device_status)
        repr_str = repr(status)

        assert "95%" in repr_str  # dhw_charge_per
        assert "121°F" in repr_str  # dhw_temperature
        assert "Mode 32" in repr_str  # operation_mode


class TestDeviceFeatures:
    """Test cases for DeviceFeatures model."""

    def test_device_features_creation(self):
        """Test DeviceFeatures creation."""
        features_data = {
            "dhw_mode_available": True,
            "temperature_control": True,
            "scheduling_available": True,
            "remote_control": True,
            "eco_mode_available": False,
        }

        features = DeviceFeatures(**features_data)

        assert features.dhw_mode_available is True
        assert features.temperature_control is True
        assert features.eco_mode_available is False

    def test_features_defaults(self):
        """Test default feature values."""
        features = DeviceFeatures()

        # Most features should default to False for safety
        assert features.dhw_mode_available is False
        assert features.temperature_control is False
        assert features.scheduling_available is False


class TestDataValidation:
    """Test data validation and edge cases."""

    def test_invalid_device_type(self, mock_device_data):
        """Test validation of device types."""
        # Device type 52 is expected for water heaters
        mock_device_data["device_type"] = 99  # Invalid type

        device_info = DeviceInfo(**mock_device_data)
        # Should still create but might log warning in actual implementation
        assert device_info.device_type == 99

    def test_temperature_bounds(self, mock_device_status):
        """Test temperature value bounds."""
        # Test extreme temperature values
        mock_device_status["dhw_temperature"] = 200  # Very hot
        status = DeviceStatus(**mock_device_status)

        assert status.dhw_temperature == 200
        # In a real implementation, might want validation/warnings

    def test_charge_percentage_bounds(self, mock_device_status):
        """Test charge percentage validation."""
        # Test edge cases for charge percentage
        mock_device_status["dhw_charge_per"] = 100  # Maximum
        status = DeviceStatus(**mock_device_status)
        assert status.dhw_charge_per == 100

        mock_device_status["dhw_charge_per"] = 0  # Minimum
        status = DeviceStatus(**mock_device_status)
        assert status.dhw_charge_per == 0

    def test_power_consumption_validation(self, mock_device_status):
        """Test power consumption value validation."""
        # Test very high power (electric backup mode)
        mock_device_status["current_inst_power"] = 4500
        mock_device_status["operation_mode"] = 33  # Electric backup mode

        status = DeviceStatus(**mock_device_status)
        assert status.current_inst_power == 4500
        assert not status.is_heat_pump_active  # Should detect electric mode
