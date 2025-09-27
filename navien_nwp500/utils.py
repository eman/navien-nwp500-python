"""
Utility functions for the NaviLink library.
"""

import hashlib
import hmac
import logging
import urllib.parse
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

def create_aws_signature(
    method: str,
    uri: str,
    query_params: Dict[str, str],
    headers: Dict[str, str],
    payload: str,
    secret_key: str,
    access_key: str,
    session_token: str,
    region: str = "us-east-1",
    service: str = "iotdata"
) -> str:
    """
    Create AWS4-HMAC-SHA256 signature for IoT requests.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        uri: Request URI
        query_params: Query parameters
        headers: Request headers
        payload: Request payload
        secret_key: AWS secret access key
        access_key: AWS access key ID
        session_token: AWS session token
        region: AWS region
        service: AWS service name
        
    Returns:
        AWS signature string
    """
    # Create canonical request
    canonical_uri = urllib.parse.quote(uri, safe='/')
    canonical_querystring = '&'.join([f"{k}={urllib.parse.quote_plus(str(v))}" 
                                     for k, v in sorted(query_params.items())])
    canonical_headers = '\n'.join([f"{k.lower()}:{v.strip()}" 
                                  for k, v in sorted(headers.items())]) + '\n'
    signed_headers = ';'.join(sorted([k.lower() for k in headers.keys()]))
    
    payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    
    canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    
    # Create string to sign
    timestamp = headers.get('X-Amz-Date', datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'))
    date_stamp = timestamp[:8]
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    algorithm = "AWS4-HMAC-SHA256"
    
    string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    
    # Calculate signature
    def sign(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()
    
    k_date = sign(('AWS4' + secret_key).encode('utf-8'), date_stamp)
    k_region = sign(k_date, region)
    k_service = sign(k_region, service)
    k_signing = sign(k_service, 'aws4_request')
    
    signature = hmac.new(k_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    
    return signature

def create_websocket_url(
    base_url: str,
    access_key: str,
    secret_key: str,
    session_token: str,
    region: str = "us-east-1"
) -> str:
    """
    Create signed WebSocket URL for AWS IoT Core.
    
    Args:
        base_url: Base WebSocket URL
        access_key: AWS access key ID
        secret_key: AWS secret access key
        session_token: AWS session token
        region: AWS region
        
    Returns:
        Signed WebSocket URL
    """
    import urllib.parse
    from datetime import datetime

    # For AWS IoT WebSocket, we need to use a different approach
    # Based on AWS IoT WebSocket connection format
    
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    date_stamp = timestamp[:8]
    
    # Parse the IoT endpoint
    parsed_url = urllib.parse.urlparse(base_url)
    host = parsed_url.netloc
    
    # AWS IoT WebSocket parameters
    query_params = {
        'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
        'X-Amz-Credential': f"{access_key}/{date_stamp}/{region}/iotdevicegateway/aws4_request",
        'X-Amz-Date': timestamp,
        'X-Amz-SignedHeaders': 'host',
        'X-Amz-Security-Token': session_token
    }
    
    # Create canonical request for AWS IoT
    headers = {'host': host}
    
    # Create signature using iotdevicegateway service
    signature = create_aws_signature(
        method='GET',
        uri='/mqtt',
        query_params=query_params,
        headers=headers,
        payload='',
        secret_key=secret_key,
        access_key=access_key,
        session_token=session_token,
        region=region,
        service='iotdevicegateway'  # Changed from iotdata to iotdevicegateway
    )
    
    query_params['X-Amz-Signature'] = signature
    
    query_string = '&'.join([f"{k}={urllib.parse.quote_plus(str(v))}" 
                            for k, v in query_params.items()])
    
    return f"{base_url}?{query_string}"

def generate_session_id() -> str:
    """Generate a unique session ID for MQTT communication."""
    import uuid
    return str(uuid.uuid4())

def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (fahrenheit - 32) * 5 / 9

def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9 / 5) + 32

def parse_device_response(response_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse device response data from MQTT messages.
    
    Args:
        response_data: Raw response data from device
        
    Returns:
        Parsed device data or None if invalid
    """
    try:
        if 'response' in response_data:
            return response_data['response']
        return response_data
    except Exception as e:
        logger.error(f"Failed to parse device response: {e}")
        return None

def validate_mac_address(mac_address: str) -> bool:
    """
    Validate MAC address format.
    
    Args:
        mac_address: MAC address string
        
    Returns:
        True if valid MAC address format
    """
    import re

    # Accept formats: 04:78:63:32:fc:a0 or 04786332fca0
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$'
    return bool(re.match(pattern, mac_address))

def normalize_mac_address(mac_address: str) -> str:
    """
    Normalize MAC address to lowercase without colons.
    
    Args:
        mac_address: MAC address in any common format
        
    Returns:
        Normalized MAC address (lowercase, no separators)
    """
    return mac_address.replace(':', '').replace('-', '').lower()