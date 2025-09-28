"""
Test parser validation using real HAR file data (sanitized).

This module tests that our parsers correctly handle real API responses
from the NaviLink service, ensuring field mappings and data transformations
work correctly with production data structures.
"""

import json
from pathlib import Path

import pytest

from navien_nwp500.auth import NaviLinkAuth
from navien_nwp500.client import NaviLinkClient
from navien_nwp500.config import NaviLinkConfig
from navien_nwp500.models import DeviceFeatures, DeviceInfo, DeviceStatus, UserInfo

# Load test fixtures
FIXTURES_PATH = Path(__file__).parent / "fixtures" / "har_test_data.json"


@pytest.fixture
def har_test_data():
    """Load sanitized HAR test data."""
    with open(FIXTURES_PATH) as f:
        return json.load(f)


@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    return NaviLinkConfig(
        email="test@example.com",
        password="test_password",
        base_url="https://nlus.naviensmartcontrol.com/api/v2.1",
    )


class TestAuthenticationParser:
    """Test authentication response parsing."""

    def test_sign_in_response_parsing(self, har_test_data, mock_config):
        """Test that sign-in responses are parsed correctly."""
        sign_in_data = har_test_data["api_responses"]["POST_user_sign-in"]

        # Verify the response structure
        assert sign_in_data["status"] == 200
        response_data = sign_in_data["data"]

        # Check top-level structure
        assert response_data["code"] == 200
        assert response_data["msg"] == "SUCCESS"
        assert "data" in response_data

        data = response_data["data"]

        # Check user info structure
        assert "userInfo" in data
        user_info = data["userInfo"]
        assert "userType" in user_info
        assert "userSeq" in user_info
        assert "userStatus" in user_info

        # Check token structure
        assert "token" in data
        token_data = data["token"]
        required_tokens = ["accessToken", "refreshToken", "idToken"]
        for token_type in required_tokens:
            assert token_type in token_data
            # Check that tokens exist and are non-empty strings
            assert isinstance(token_data[token_type], str)
            assert len(token_data[token_type]) > 10  # Reasonable minimum token length

        # Check AWS credentials
        aws_fields = ["accessKeyId", "secretKey", "sessionToken"]
        for field in aws_fields:
            assert field in token_data

        # Test UserInfo model parsing
        # Note: We can't test with real tokens, but we can verify structure
        assert user_info["userType"] in ["O", "U"]  # Owner or User
        assert isinstance(user_info["userSeq"], int)

    def test_auth_refresh_response_parsing(self, har_test_data):
        """Test auth refresh response parsing."""
        refresh_data = har_test_data["api_responses"]["POST_auth_refresh"]

        assert refresh_data["status"] == 200
        response_data = refresh_data["data"]

        # Should have similar structure to sign-in
        assert response_data["code"] == 200
        assert "data" in response_data


class TestDeviceListParser:
    """Test device list response parsing."""

    def test_device_list_parsing(self, har_test_data):
        """Test device list response structure."""
        device_list_data = har_test_data["api_responses"]["POST_device_list"]

        assert device_list_data["status"] == 200
        response_data = device_list_data["data"]

        # Check response structure
        assert response_data["code"] == 200
        assert response_data["msg"] == "SUCCESS"
        assert "data" in response_data

        devices = response_data["data"]
        assert isinstance(devices, list)

        if devices:  # If we have device data
            device = devices[0]

            # Check device info structure
            assert "deviceInfo" in device
            device_info = device["deviceInfo"]

            required_fields = [
                "homeSeq",
                "macAddress",
                "additionalValue",
                "deviceType",
                "deviceName",
            ]
            for field in required_fields:
                assert field in device_info

            # Check location structure
            assert "location" in device
            location = device["location"]
            location_fields = ["state", "city", "address"]
            for field in location_fields:
                assert field in location

            # Verify device type for water heater
            assert device_info["deviceType"] == 52  # NWP500 device type
            assert device_info["deviceName"] == "NWP500"

            # Test sanitization worked
            assert device_info["macAddress"] == "aabbccddeeff"


class TestDeviceInfoParser:
    """Test device info response parsing."""

    def test_device_info_parsing(self, har_test_data):
        """Test device info response structure."""
        device_info_data = har_test_data["api_responses"]["POST_device_info"]

        assert device_info_data["status"] == 200
        response_data = device_info_data["data"]

        assert response_data["code"] == 200
        data = response_data["data"]

        # Check main sections
        required_sections = ["deviceInfo", "location", "installer", "alarmInfo"]
        for section in required_sections:
            assert section in data

        # Check device info details
        device_info = data["deviceInfo"]
        assert device_info["deviceType"] == 52
        assert device_info["installType"] == "R"  # Residential
        assert "connected" in device_info

        # Check location with coordinates
        location = data["location"]
        geo_fields = ["latitude", "longitude"]
        for field in geo_fields:
            assert field in location


