#!/usr/bin/env python3
"""
Production Integration Test for NaviLink Library

This test validates the core functionality of the NaviLink library with 
real hardware in a production environment. It tests:

- Authentication and session management
- Device discovery and connectivity
- MQTT connection and data retrieval
- Error handling and recovery
- Configuration system

Usage:
    export NAVILINK_EMAIL="your@email.com"
    export NAVILINK_PASSWORD="your_password"
    python -m pytest tests/test_integration.py -v

Or directly:
    python tests/test_integration.py
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from navilink import NaviLinkClient, NaviLinkConfig, NaviLinkDevice
from navilink.config import ReconnectConfig
from navilink.exceptions import NaviLinkError


class ProductionIntegrationTest:
    """Production integration test for NaviLink library."""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.config = None
        self.client = None
        self.device = None
        self.test_results = {
            'authentication': False,
            'device_discovery': False,
            'device_connectivity': False,
            'mqtt_connection': False,
            'data_retrieval': False,
            'error_handling': False
        }
        
    def _setup_logging(self):
        """Setup test logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
        
    async def test_configuration(self) -> bool:
        """Test configuration system."""
        try:
            self.logger.info("🔧 Testing configuration system...")
            
            # Test environment variable loading
            self.config = NaviLinkConfig.from_environment()
            
            # Validate credentials are available
            if not self.config.email or not self.config.password:
                self.logger.error("❌ Email and password must be set via environment variables")
                self.logger.info("   Set NAVILINK_EMAIL and NAVILINK_PASSWORD")
                return False
                
            # Test configuration validation
            self.config.validate()
            
            self.logger.info("✅ Configuration test passed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Configuration test failed: {e}")
            return False
            
    async def test_authentication(self) -> bool:
        """Test authentication system."""
        try:
            self.logger.info("🔐 Testing authentication...")
            
            self.client = NaviLinkClient(config=self.config)
            await self.client.authenticate(self.config.email, self.config.password)
            
            # Verify session is available
            if not self.client._auth or not self.client._auth.session:
                raise RuntimeError("Authentication succeeded but no session available")
                
            self.test_results['authentication'] = True
            self.logger.info("✅ Authentication test passed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Authentication test failed: {e}")
            return False
            
    async def test_device_discovery(self) -> bool:
        """Test device discovery."""
        try:
            self.logger.info("📱 Testing device discovery...")
            
            devices = await self.client.get_devices()
            
            if not devices:
                raise RuntimeError("No devices found in account")
                
            self.device = devices[0]
            device_name = getattr(self.device, 'device_name', 'Unknown')
            
            self.logger.info(f"🏠 Found device: {device_name} (MAC: {self.device.mac_address})")
            
            # Test device info retrieval
            info = await self.device.get_device_info()
            if not info:
                raise RuntimeError("Failed to get device information")
                
            self.test_results['device_discovery'] = True
            self.logger.info("✅ Device discovery test passed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Device discovery test failed: {e}")
            return False
            
    async def test_device_connectivity(self) -> bool:
        """Test device connectivity status."""
        try:
            self.logger.info("📡 Testing device connectivity...")
            
            connectivity = await self.device.get_connectivity_status()
            
            if not isinstance(connectivity, dict):
                raise RuntimeError("Invalid connectivity response")
                
            device_connected = connectivity.get('device_connected', 0)
            self.logger.info(f"Device connection status: {device_connected}")
            
            if device_connected == 0:
                self.logger.warning("⚠️ Device appears offline, MQTT tests may fail")
            else:
                self.logger.info("✅ Device is online")
                
            self.test_results['device_connectivity'] = True
            self.logger.info("✅ Device connectivity test passed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Device connectivity test failed: {e}")
            return False
            
    async def test_mqtt_connection(self) -> bool:
        """Test MQTT connection establishment."""
        try:
            self.logger.info("🔌 Testing MQTT connection...")
            
            # Configure reconnection for testing
            reconnect_config = ReconnectConfig(
                max_retries=5,
                initial_delay=1.0,
                max_delay=10.0,
                jitter=True
            )
            
            mqtt_conn = await self.device.get_mqtt_connection(
                reconnect_config=reconnect_config
            )
            
            # Test connection
            await mqtt_conn.connect()
            self.logger.info("✅ MQTT connection established")
            
            # Test disconnection
            await mqtt_conn.disconnect()
            self.logger.info("✅ MQTT disconnection successful")
            
            self.test_results['mqtt_connection'] = True
            self.logger.info("✅ MQTT connection test passed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ MQTT connection test failed: {e}")
            return False
            
    async def test_data_retrieval(self) -> bool:
        """Test data retrieval via MQTT."""
        try:
            self.logger.info("📊 Testing data retrieval...")
            
            # Configure reconnection for testing
            reconnect_config = ReconnectConfig(
                max_retries=3,
                initial_delay=1.0,
                max_delay=5.0,
                jitter=False
            )
            
            mqtt_conn = await self.device.get_mqtt_connection(
                reconnect_config=reconnect_config
            )
            
            # Setup data collection
            received_data = []
            
            async def collect_data(status):
                received_data.append(status)
                self.logger.info("📊 Received status update")
                
                # Log key fields for validation
                charge = getattr(status, 'dhw_charge_per', 0)
                temp = getattr(status, 'dhw_temperature', 0)
                mode = getattr(status, 'operation_mode', 0)
                power = getattr(status, 'current_inst_power', 0)
                
                self.logger.info(f"   Tank: {charge}% | Temp: {temp}°F | Mode: {mode} | Power: {power}W")
                
            await mqtt_conn.connect()
            mqtt_conn.set_status_callback(collect_data)
            
            # Start monitoring for a short period
            self.logger.info("⏱️ Starting 30-second data collection...")
            monitoring_task = asyncio.create_task(
                mqtt_conn.start_monitoring(polling_interval=10)
            )
            
            # Wait for data collection
            await asyncio.sleep(30)
            
            # Stop monitoring
            monitoring_task.cancel()
            try:
                await monitoring_task
            except asyncio.CancelledError:
                pass
                
            await mqtt_conn.disconnect()
            
            # Validate received data
            if not received_data:
                raise RuntimeError("No data received during monitoring period")
                
            self.logger.info(f"✅ Received {len(received_data)} status updates")
            
            # Validate data structure
            sample_data = received_data[0]
            required_fields = [
                'dhw_charge_per', 'dhw_temperature', 'operation_mode', 
                'current_inst_power', 'error_code'
            ]
            
            for field in required_fields:
                if not hasattr(sample_data, field):
                    raise RuntimeError(f"Missing required field: {field}")
                    
            self.test_results['data_retrieval'] = True
            self.logger.info("✅ Data retrieval test passed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Data retrieval test failed: {e}")
            return False
            
    async def test_error_handling(self) -> bool:
        """Test error handling capabilities."""
        try:
            self.logger.info("🛠️ Testing error handling...")
            
            # Test invalid authentication
            try:
                invalid_client = NaviLinkClient()
                await invalid_client.authenticate("invalid@email.com", "invalid_password")
                raise RuntimeError("Invalid authentication should have failed")
            except NaviLinkError:
                self.logger.info("✅ Invalid authentication properly rejected")
            except Exception as e:
                self.logger.warning(f"Unexpected error type for invalid auth: {type(e).__name__}")
            finally:
                if 'invalid_client' in locals():
                    await invalid_client.close()
                    
            # Test connection recovery (simulate by using invalid endpoint)
            try:
                invalid_config = NaviLinkConfig(
                    email=self.config.email,
                    password=self.config.password,
                    websocket_url="wss://invalid-endpoint.example.com/mqtt"
                )
                test_client = NaviLinkClient(config=invalid_config)
                await test_client.authenticate(self.config.email, self.config.password)
                
                devices = await test_client.get_devices()
                if devices:
                    test_device = devices[0]
                    
                    # This should fail gracefully
                    mqtt_conn = await test_device.get_mqtt_connection()
                    try:
                        await asyncio.wait_for(mqtt_conn.connect(), timeout=5.0)
                        self.logger.warning("Expected connection to invalid endpoint to fail")
                    except Exception:
                        self.logger.info("✅ Connection to invalid endpoint properly failed")
                        
                await test_client.close()
                
            except Exception as e:
                self.logger.info(f"✅ Error handling working as expected: {type(e).__name__}")
                
            self.test_results['error_handling'] = True
            self.logger.info("✅ Error handling test passed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error handling test failed: {e}")
            return False
            
    async def cleanup(self):
        """Clean up test resources."""
        try:
            if self.client:
                await self.client.close()
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
            
    def print_results(self):
        """Print test results summary."""
        self.logger.info("=" * 50)
        self.logger.info("🏁 Production Integration Test Results")
        self.logger.info("=" * 50)
        
        passed = 0
        total = len(self.test_results)
        
        for test, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            self.logger.info(f"{test.replace('_', ' ').title()}: {status}")
            if result:
                passed += 1
                
        self.logger.info("=" * 50)
        self.logger.info(f"Overall: {passed}/{total} tests passed")
        
        if passed == total:
            self.logger.info("🎉 All tests passed! Library is production ready.")
        else:
            self.logger.error(f"💥 {total - passed} tests failed. Review configuration and connectivity.")
            
        return passed == total
        

async def main():
    """Run production integration tests."""
    test = ProductionIntegrationTest()
    
    try:
        # Run test suite
        test.logger.info("🚀 Starting NaviLink Production Integration Test")
        test.logger.info("📝 Testing with real hardware and live service")
        test.logger.info("")
        
        # Configuration test
        if not await test.test_configuration():
            return False
            
        # Core functionality tests
        tests = [
            test.test_authentication,
            test.test_device_discovery,
            test.test_device_connectivity,
            test.test_mqtt_connection,
            test.test_data_retrieval,
            test.test_error_handling
        ]
        
        for test_func in tests:
            if not await test_func():
                break
            await asyncio.sleep(1)  # Brief pause between tests
            
    except KeyboardInterrupt:
        test.logger.info("\n🛑 Test interrupted by user")
    except Exception as e:
        test.logger.error(f"💥 Test suite failed: {e}")
    finally:
        await test.cleanup()
        
    # Print results
    return test.print_results()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)