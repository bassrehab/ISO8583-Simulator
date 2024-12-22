from enum import Enum
from typing import Dict, Optional, Union
from dataclasses import dataclass
from datetime import datetime


class ISO8583Version(Enum):
    """ISO 8583 protocol versions"""
    V1987 = "1987"
    V1993 = "1993"
    V2003 = "2003"


class FieldType(Enum):
    """Field data types in ISO 8583"""
    NUMERIC = "n"  # Numbers only
    ALPHA = "a"  # Letters only
    ALPHANUMERIC = "an"  # Letters and numbers
    BINARY = "b"  # Binary data
    SPECIAL = "s"  # Special characters
    TRACK2 = "z"  # Track 2 data
    LLVAR = "ll"  # Variable length (max 99)
    LLLVAR = "lll"  # Variable length (max 999)


@dataclass
class FieldDefinition:
    """Definition of an ISO 8583 field"""
    field_type: FieldType
    max_length: int
    description: str
    encoding: str = "ascii"
    min_length: Optional[int] = None
    padding_char: Optional[str] = None
    padding_direction: str = "left"  # 'left' or 'right'


class MTI(Enum):
    """Message Type Indicators"""
    # Authorization Messages (1XXX)
    AUTH_REQUEST = "1100"
    AUTH_RESPONSE = "1110"
    AUTH_ADVICE = "1120"
    AUTH_ADVICE_RESPONSE = "1130"

    # Financial Messages (2XXX)
    FIN_REQUEST = "1200"
    FIN_RESPONSE = "1210"
    FIN_ADVICE = "1220"
    FIN_ADVICE_RESPONSE = "1230"

    # File Actions (3XXX)
    FILE_UPDATE_REQUEST = "1304"
    FILE_UPDATE_RESPONSE = "1314"

    # Reversals (4XXX)
    REVERSAL_REQUEST = "1400"
    REVERSAL_RESPONSE = "1410"

    # Reconciliation (5XXX)
    RECONCILIATION_REQUEST = "1500"
    RECONCILIATION_RESPONSE = "1510"

    # Administrative Messages (6XXX)
    ADMIN_REQUEST = "1600"
    ADMIN_RESPONSE = "1610"

    # Network Management (8XXX)
    NETWORK_REQUEST = "1800"
    NETWORK_RESPONSE = "1810"


# Standard ISO 8583 field definitions
ISO8583_FIELDS: Dict[int, FieldDefinition] = {
    0: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Message Type Indicator"
    ),
    2: FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=19,
        description="Primary Account Number (PAN)"
    ),
    3: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Processing Code"
    ),
    4: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Amount, Transaction"
    ),
    7: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Transmission Date & Time"
    ),
    11: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Systems Trace Audit Number (STAN)"
    ),
    12: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Time, Local Transaction"
    ),
    13: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Date, Local Transaction"
    ),
    # Add more field definitions as needed...
}


@dataclass
class ISO8583Message:
    """Represents a complete ISO 8583 message"""
    mti: str
    fields: Dict[int, str]
    version: ISO8583Version = ISO8583Version.V1987
    raw_message: Optional[str] = None
    bitmap: Optional[str] = None

    def __post_init__(self):
        """Validate MTI and ensure fields dict exists"""
        if not self.fields:
            self.fields = {}
        if self.mti:
            self.fields[0] = self.mti


class ISO8583Error(Exception):
    """Base exception for ISO 8583 errors"""
    pass


class ParseError(ISO8583Error):
    """Raised when parsing fails"""
    pass


class ValidationError(ISO8583Error):
    """Raised when validation fails"""
    pass


class BuildError(ISO8583Error):
    """Raised when message building fails"""
    pass