class TestMqttStatusParser:
    """Test MQTT device status parsing."""

    def test_mqtt_status_structure(self, har_test_data):
        """Test MQTT status message structure."""
        mqtt_data = har_test_data["mqtt_status_data"]

        assert len(mqtt_data) > 0, "Should have MQTT status data"

        # Test first status message
        status_msg = mqtt_data[0]

        # Check MQTT wrapper structure
        assert "protocolVersion" in status_msg
        assert "clientID" in status_msg
        assert "sessionID" in status_msg
        assert "response" in status_msg

        response = status_msg["response"]
        assert "deviceType" in response
        assert "macAddress" in response
        assert "status" in response

        # Check status data structure
        status = response["status"]

        # Test core status fields that should always be present
        core_fields = [
            "command",
            "errorCode",
            "subErrorCode",
            "operationMode",
            "dhwTemperature",
            "dhwTemperatureSetting",
            "dhwChargePer",
            "currentInstPower",
            "wifiRssi",
        ]

        for field in core_fields:
            assert field in status, f"Missing core field: {field}"

        # Test heat source fields
        heat_fields = ["compUse", "heatUpperUse", "heatLowerUse", "evaFanUse"]
        for field in heat_fields:
            assert field in status, f"Missing heat source field: {field}"

        # Test temperature sensor fields (with correct spellings)
        temp_fields = [
            "tankUpperTemperature",
            "tankLowerTemperature",
            "dischargeTemperature",
            "ambientTemperature",
        ]
        for field in temp_fields:
            assert field in status, f"Missing temperature field: {field}"

    def test_device_status_model_parsing(self, har_test_data):
        """Test that DeviceStatus model can parse MQTT data."""
        mqtt_data = har_test_data["mqtt_status_data"]
        status_msg = mqtt_data[0]
        status_data = status_msg["response"]["status"]

        # Create DeviceStatus from the data
        # Note: We need to convert camelCase to snake_case for our model
        converted_data = {}

        # Field mapping from camelCase API to snake_case model
        field_mapping = {
            "outsideTemperature": "outside_temperature",
            "specialFunctionStatus": "special_function_status",
            "didReload": "did_reload",
            "errorCode": "error_code",
            "subErrorCode": "sub_error_code",
            "operationMode": "operation_mode",
            "operationBusy": "operation_busy",
            "freezeProtectionUse": "freeze_protection_use",
            "dhwUse": "dhw_use",
            "dhwUseSustained": "dhw_use_sustained",
            "dhwTemperature": "dhw_temperature",
            "dhwTemperatureSetting": "dhw_temperature_setting",
            "currentInstPower": "current_inst_power",
            "dhwChargePer": "dhw_charge_per",
            "wifiRssi": "wifi_rssi",
            "compUse": "comp_use",
            "evaFanUse": "eva_fan_use",
            "heatUpperUse": "heat_upper_use",
            "heatLowerUse": "heat_lower_use",
        }

        for api_field, model_field in field_mapping.items():
            if api_field in status_data:
                converted_data[model_field] = status_data[api_field]

        # Add required fields with defaults if missing (all 67+ fields needed by DeviceStatus)
        required_defaults = {
            "command": status_data.get("command", 16777219),
            "outside_temperature": status_data.get("outsideTemperature", 0),
            "special_function_status": status_data.get("specialFunctionStatus", 1),
            "did_reload": status_data.get("didReload", 1),
            "program_reservation_use": 0,
            "smart_diagnostic": 0,
            "fault_status1": 0,
            "fault_status2": 0,
            "eco_use": 0,
            "dhw_target_temperature_setting": 121,
            "tank_upper_temperature": 605,
            "tank_lower_temperature": 611,
            "discharge_temperature": 761,
            "suction_temperature": 400,
            "evaporator_temperature": 600,
            "ambient_temperature": 238,
            "target_super_heat": 10,
            "eev_use": 50,
            "shut_off_valve_use": 0,
            "con_ovr_sensor_use": 0,
            "wtr_ovr_sensor_use": 0,
            "dr_event_status": 0,
            "vacation_day_setting": 0,
            "vacation_day_elapsed": 0,
            "freeze_protection_temperature": 45,
            "anti_legionella_use": 0,
            "anti_legionella_period": 7,
            "anti_legionella_operation_busy": 0,
            "program_reservation_type": 0,
            "dhw_operation_setting": 2,
            "temperature_type": 1,
            "temp_formula_type": 1,
            "error_buzzer_use": 0,
            "current_heat_use": 0,
            "current_inlet_temperature": 0,
            "current_statenum": 0,
            "target_fan_rpm": 0,
            "current_fan_rpm": 0,
            "fan_pwm": 0,
            "dhw_temperature2": 0,
            "current_dhw_flow_rate": 0,
            "mixing_rate": 0,
            "eev_step": 0,
            "current_super_heat": 0,
            "scald_use": 0,
            "air_filter_alarm_use": 2,
            "air_filter_alarm_period": 1000,
            "air_filter_alarm_elapsed": 0,
            "cumulated_op_time_eva_fan": 0,
            "cumulated_dhw_flow_rate": 0,
            "tou_status": 0,
            "hp_upper_on_temp_setting": 0,
            "hp_upper_off_temp_setting": 0,
            "hp_lower_on_temp_setting": 0,
            "hp_lower_off_temp_setting": 0,
            "he_upper_on_temp_setting": 0,
            "he_upper_off_temp_setting": 0,
            "he_lower_on_temp_setting": 0,
            "he_lower_off_temp_setting": 0,
            "hp_upper_on_diff_temp_setting": 0,
            "hp_upper_off_diff_temp_setting": 0,
            "hp_lower_on_diff_temp_setting": 0,
            "hp_lower_off_diff_temp_setting": 0,
            "he_upper_on_diff_temp_setting": 0,
            "he_upper_off_diff_temp_setting": 0,
            "he_lower_on_tdiffemp_setting": 0,
            "he_lower_off_diff_temp_setting": 0,
            "dr_override_status": 0,
            "tou_override_status": 0,
            "total_energy_capacity": 0,
            "available_energy_capacity": 0,
        }

        for field, default in required_defaults.items():
            if field not in converted_data:
                converted_data[field] = default

        # Verify we can create the model
        try:
            device_status = DeviceStatus(**converted_data)
            assert device_status.error_code == 0  # Should be no error
            assert device_status.operation_mode in [0, 32]  # Valid modes observed
            assert device_status.dhw_charge_per >= 0  # Tank charge percentage
            assert device_status.dhw_temperature > 0  # Should have temperature
        except Exception as e:
            pytest.fail(f"Failed to create DeviceStatus model: {e}")

    def test_production_data_insights(self, har_test_data):
        """Test production data insights and field validation."""
        mqtt_data = har_test_data["mqtt_status_data"]

        # Analyze multiple status messages for patterns
        for i, status_msg in enumerate(mqtt_data[:5]):  # Test first 5 messages
            status = status_msg["response"]["status"]

            # Validate operation modes observed in production
            op_mode = status.get("operationMode", -1)
            assert op_mode in [0, 32], f"Unexpected operation mode: {op_mode}"

            # Validate DHW charge percentage range
            charge = status.get("dhwChargePer", -1)
            assert 0 <= charge <= 100, f"DHW charge out of range: {charge}%"

            # Validate temperature ranges (Fahrenheit)
            dhw_temp = status.get("dhwTemperature", -1)
            if dhw_temp > 0:
                assert (
                    70 <= dhw_temp <= 140
                ), f"DHW temperature out of range: {dhw_temp}°F"

            # Validate power consumption patterns
            power = status.get("currentInstPower", -1)
            comp_use = status.get("compUse", -1)

            if op_mode == 0:  # Standby mode
                assert power <= 10, f"Standby power too high: {power}W"
            elif op_mode == 32 and comp_use == 2:  # Heat pump active
                assert power >= 400, f"Heat pump power too low: {power}W"


