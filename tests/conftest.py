"""
Pytest configuration and fixtures for the navien_nwp500 test suite.
"""
import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from navien_nwp500 import NaviLinkClient, NaviLinkConfig, NaviLinkDevice
from navien_nwp500.models import DeviceInfo, DeviceStatus


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
        email="test@example.com",
        password="test_password",
        log_level="DEBUG"
    )


@pytest.fixture
def mock_device_data() -> Dict[str, Any]:
    """Sample device data for testing."""
    return {
        "device_id": "TEST123456",
        "device_type": 52,
        "mac_address": "AA:BB:CC:DD:EE:FF",
        "device_name": "NWP500 Test",
        "model_name": "NWP500",
        "device_connected": 1,
        "group_id": "test_group",
        "location": "Test Location"
    }


@pytest.fixture
def mock_device_status() -> Dict[str, Any]:
    """Sample device status data for testing."""
    return {
        "dhw_charge_per": 95,
        "dhw_temperature": 121,
        "dhw_temperature_setting": 121,
        "operation_mode": 32,
        "comp_use": 2,
        "heat_upper_use": 1,
        "heat_lower_use": 1,
        "eva_fan_use": 2,
        "dhw_use": 0,
        "error_code": 0,
        "sub_error_code": 0,
        "current_inst_power": 466,
        "tank_upper_temperature": 605,  # 60.5°F
        "tank_lower_temperature": 611,  # 61.1°F
        "discharge_temperature": 761,   # 76.1°F
        "ambient_temperature": 238,     # 23.8°F
        "outside_temperature": 0,
        "wifi_rssi": -45,
        "device_connected": 1
    }


@pytest.fixture
def mock_device_info(mock_device_data) -> DeviceInfo:
    """Create a mock DeviceInfo object."""
    return DeviceInfo(**mock_device_data)


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
            "region": "us-east-1"
        }
    }
    
    # Mock device list response
    device_response = AsyncMock()
    device_response.status = 200
    device_response.json.return_value = {
        "result": "success",
        "data": {
            "device_list": [{
                "device_id": "TEST123456",
                "device_type": 52,
                "mac_address": "AA:BB:CC:DD:EE:FF",
                "device_name": "NWP500 Test",
                "model_name": "NWP500",
                "device_connected": 1,
                "group_id": "test_group"
            }]
        }
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
        help="run integration tests"
    )