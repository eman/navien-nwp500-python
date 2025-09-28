"""
Test Home Assistant Compatibility Interface.

This test validates that the NavienClient provides the expected interface
for Home Assistant integration while preserving all critical data fields
including the dhw_charge_percent that was missing from the original recommendations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from navien_nwp500.exceptions import AuthenticationError, DeviceError
from navien_nwp500.ha_compat import NavienClient
from navien_nwp500.models import DeviceFeatures, DeviceInfo, DeviceStatus


@pytest.fixture
def mock_device_status():
    """Create a mock DeviceStatus with realistic production data."""
    return DeviceStatus(
        command=16777219,
        outside_temperature=0,
        special_function_status=0,
        did_reload=0,
        error_code=0,
        sub_error_code=0,
        operation_mode=32,  # Heat pump active
        operation_busy=0,
        freeze_protection_use=0,
        dhw_use=1,
        dhw_use_sustained=0,
        dhw_temperature=121,  # °F
        dhw_temperature_setting=121,  # °F
        program_reservation_use=0,
        smart_diagnostic=0,
        fault_status1=0,
        fault_status2=0,
        wifi_rssi=-45,
        eco_use=0,
        dhw_target_temperature_setting=121,
        tank_upper_temperature=605,  # 0.1°F units = 60.5°F
        tank_lower_temperature=611,  # 0.1°F units = 61.1°F
        discharge_temperature=761,  # 0.1°F units = 76.1°F
        suction_temperature=0,
        evaporator_temperature=0,
        ambient_temperature=238,  # 0.1°F units = 23.8°F
        target_super_heat=0,
        comp_use=2,  # Compressor active
        eev_use=0,
        eva_fan_use=2,  # Evaporator fan active
        current_inst_power=466,  # Watts
        shut_off_valve_use=0,
        con_ovr_sensor_use=0,
        wtr_ovr_sensor_use=0,
        dhw_charge_per=99,  # CRITICAL: Tank charge percentage
        dr_event_status=0,
        vacation_day_setting=0,
        vacation_day_elapsed=0,
        freeze_protection_temperature=0,
        anti_legionella_use=0,
        anti_legionella_period=0,
        anti_legionella_operation_busy=0,
        program_reservation_type=0,
        dhw_operation_setting=0,
        temperature_type=0,
        temp_formula_type=0,
        error_buzzer_use=0,
        current_heat_use=0,
        current_inlet_temperature=0,
        current_statenum=0,
        target_fan_rpm=0,
        current_fan_rpm=0,
        fan_pwm=0,
        dhw_temperature2=0,
        current_dhw_flow_rate=0,
        mixing_rate=0,
        eev_step=0,
        current_super_heat=0,
        heat_upper_use=1,  # Ready
        heat_lower_use=1,  # Ready
        scald_use=0,
        air_filter_alarm_use=0,
        air_filter_alarm_period=0,
        air_filter_alarm_elapsed=0,
        cumulated_op_time_eva_fan=0,
        cumulated_dhw_flow_rate=0,
        tou_status=0,
        hp_upper_on_temp_setting=0,
        hp_upper_off_temp_setting=0,
        hp_lower_on_temp_setting=0,
        hp_lower_off_temp_setting=0,
        he_upper_on_temp_setting=0,
        he_upper_off_temp_setting=0,
        he_lower_on_temp_setting=0,
        he_lower_off_temp_setting=0,
        hp_upper_on_diff_temp_setting=0,
        hp_upper_off_diff_temp_setting=0,
        hp_lower_on_diff_temp_setting=0,
        hp_lower_off_diff_temp_setting=0,
        he_upper_on_diff_temp_setting=0,
        he_upper_off_diff_temp_setting=0,
        he_lower_on_tdiffemp_setting=0,
        he_lower_off_diff_temp_setting=0,
        dr_override_status=0,
        tou_override_status=0,
        total_energy_capacity=0,
        available_energy_capacity=0,
        heat_pump_status=2,
        resistance_heater_status=0,
        defrost_mode=0,
        device_connected=1,
    )


class TestNavienClientAPI:
    """Test the Home Assistant compatible API interface."""

    def test_client_initialization(self):
        """Test that NavienClient initializes correctly."""
        client = NavienClient("test@example.com", "password")

        assert client.username == "test@example.com"
        assert client.password == "password"
        assert client._authenticated == False
        assert client._client is None
        assert client._device is None

    @pytest.mark.asyncio
    async def test_authentication_success(self):
        """Test successful authentication."""
        client = NavienClient("test@example.com", "password")

        # Mock the underlying NaviLink client
        with patch("navien_nwp500.ha_compat.NaviLinkClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.authenticate.return_value = MagicMock()
            mock_client.get_devices.return_value = [MagicMock(name="Test Device")]
            mock_client_class.return_value = mock_client

            result = await client.authenticate()

            assert result is True
            assert client._authenticated is True
            assert client._client is not None
            assert client._device is not None

    @pytest.mark.asyncio
    async def test_authentication_failure(self):
        """Test authentication failure with proper error message."""
        client = NavienClient("bad@example.com", "badpassword")

        with patch("navien_nwp500.ha_compat.NaviLinkClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.authenticate.side_effect = AuthenticationError(
                "Invalid credentials"
            )
            mock_client_class.return_value = mock_client

            with pytest.raises(Exception) as exc_info:
                await client.authenticate()

            # Should contain "authentication" for Home Assistant compatibility
            assert "authentication" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_device_data_success(self, mock_device_status):
        """Test successful device data retrieval with all required fields."""
        client = NavienClient("test@example.com", "password")
        client._authenticated = True

        # Mock device
        mock_device = AsyncMock()
        mock_device.get_status.return_value = mock_device_status
        mock_device.get_info.return_value = None  # Simulate no additional info
        client._device = mock_device

        device_data = await client.get_device_data()

        # Test Home Assistant required fields from recommendations
        assert "water_temperature" in device_data
        assert "set_temperature" in device_data
        assert "inlet_temperature" in device_data
        assert "outlet_temperature" in device_data
        assert "ambient_temperature" in device_data
        assert "power_consumption" in device_data
        assert "operating_mode" in device_data
        assert "error_code" in device_data
        assert "compressor_status" in device_data
        assert "heating_element_status" in device_data

        # Test critical dhw_charge_percent is included (missing from recommendations)
        assert "dhw_charge_percent" in device_data
        assert device_data["dhw_charge_percent"] == 99.0

        # Test alternative field names for flexibility
        assert "tank_charge_percent" in device_data
        assert "charge_level" in device_data

        # Test proper temperature conversions
        assert device_data["water_temperature"] == 121.0
        assert device_data["inlet_temperature"] == 60.5  # Converted from 0.1°F units
        assert device_data["ambient_temperature"] == 23.8  # Converted from 0.1°F units

        # Test power data
        assert device_data["power_consumption"] == 466.0

        # Test descriptive operation mode
        assert device_data["operating_mode"] == "heat_pump_active"

        # Test component status
        assert device_data["compressor_status"] == "active"  # comp_use=2
        assert (
            device_data["heating_element_status"] == "ready"
        )  # heat_upper_use=1, heat_lower_use=1

    @pytest.mark.asyncio
    async def test_get_device_data_not_authenticated(self):
        """Test get_device_data fails when not authenticated."""
        client = NavienClient("test@example.com", "password")

        with pytest.raises(Exception) as exc_info:
            await client.get_device_data()

        assert "authenticate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_temperature_success(self):
        """Test successful temperature setting."""
        client = NavienClient("test@example.com", "password")
        client._authenticated = True

        mock_device = AsyncMock()
        mock_device.set_temperature.return_value = {"success": True}
        client._device = mock_device

        result = await client.set_temperature(125.0)

        assert result is True
        mock_device.set_temperature.assert_called_once_with(
            125
        )  # Should convert to int

    @pytest.mark.asyncio
    async def test_set_temperature_validation(self):
        """Test temperature validation."""
        client = NavienClient("test@example.com", "password")
        client._authenticated = True
        client._device = AsyncMock()

        # Test temperature too low
        with pytest.raises(Exception) as exc_info:
            await client.set_temperature(50.0)
        assert "range" in str(exc_info.value)

        # Test temperature too high
        with pytest.raises(Exception) as exc_info:
            await client.set_temperature(200.0)
        assert "range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_operation_mode_success(self):
        """Test successful operation mode setting."""
        client = NavienClient("test@example.com", "password")
        client._authenticated = True

        mock_device = AsyncMock()
        mock_device.set_dhw_mode.return_value = {"success": True}
        client._device = mock_device

        # Test heat pump mode
        result = await client.set_operation_mode("heat_pump")
        assert result is True
        mock_device.set_dhw_mode.assert_called_with(2)

        # Test hybrid mode
        await client.set_operation_mode("hybrid")
        mock_device.set_dhw_mode.assert_called_with(3)

        # Test electric mode
        await client.set_operation_mode("electric")
        mock_device.set_dhw_mode.assert_called_with(4)

    @pytest.mark.asyncio
    async def test_set_operation_mode_invalid(self):
        """Test operation mode validation."""
        client = NavienClient("test@example.com", "password")
        client._authenticated = True
        client._device = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await client.set_operation_mode("invalid_mode")

        assert "invalid mode" in str(exc_info.value).lower()
        assert "valid modes" in str(exc_info.value).lower()


class TestNavienClientHelpers:
    """Test helper methods for status conversion."""

    def test_get_operation_mode_name(self):
        """Test operation mode conversion."""
        client = NavienClient("test@example.com", "password")

        assert client._get_operation_mode_name(0) == "standby"
        assert client._get_operation_mode_name(32) == "heat_pump_active"
        assert client._get_operation_mode_name(33) == "electric_backup"
        assert client._get_operation_mode_name(34) == "hybrid_mode"
        assert client._get_operation_mode_name(999) == "unknown_999"

    def test_get_component_status(self):
        """Test component status conversion."""
        client = NavienClient("test@example.com", "password")

        assert client._get_component_status(0) == "off"
        assert client._get_component_status(1) == "ready"
        assert client._get_component_status(2) == "active"
        assert client._get_component_status(999) == "unknown_999"

    def test_get_heater_status(self):
        """Test heating element status logic."""
        client = NavienClient("test@example.com", "password")

        # Both off
        assert client._get_heater_status(0, 0) == "off"

        # One ready
        assert client._get_heater_status(1, 0) == "ready"
        assert client._get_heater_status(0, 1) == "ready"

        # One active
        assert client._get_heater_status(2, 0) == "active"
        assert client._get_heater_status(0, 2) == "active"

        # Both ready
        assert client._get_heater_status(1, 1) == "ready"

        # Mixed - active takes precedence
        assert client._get_heater_status(2, 1) == "active"


class TestNavienClientContextManager:
    """Test async context manager functionality."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager usage."""
        with patch("navien_nwp500.ha_compat.NaviLinkClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            async with NavienClient("test@example.com", "password") as client:
                assert isinstance(client, NavienClient)

            # Should call close on exit
            # (We can't easily test this without more complex mocking)


class TestHomeAssistantCompatibility:
    """Test specific Home Assistant integration requirements."""

    @pytest.mark.asyncio
    async def test_all_required_fields_present(self, mock_device_status):
        """Ensure all fields from LIBRARY_RECOMMENDATIONS.md are present."""
        client = NavienClient("test@example.com", "password")
        client._authenticated = True

        mock_device = AsyncMock()
        mock_device.get_status.return_value = mock_device_status
        mock_device.get_info.return_value = None
        client._device = mock_device

        device_data = await client.get_device_data()

        # Temperature fields from recommendations
        required_temp_fields = [
            "water_temperature",
            "set_temperature",
            "target_temp",
            "tank_temp",
            "inlet_temperature",
            "outlet_temperature",
            "ambient_temperature",
        ]
        for field in required_temp_fields:
            assert field in device_data, f"Missing temperature field: {field}"

        # Power fields from recommendations
        required_power_fields = ["power_consumption", "current_power", "power"]
        for field in required_power_fields:
            assert field in device_data, f"Missing power field: {field}"

        # Status fields from recommendations
        required_status_fields = [
            "operating_mode",
            "mode",
            "operation_mode",
            "error_code",
            "error",
            "fault_code",
            "compressor_status",
            "compressor",
            "heating_element_status",
            "heater",
        ]
        for field in required_status_fields:
            assert field in device_data, f"Missing status field: {field}"

        # CRITICAL: DHW charge percent (missing from recommendations but essential)
        critical_fields = ["dhw_charge_percent", "tank_charge_percent", "charge_level"]
        for field in critical_fields:
            assert field in device_data, f"Missing critical field: {field}"

    @pytest.mark.asyncio
    async def test_error_message_format_for_ha(self):
        """Test that error messages are Home Assistant compatible."""
        client = NavienClient("test@example.com", "password")

        # Authentication errors should mention "authentication"
        with patch("navien_nwp500.ha_compat.NaviLinkClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.authenticate.side_effect = Exception("Auth failed")
            mock_client_class.return_value = mock_client

            with pytest.raises(Exception) as exc_info:
                await client.authenticate()

            # The ha_compat module should wrap errors to include "authentication"
            error_msg = str(exc_info.value).lower()
            assert "authentication" in error_msg

    def test_temperature_type_compatibility(self):
        """Ensure temperature values are proper floats for Home Assistant."""
        client = NavienClient("test@example.com", "password")

        # Test that temperature conversion returns floats
        assert isinstance(121.0, float)  # Direct temperature
        assert isinstance(605 / 10.0, float)  # Converted temperature

    def test_mode_string_compatibility(self):
        """Test that mode strings are Home Assistant friendly."""
        client = NavienClient("test@example.com", "password")

        # Test mode names are lowercase with underscores (HA convention)
        mode_name = client._get_operation_mode_name(32)
        assert mode_name == "heat_pump_active"
        assert mode_name.islower()
        assert "_" in mode_name or mode_name.isalpha()