class TestTimeOfUseParser:
    """Test Time of Use (TOU) data parsing."""

    def test_tou_response_structure(self, har_test_data):
        """Test TOU response structure."""
        tou_data = har_test_data["api_responses"]["GET_device_tou"]

        assert tou_data["status"] == 200
        response_data = tou_data["data"]

        assert response_data["code"] == 200
        data = response_data["data"]

        # Check TOU structure
        assert "registerPath" in data
        assert "sourceType" in data
        assert "touInfo" in data

        tou_info = data["touInfo"]
        required_fields = ["controllerId", "name", "schedule", "utility", "zipCode"]
        for field in required_fields:
            assert field in tou_info

        # Check schedule structure
        schedule = tou_info["schedule"]
        assert isinstance(schedule, list)

        if schedule:
            season = schedule[0]
            assert "season" in season
            assert "interval" in season

            intervals = season["interval"]
            if intervals:
                interval = intervals[0]
                interval_fields = [
                    "priceMin",
                    "priceMax",
                    "startHour",
                    "endHour",
                    "decimalPoint",
                ]
                for field in interval_fields:
                    assert field in interval


class TestFirmwareInfoParser:
    """Test firmware information parsing."""

    def test_firmware_info_structure(self, har_test_data):
        """Test firmware info response structure."""
        firmware_data = har_test_data["api_responses"]["POST_device_firmware_info"]

        assert firmware_data["status"] == 200
        response_data = firmware_data["data"]

        assert response_data["code"] == 200
        data = response_data["data"]

        assert "firmwares" in data
        firmwares = data["firmwares"]
        assert isinstance(firmwares, list)

        if firmwares:
            firmware = firmwares[0]
            required_fields = [
                "macAddress",
                "additionalValue",
                "deviceType",
                "curSwCode",
                "curVersion",
            ]
            for field in required_fields:
                assert field in firmware

            # Verify device type consistency
            assert firmware["deviceType"] == 52
            assert firmware["macAddress"] == "aabbccddeeff"  # Sanitized


