"""
Simple tests to validate basic functionality.
"""

def test_import():
    """Test that the package can be imported correctly."""
    import navien_nwp500
    assert hasattr(navien_nwp500, '__version__')
    assert hasattr(navien_nwp500, 'NaviLinkClient')
    assert hasattr(navien_nwp500, 'NaviLinkConfig')


def test_version():
    """Test version information is available."""
    from navien_nwp500 import __author__, __version__
    assert isinstance(__version__, str)
    assert isinstance(__author__, str)
    assert len(__version__) > 0
    assert len(__author__) > 0


def test_exceptions_import():
    """Test that all exceptions can be imported."""
    from navien_nwp500 import (
        APIError,
        AuthenticationError,
        CommunicationError,
        DeviceError,
        DeviceOfflineError,
        MQTTError,
        NaviLinkError,
        WebSocketError,
    )

    # Test basic exception hierarchy
    assert issubclass(AuthenticationError, NaviLinkError)
    assert issubclass(DeviceError, NaviLinkError)
    assert issubclass(CommunicationError, NaviLinkError)
    assert issubclass(DeviceOfflineError, DeviceError)


def test_config_creation():
    """Test basic config creation."""
    from navien_nwp500.config import LogLevel, NaviLinkConfig
    
    config = NaviLinkConfig(
        email="test@example.com",
        password="test_pass"
    )
    
    assert config.email == "test@example.com"
    assert config.password == "test_pass"
    assert config.log_level == LogLevel.INFO  # Default


def test_client_creation():
    """Test basic client creation."""
    from navien_nwp500 import NaviLinkClient, NaviLinkConfig
    
    config = NaviLinkConfig(
        email="test@example.com", 
        password="test_pass"
    )
    
    client = NaviLinkClient(config=config)
    assert client.config == config
    # Just check the client was created successfully
    assert client is not None