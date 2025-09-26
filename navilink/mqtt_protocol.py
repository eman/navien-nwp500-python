"""
Binary MQTT protocol implementation for NaviLink WebSocket communication.
"""

import struct
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# MQTT Packet Types
class MQTTPacketType:
    RESERVED_0 = 0
    CONNECT = 1
    CONNACK = 2
    PUBLISH = 3
    PUBACK = 4
    PUBREC = 5
    PUBREL = 6
    PUBCOMP = 7
    SUBSCRIBE = 8
    SUBACK = 9
    UNSUBSCRIBE = 10
    UNSUBACK = 11
    PINGREQ = 12
    PINGRESP = 13
    DISCONNECT = 14
    RESERVED_15 = 15

# MQTT Connect Flags
class MQTTConnectFlags:
    CLEAN_SESSION = 0x02
    WILL_FLAG = 0x04
    WILL_QOS_1 = 0x08
    WILL_QOS_2 = 0x10
    WILL_RETAIN = 0x20
    PASSWORD_FLAG = 0x40
    USERNAME_FLAG = 0x80

@dataclass
class MQTTMessage:
    """Represents an MQTT message."""
    packet_type: int
    flags: int
    payload: bytes
    packet_id: Optional[int] = None

class MQTTProtocol:
    """Binary MQTT protocol handler."""
    
    def __init__(self):
        self._packet_id = 1
        
    def _encode_remaining_length(self, length: int) -> bytes:
        """Encode remaining length according to MQTT specification."""
        encoded = bytearray()
        while True:
            encoded_byte = length % 128
            length = length // 128
            if length > 0:
                encoded_byte |= 128
            encoded.append(encoded_byte)
            if length == 0:
                break
        return bytes(encoded)
    
    def _decode_remaining_length(self, data: bytes, offset: int = 1) -> Tuple[int, int]:
        """Decode remaining length from MQTT packet."""
        multiplier = 1
        length = 0
        pos = offset
        
        while pos < len(data):
            encoded_byte = data[pos]
            length += (encoded_byte & 127) * multiplier
            if (encoded_byte & 128) == 0:
                break
            multiplier *= 128
            if multiplier > 128 * 128 * 128:
                raise ValueError("Malformed remaining length")
            pos += 1
            
        return length, pos + 1
    
    def _encode_string(self, s: str) -> bytes:
        """Encode string with length prefix for MQTT."""
        encoded = s.encode('utf-8')
        return struct.pack('!H', len(encoded)) + encoded
    
    def _decode_string(self, data: bytes, offset: int) -> Tuple[str, int]:
        """Decode string from MQTT packet."""
        if offset + 2 > len(data):
            raise ValueError("Insufficient data for string length")
        
        str_len = struct.unpack('!H', data[offset:offset+2])[0]
        if offset + 2 + str_len > len(data):
            raise ValueError("Insufficient data for string content")
        
        string = data[offset+2:offset+2+str_len].decode('utf-8')
        return string, offset + 2 + str_len
    
    def create_connect_packet(
        self, 
        client_id: str, 
        username: Optional[str] = None,
        password: Optional[str] = None,
        clean_session: bool = True,
        keep_alive: int = 60
    ) -> bytes:
        """Create MQTT CONNECT packet."""
        
        # Variable header
        protocol_name = self._encode_string("MQTT")
        protocol_version = struct.pack('!B', 4)  # MQTT 3.1.1
        
        # Connect flags
        flags = 0
        if clean_session:
            flags |= MQTTConnectFlags.CLEAN_SESSION
        if username:
            flags |= MQTTConnectFlags.USERNAME_FLAG
        if password:
            flags |= MQTTConnectFlags.PASSWORD_FLAG
            
        connect_flags = struct.pack('!B', flags)
        keep_alive_bytes = struct.pack('!H', keep_alive)
        
        variable_header = protocol_name + protocol_version + connect_flags + keep_alive_bytes
        
        # Payload
        payload = self._encode_string(client_id)
        if username:
            payload += self._encode_string(username)
        if password:
            payload += self._encode_string(password)
        
        # Fixed header
        remaining_length = len(variable_header) + len(payload)
        fixed_header = struct.pack('!B', (MQTTPacketType.CONNECT << 4)) + self._encode_remaining_length(remaining_length)
        
        return fixed_header + variable_header + payload
    
    def create_subscribe_packet(self, topic: str, qos: int = 1) -> bytes:
        """Create MQTT SUBSCRIBE packet."""
        
        packet_id = self._get_next_packet_id()
        
        # Variable header (packet identifier)
        variable_header = struct.pack('!H', packet_id)
        
        # Payload (topic filter and QoS)
        payload = self._encode_string(topic) + struct.pack('!B', qos)
        
        # Fixed header
        remaining_length = len(variable_header) + len(payload)
        fixed_header = struct.pack('!B', (MQTTPacketType.SUBSCRIBE << 4) | 0x02) + self._encode_remaining_length(remaining_length)
        
        return fixed_header + variable_header + payload
    
    def create_publish_packet(
        self, 
        topic: str, 
        payload: bytes, 
        qos: int = 0, 
        retain: bool = False,
        dup: bool = False
    ) -> bytes:
        """Create MQTT PUBLISH packet."""
        
        # Fixed header flags
        flags = 0
        if dup:
            flags |= 0x08
        if qos == 1:
            flags |= 0x02
        elif qos == 2:
            flags |= 0x04
        if retain:
            flags |= 0x01
            
        # Variable header
        variable_header = self._encode_string(topic)
        if qos > 0:
            packet_id = self._get_next_packet_id()
            variable_header += struct.pack('!H', packet_id)
        
        # Fixed header
        remaining_length = len(variable_header) + len(payload)
        fixed_header = struct.pack('!B', (MQTTPacketType.PUBLISH << 4) | flags) + self._encode_remaining_length(remaining_length)
        
        return fixed_header + variable_header + payload
    
    def parse_packet(self, data: bytes) -> MQTTMessage:
        """Parse incoming MQTT packet."""
        if len(data) < 2:
            raise ValueError("Packet too short")
        
        # Fixed header
        first_byte = data[0]
        packet_type = (first_byte >> 4) & 0x0F
        flags = first_byte & 0x0F
        
        # Remaining length
        remaining_length, payload_start = self._decode_remaining_length(data)
        
        if len(data) < payload_start + remaining_length:
            raise ValueError("Incomplete packet")
        
        # Extract payload
        payload = data[payload_start:payload_start + remaining_length]
        
        # Extract packet ID if applicable
        packet_id = None
        if packet_type in [MQTTPacketType.PUBACK, MQTTPacketType.PUBREC, 
                          MQTTPacketType.PUBREL, MQTTPacketType.PUBCOMP,
                          MQTTPacketType.SUBSCRIBE, MQTTPacketType.SUBACK,
                          MQTTPacketType.UNSUBSCRIBE, MQTTPacketType.UNSUBACK]:
            if len(payload) >= 2:
                packet_id = struct.unpack('!H', payload[:2])[0]
        
        return MQTTMessage(
            packet_type=packet_type,
            flags=flags,
            payload=payload,
            packet_id=packet_id
        )
    
    def parse_connack(self, payload: bytes) -> Dict[str, Any]:
        """Parse CONNACK payload."""
        if len(payload) < 2:
            raise ValueError("Invalid CONNACK payload")
        
        session_present = bool(payload[0] & 0x01)
        return_code = payload[1]
        
        return_codes = {
            0: "Connection Accepted",
            1: "Connection Refused, unacceptable protocol version",
            2: "Connection Refused, identifier rejected", 
            3: "Connection Refused, Server unavailable",
            4: "Connection Refused, bad user name or password",
            5: "Connection Refused, not authorized"
        }
        
        return {
            "session_present": session_present,
            "return_code": return_code,
            "return_code_name": return_codes.get(return_code, f"Unknown ({return_code})")
        }
    
    def parse_suback(self, payload: bytes) -> Dict[str, Any]:
        """Parse SUBACK payload."""
        if len(payload) < 3:  # packet_id (2 bytes) + at least 1 return code
            raise ValueError("Invalid SUBACK payload")
        
        packet_id = struct.unpack('!H', payload[:2])[0]
        return_codes = list(payload[2:])
        
        return {
            "packet_id": packet_id,
            "return_codes": return_codes
        }
    
    def parse_publish(self, flags: int, payload: bytes) -> Dict[str, Any]:
        """Parse PUBLISH payload."""
        qos = (flags & 0x06) >> 1
        retain = bool(flags & 0x01)
        dup = bool(flags & 0x08)
        
        # Extract topic
        topic, offset = self._decode_string(payload, 0)
        
        # Extract packet ID if QoS > 0
        packet_id = None
        if qos > 0:
            if offset + 2 > len(payload):
                raise ValueError("Missing packet ID")
            packet_id = struct.unpack('!H', payload[offset:offset+2])[0]
            offset += 2
        
        # Extract message payload
        message_payload = payload[offset:]
        
        return {
            "topic": topic,
            "payload": message_payload,
            "qos": qos,
            "retain": retain,
            "dup": dup,
            "packet_id": packet_id
        }
    
    def _get_next_packet_id(self) -> int:
        """Get next packet ID for QoS > 0 messages."""
        packet_id = self._packet_id
        self._packet_id = (self._packet_id % 65535) + 1
        return packet_id