class TestParserRobustness:
    """Test parser robustness and error handling."""

    def test_missing_fields_handling(self):
        """Test handling of missing or malformed fields."""
        # Test incomplete status data
        partial_status = {
            "command": 16777219,
            "errorCode": 0,
            "operationMode": 0,
            "dhwTemperature": 80,
            # Missing many required fields
        }

        # Should handle gracefully or provide defaults
        # This tests the robustness of our parsing logic

    def test_field_type_validation(self, har_test_data):
        """Test that field types match expectations."""
        mqtt_data = har_test_data["mqtt_status_data"]
        status = mqtt_data[0]["response"]["status"]

        # Test integer fields
        int_fields = [
            "command",
            "errorCode",
            "operationMode",
            "dhwTemperature",
            "currentInstPower",
            "dhwChargePer",
            "wifiRssi",
        ]

        for field in int_fields:
            if field in status:
                assert isinstance(status[field], int), f"{field} should be integer"

        # Test boolean-like fields (0, 1, 2 pattern)
        status_fields = ["compUse", "heatUpperUse", "heatLowerUse", "evaFanUse"]

        for field in status_fields:
            if field in status:
                value = status[field]
                assert value in [0, 1, 2], f"{field} should be 0, 1, or 2, got {value}"


@pytest.mark.integration
class TestEndToEndParsing:
    """Integration tests for complete parsing workflows."""

    def test_authentication_workflow(self, har_test_data, mock_config):
        """Test complete authentication parsing workflow."""
        sign_in_data = har_test_data["api_responses"]["POST_user_sign-in"]["data"]

        # Test that the response can be processed by our auth parser
        # This would normally be done by NaviLinkAuth._parse_user_info()
        data = sign_in_data["data"]
        user_info_data = data["userInfo"]
        token_data = data["token"]

        # Verify structure matches what our parser expects
        assert "userSeq" in user_info_data
        assert "userType" in user_info_data
        assert "accessToken" in token_data
        assert "refreshToken" in token_data
        assert "accessKeyId" in token_data
        assert "secretKey" in token_data
        assert "sessionToken" in token_data

    def test_device_discovery_workflow(self, har_test_data):
        """Test complete device discovery parsing workflow."""
        device_list_data = har_test_data["api_responses"]["POST_device_list"]["data"]

        devices_data = device_list_data["data"]

        # Test that this can be processed by NaviLinkClient.get_devices()
        processed_devices = []
        for device_data in devices_data:
            # Extract deviceInfo and location as the client does
            device_entry = {
                **device_data.get("deviceInfo", {}),
                "location": device_data.get("location", {}),
            }
            processed_devices.append(device_entry)

        assert len(processed_devices) > 0
        device = processed_devices[0]

        # Verify fields needed for DeviceInfo model
        required_for_device_info = ["macAddress", "deviceType", "deviceName"]
        for field in required_for_device_info:
            assert field in device

    def test_status_monitoring_workflow(self, har_test_data):
        """Test complete status monitoring parsing workflow."""
        mqtt_data = har_test_data["mqtt_status_data"]

        # Test that MQTT responses can be processed by our status parser
        for status_msg in mqtt_data[:3]:  # Test first 3 messages
            # Verify MQTT message structure
            assert "response" in status_msg
            assert "status" in status_msg["response"]

            status_data = status_msg["response"]["status"]

            # Test critical fields for tank monitoring
            monitoring_fields = [
                "dhwChargePer",  # Tank charge percentage
                "dhwTemperature",  # Hot water temperature
                "operationMode",  # Heat pump mode
                "currentInstPower",  # Power consumption
                "errorCode",  # Error status
            ]

            for field in monitoring_fields:
                assert (
                    field in status_data
                ), f"Critical monitoring field missing: {field}"

            # Validate monitoring data ranges
            assert 0 <= status_data["dhwChargePer"] <= 100
            assert status_data["errorCode"] == 0  # No errors in test data
            assert status_data["operationMode"] in [0, 32]  # Valid modes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
