"""
Pytest configuration and fixtures for the navien_nwp500 test suite.
"""

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from navien_nwp500 import NaviLinkClient, NaviLinkConfig, NaviLinkDevice
from navien_nwp500.models import DeviceFeatures, DeviceInfo, DeviceStatus


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config() -> NaviLinkConfig:
    """Create a mock configuration for testing."""
    return NaviLinkConfig(
        email="test@example.com", password="test_password", log_level="DEBUG"
    )


@pytest.fixture
def mock_device_data() -> Dict[str, Any]:
    """Sample device data for testing."""
    return {
        "device_type": 52,
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "additional_value": "test_additional",
        "controller_serial_number": "TEST123456",
    }


@pytest.fixture
def mock_device_status() -> Dict[str, Any]:
    """Sample device status data for testing."""
    return {
        "command": 16777219,
        "outside_temperature": 0,
        "special_function_status": 0,
        "did_reload": 0,
        "error_code": 0,
        "sub_error_code": 0,
        "operation_mode": 32,
        "operation_busy": 2,
        "freeze_protection_use": 0,
        "dhw_use": 0,
        "dhw_use_sustained": 0,
        "dhw_temperature": 121,
        "dhw_temperature_setting": 121,
        "program_reservation_use": 0,
        "smart_diagnostic": 0,
        "fault_status1": 0,
        "fault_status2": 0,
        "wifi_rssi": -45,
        "eco_use": 0,
        "dhw_target_temperature_setting": 121,
        "tank_upper_temperature": 605,  # 60.5°F
        "tank_lower_temperature": 611,  # 61.1°F
        "discharge_temperature": 761,  # 76.1°F
        "suction_temperature": 400,
        "evaporator_temperature": 600,
        "ambient_temperature": 238,  # 23.8°F
        "target_super_heat": 10,
        "comp_use": 2,
        "eev_use": 50,
        "eva_fan_use": 2,
        "current_inst_power": 466,
        "shut_off_valve_use": 0,
        "con_ovr_sensor_use": 0,
        "wtr_ovr_sensor_use": 0,
        "dhw_charge_per": 95,
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
        "heat_upper_use": 1,
        "heat_lower_use": 1,
        "device_connected": 1,
    }


@pytest.fixture
def mock_device_features() -> DeviceFeatures:
    """Create a mock DeviceFeatures object for testing."""
    return DeviceFeatures(
        country_code=1,
        model_type_code=52,
        control_type_code=1,
        volume_code=50,
        controller_sw_version=100,
        panel_sw_version=100,
        wifi_sw_version=100,
        controller_sw_code=1,
        panel_sw_code=1,
        wifi_sw_code=1,
        controller_serial_number="TEST123456",
        power_use=1,
        holiday_use=1,
        program_reservation_use=1,
        dhw_use=1,
        dhw_temperature_setting_use=1,
        dhw_temperature_min=70,
        dhw_temperature_max=140,
        smart_diagnostic_use=1,
        wifi_rssi_use=1,
        temperature_type=1,
        temp_formula_type=1,
        energy_usage_use=1,
        freeze_protection_use=1,
        freeze_protection_temp_min=40,
        freeze_protection_temp_max=80,
        mixing_value_use=1,
        dr_setting_use=1,
        anti_legionella_setting_use=1,
        hpwh_use=1,
        dhw_refill_use=1,
        eco_use=1,
        electric_use=1,
        heatpump_use=1,
        energy_saver_use=1,
        high_demand_use=1,
    )


@pytest.fixture
def mock_device_info(mock_device_data, mock_device_features) -> DeviceInfo:
    """Create a mock DeviceInfo object."""
    return DeviceInfo(features=mock_device_features, **mock_device_data)


@pytest.fixture
def mock_device_status_obj(mock_device_status) -> DeviceStatus:
    """Create a mock DeviceStatus object."""
    return DeviceStatus(**mock_device_status)


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for HTTP requests."""
    session = AsyncMock()

    # Mock successful authentication response
    auth_response = AsyncMock()
    auth_response.status = 200
    auth_response.json.return_value = {
        "result": "success",
        "data": {
            "user_id": "test@example.com",
            "session_id": "mock_session_123",
            "access_key_id": "MOCK_ACCESS_KEY",
            "secret_access_key": "MOCK_SECRET_KEY",
            "session_token": "MOCK_SESSION_TOKEN",
            "region": "us-east-1",
        },
    }

    # Mock device list response
    device_response = AsyncMock()
    device_response.status = 200
    device_response.json.return_value = {
        "result": "success",
        "data": {
            "device_list": [
                {
                    "device_id": "TEST123456",
                    "device_type": 52,
                    "mac_address": "AA:BB:CC:DD:EE:FF",
                    "device_name": "NWP500 Test",
                    "model_name": "NWP500",
                    "device_connected": 1,
                    "group_id": "test_group",
                }
            ]
        },
    }

    session.post.return_value.__aenter__.return_value = auth_response
    session.get.return_value.__aenter__.return_value = device_response

    return session


@pytest.fixture
def mock_client(mock_config, mock_aiohttp_session) -> NaviLinkClient:
    """Create a mock NaviLinkClient."""
    client = NaviLinkClient(config=mock_config)
    client._session = mock_aiohttp_session
    return client


@pytest.fixture
def mock_device(mock_client, mock_device_info) -> NaviLinkDevice:
    """Create a mock NaviLinkDevice."""
    return NaviLinkDevice(client=mock_client, device_info=mock_device_info)


# Skip integration tests by default unless --integration flag is used
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--integration"):
        # --integration given in cli: do not skip integration tests
        return
    skip_integration = pytest.mark.skip(reason="need --integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run integration tests",
    )
