# iso8583sim/core/types.py

from enum import Enum
from typing import Dict, Optional, Union, Any
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


class CardNetwork(Enum):
    """Card network identifiers"""
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    AMEX = "AMEX"
    DISCOVER = "DISCOVER"
    JCB = "JCB"
    UNIONPAY = "UNIONPAY"


class MessageClass(Enum):
    """Message class identifiers (position 2 of MTI)"""
    AUTHORIZATION = "1"
    FINANCIAL = "2"
    FILE_ACTIONS = "3"
    REVERSAL = "4"
    RECONCILIATION = "5"
    ADMINISTRATIVE = "6"
    FEE_COLLECTION = "7"
    NETWORK_MANAGEMENT = "8"


class MessageFunction(Enum):
    """Message function identifiers (position 3 of MTI)"""
    REQUEST = "0"
    RESPONSE = "1"
    ADVICE = "2"
    ADVICE_RESPONSE = "3"
    NOTIFICATION = "4"
    NETWORK_REQUEST = "8"
    NETWORK_RESPONSE = "9"


class MessageOrigin(Enum):
    """Message origin identifiers (position 4 of MTI)"""
    ACQUIRER = "0"
    ACQUIRER_REPEAT = "1"
    ISSUER = "2"
    ISSUER_REPEAT = "3"
    OTHER = "4"
    OTHER_REPEAT = "5"


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

    def __post_init__(self):
        """Set min_length to max_length if not specified for fixed-length fields"""
        if self.min_length is None and self.field_type not in [FieldType.LLVAR, FieldType.LLLVAR]:
            self.min_length = self.max_length


@dataclass
class ISO8583Message:
    """Represents a complete ISO 8583 message"""
    mti: str
    fields: Dict[int, str]
    version: ISO8583Version = ISO8583Version.V1987
    network: Optional[CardNetwork] = None
    raw_message: Optional[str] = None
    bitmap: Optional[str] = None

    def __post_init__(self):
        """Validate MTI and ensure fields dict exists"""
        if not self.fields:
            self.fields = {}
        if self.mti:
            self.fields[0] = self.mti

    @property
    def message_class(self) -> MessageClass:
        """Get message class from MTI"""
        return MessageClass(self.mti[1])

    @property
    def message_function(self) -> MessageFunction:
        """Get message function from MTI"""
        return MessageFunction(self.mti[2])

    @property
    def message_origin(self) -> MessageOrigin:
        """Get message origin from MTI"""
        return MessageOrigin(self.mti[3])


# Custom exceptions
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


# Standard ISO8583 field definitions
ISO8583_FIELDS: Dict[int, FieldDefinition] = {
    # Basic Fields (0-9)
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
        description="Amount, Transaction",
        padding_char="0",
        padding_direction="left"
    ),
    5: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Amount, Settlement",
        padding_char="0",
        padding_direction="left"
    ),
    6: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Amount, Cardholder Billing",
        padding_char="0",
        padding_direction="left"
    ),
    7: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Transmission Date & Time (MMDDhhmmss)"
    ),
    8: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=8,
        description="Amount, Cardholder Billing Fee",
        padding_char="0",
        padding_direction="left"
    ),
    9: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=8,
        description="Conversion Rate, Settlement",
        padding_char="0",
        padding_direction="left"
    ),

    # Transaction Detail Fields (10-19)
    10: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=8,
        description="Conversion Rate, Cardholder Billing"
    ),
    11: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Systems Trace Audit Number (STAN)",
        padding_char="0",
        padding_direction="left"
    ),
    12: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Time, Local Transaction (hhmmss)"
    ),
    13: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Date, Local Transaction (MMDD)"
    ),
    14: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Date, Expiration (YYMM)"
    ),
    15: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Date, Settlement (MMDD)"
    ),
    16: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Date, Conversion (MMDD)"
    ),
    17: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Date, Capture (MMDD)"
    ),
    18: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Merchant Type/Merchant Category Code"
    ),
    19: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Acquiring Institution Country Code"
    ),

    # POS and Card Data Fields (20-39)
    22: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Point of Service Entry Mode"
    ),
    23: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Card Sequence Number"
    ),
    25: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=2,
        description="Point of Service Condition Code"
    ),
    26: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=2,
        description="Point of Service PIN Capture Code"
    ),
    28: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=9,
        description="Amount, Transaction Fee",
        padding_char="0",
        padding_direction="left"
    ),
    32: FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=11,
        description="Acquiring Institution ID Code"
    ),
    33: FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=11,
        description="Forwarding Institution ID Code"
    ),
    35: FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=37,
        description="Track 2 Data"
    ),
    36: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=104,
        description="Track 3 Data"
    ),
    37: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=12,
        description="Retrieval Reference Number",
        padding_char=" ",
        padding_direction="right"
    ),
    38: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=6,
        description="Authorization ID Response",
        padding_char=" ",
        padding_direction="right"
    ),
    39: FieldDefinition(
        field_type=FieldType.NUMERIC,  # Changed from ALPHANUMERIC to NUMERIC
        max_length=2,
        description="Response Code",
        padding_char="0",
        padding_direction="left"
    ),

    # Terminal and Merchant Fields (40-49)
    41: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=8,
        description="Card Acceptor Terminal ID",
        padding_char=" ",
        padding_direction="right"
    ),
    42: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=15,
        description="Card Acceptor ID Code",
        padding_char=" ",
        padding_direction="right"
    ),
    43: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=40,
        description="Card Acceptor Name/Location",
        padding_char=" ",
        padding_direction="right"
    ),
    44: FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=25,
        description="Additional Response Data"
    ),
    45: FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=76,
        description="Track 1 Data"
    ),
    48: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Additional Data - Private"
    ),
    49: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Currency Code, Transaction"
    ),

    # Security Related Fields (50-59)
    50: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Currency Code, Settlement"
    ),
    51: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Currency Code, Cardholder Billing"
    ),
    52: FieldDefinition(
        field_type=FieldType.BINARY,
        max_length=8,
        description="Personal Identification Number (PIN) Data"
    ),
    53: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=16,
        description="Security Related Control Information"
    ),
    54: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=120,
        description="Additional Amounts"
    ),
    55: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="ICC System Related Data"
    ),
    56: FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=35,
        description="Reserved ISO"
    ),
    57: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved National"
    ),
    58: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved National"
    ),
    59: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved National"
    ),

    # Additional Data Fields (60-79)
    60: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved National"
    ),
    61: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved National"
    ),
    62: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved Private"
    ),
    63: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved Private"
    ),
    64: FieldDefinition(
        field_type=FieldType.BINARY,
        max_length=8,
        description="Message Authentication Code (MAC)"
    ),
    65: FieldDefinition(
        field_type=FieldType.BINARY,
        max_length=8,
        description="Extended Bitmap Indicator",
        padding_char="0",
        padding_direction="left"
    ),
    66: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=1,
        description="Settlement Code"
    ),
    67: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=2,
        description="Extended Payment Code"
    ),
    68: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Receiving Institution Country Code"
    ),
    69: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Settlement Institution Country Code"
    ),
    70: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Network Management Information Code"
    ),
    71: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Message Number"
    ),
    72: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Last Message Number"
    ),
    73: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Action Date (YYMMDD)"
    ),
    74: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Credits, Number"
    ),
    75: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Credits, Reversal Number"
    ),
    76: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Debits, Number"
    ),
    77: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Debits, Reversal Number"
    ),
    78: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Transfer, Number"
    ),
    79: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Transfer, Reversal Number"
    ),

    # Network Fields (80-99)
    80: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Inquiries, Number"
    ),
    81: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Authorizations, Number"
    ),
    82: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Credits, Processing Fee Amount"
    ),
    83: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Credits, Transaction Fee Amount"
    ),
    84: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Debits, Processing Fee Amount"
    ),
    85: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Debits, Transaction Fee Amount"
    ),
    86: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=16,
        description="Credits, Amount"
    ),
    87: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=16,
        description="Credits, Reversal Amount"
    ),
    88: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=16,
        description="Debits, Amount"
    ),
    89: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=16,
        description="Debits, Reversal Amount"
    ),
    90: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=42,
        description="Original Data Elements",
        padding_char="0",
        padding_direction="left"
    ),
    91: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=1,
        description="File Update Code"
    ),
    92: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=2,
        description="File Security Code"
    ),
    93: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=5,
        description="Response Indicator"
    ),
    94: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=7,
        description="Service Indicator"
    ),
    95: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=42,
        description="Replacement Amounts"
    ),
    96: FieldDefinition(
        field_type=FieldType.BINARY,
        max_length=8,
        description="Message Security Code",
        padding_char="0",
        padding_direction="left"
    ),
    97: FieldDefinition(
        field_type=FieldType.BINARY,
        max_length=17,
        description="Amount, Net Settlement"
    ),
    98: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=25,
        description="Payee"
    ),
    99: FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=11,
        description="Settlement Institution ID Code"
    ),

    # Additional Fields (100-128)
    100: FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=11,
        description="Receiving Institution ID Code"
    ),
    101: FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=17,
        description="File Name"
    ),
    102: FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=28,
        description="Account Identification 1"
    ),
    103: FieldDefinition(
        field_type=FieldType.LLVAR,
        max_length=28,
        description="Account Identification 2"
    ),
    104: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=100,
        description="Transaction Description"
    ),
    105: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for ISO Use"
    ),
    106: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for ISO Use"
    ),
    107: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for ISO Use"
    ),
    108: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for ISO Use"
    ),
    109: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for ISO Use"
    ),
    110: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for ISO Use"
    ),
    111: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for ISO Use"
    ),
    112: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for National Use"
    ),
    113: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for National Use"
    ),
    114: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for National Use"
    ),
    115: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for National Use"
    ),
    116: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for National Use"
    ),
    117: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for National Use"
    ),
    118: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for National Use"
    ),
    119: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for National Use"
    ),
    120: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for Private Use"
    ),
    121: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for Private Use"
    ),
    122: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for Private Use"
    ),
    123: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for Private Use"
    ),
    124: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for Private Use"
    ),
    125: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for Private Use"
    ),
    126: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for Private Use"
    ),
    127: FieldDefinition(
        field_type=FieldType.LLLVAR,
        max_length=999,
        description="Reserved for Private Use"
    ),
    128: FieldDefinition(
        field_type=FieldType.BINARY,
        max_length=8,
        description="Message Authentication Code"
    ),
}


# Network-specific field definitions
NETWORK_SPECIFIC_FIELDS = {
    CardNetwork.VISA: {
        44: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=99,
            description="Additional Response Data (VISA)"
        ),
        46: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=204,
            description="Fee Amounts (VISA)"
        ),
        47: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - National (VISA)"
        ),
        66: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=204,
            description="Settlement Code (VISA)"
        ),
        67: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=2,
            description="Extended Payment Code (VISA)"
        ),
        71: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=8,
            description="Message Number (VISA)"
        ),
        72: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Data Record (VISA)"
        ),
        73: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=6,
            description="Action Date (VISA)"
        ),
        92: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=3,
            description="File Security Code (VISA)"
        ),
        93: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=6,
            description="Transaction Identifier (VISA)"
        ),
    },

    CardNetwork.MASTERCARD: {
        48: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - Private (MC Format)"
        ),
        54: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=120,
            description="Additional Amounts (MC Format)"
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=510,
            description="ICC System Related Data (MC EMV Tags)"
        ),
        56: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=4096,
            description="Original Data Elements (MC)"
        ),
        91: FieldDefinition(
            field_type=FieldType.ALPHANUMERIC,
            max_length=1,
            description="File Update Code (MC)"
        ),
        92: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=2,
            description="File Security Code (MC)"
        ),
        94: FieldDefinition(
            field_type=FieldType.ALPHANUMERIC,
            max_length=7,
            description="Service Indicator (MC)"
        ),
        95: FieldDefinition(
            field_type=FieldType.BINARY,
            max_length=56,
            description="Card Issuer Reference Data (MC)"
        ),
    },

    CardNetwork.AMEX: {
        44: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=99,
            description="Additional Response Data (AMEX)"
        ),
        47: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - National (AMEX)"
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="ICC Data (AMEX Format)"
        ),
        112: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data (AMEX)"
        ),
        124: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Sundry Data (AMEX)"
        ),
    },

    CardNetwork.UNIONPAY: {
        33: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=28,
            description="Forwarding Institution ID (UnionPay)"
        ),
        40: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=3,
            description="Service Restriction Code (UnionPay)"
        ),
        90: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=42,
            description="Original Data Elements (UnionPay)"
        ),
        100: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=11,
            description="Receiving Institution ID (UnionPay)"
        ),
    }
}

# Version-specific variations
VERSION_SPECIFIC_FIELDS = {
    ISO8583Version.V1987: {
        # Base version - no overrides needed
    },

    ISO8583Version.V1993: {
        43: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=99,
            description="Card Acceptor Name/Location (1993)"
        ),
        52: FieldDefinition(
            field_type=FieldType.BINARY,
            max_length=16,
            description="PIN Data (1993)"
        ),
        53: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=48,
            description="Security Related Control Information (1993)"
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=255,
            description="ICC Data (1993)"
        ),
    },

    ISO8583Version.V2003: {
        43: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=256,
            description="Card Acceptor Name/Location (2003)"
        ),
        52: FieldDefinition(
            field_type=FieldType.BINARY,
            max_length=32,
            description="PIN Data (2003)"
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="ICC Data (2003)"
        ),
        57: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Payment Data (2003)"
        ),
        58: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Reserved for National Use (2003)"
        ),
        59: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Reserved for National Use (2003)"
        ),
    }
}


def get_field_definition(
        field_number: int,
        network: Optional[CardNetwork] = None,
        version: ISO8583Version = ISO8583Version.V1987
) -> Optional[FieldDefinition]:
    """
    Get field definition considering network and version specifics

    Args:
        field_number: The field number to look up
        network: Optional card network for network-specific definitions
        version: ISO8583 version

    Returns:
        FieldDefinition if found, None otherwise
    """
    # Check network-specific fields first
    if network and network in NETWORK_SPECIFIC_FIELDS:
        if field_number in NETWORK_SPECIFIC_FIELDS[network]:
            return NETWORK_SPECIFIC_FIELDS[network][field_number]

    # Check version-specific variations
    if field_number in VERSION_SPECIFIC_FIELDS[version]:
        return VERSION_SPECIFIC_FIELDS[version][field_number]

    # Fall back to standard fields
    return ISO8583_FIELDS.get(field_number)


def is_valid_mti(mti: str) -> bool:
    """Check if MTI is valid"""
    if not mti or len(mti) != 4 or not mti.isdigit():
        return False

    version = mti[0]
    if version not in ['0', '1']:
        return False

    message_class = mti[1]
    if message_class not in [m.value for m in MessageClass]:
        return False

    message_function = mti[2]
    if message_function not in [f.value for f in MessageFunction]:
        return False

    message_origin = mti[3]
    if message_origin not in [o.value for o in MessageOrigin]:
        return False

    return True

# Extending network-specific fields in iso8583sim/core/types.py

NETWORK_SPECIFIC_FIELDS = {
    CardNetwork.VISA: {
        # Previous VISA fields remain...
        44: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=99,
            description="Additional Response Data (VISA)"
        ),
        46: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=204,
            description="Fee Amounts (VISA)"
        ),
        # Additional VISA specific fields
        47: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - National (VISA)"
        ),
        48: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - Private (VISA Installments)"
        ),
        60: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Advised Echo Data (VISA)"
        ),
        62: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Card Issuer Data (VISA)"
        ),
        63: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="SMS Fields (VISA)"
        ),
        104: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Transaction Specific Data (VISA)"
        ),
        120: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Record Data (VISA)"
        ),
        121: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Issuer Authorization Data (VISA)"
        ),
        123: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Verification Data (VISA)"
        ),
        124: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Network Control Data (VISA)"
        ),
        125: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="POS Configuration Data (VISA)"
        ),
    },

    CardNetwork.MASTERCARD: {
        # Previous Mastercard fields remain...
        48: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - Private (MC Format)"
        ),
        # Additional Mastercard specific fields
        34: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=28,
            description="Extended PAN (MC)"
        ),
        45: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=76,
            description="Track 1 Data (MC Format)"
        ),
        51: FieldDefinition(
            field_type=FieldType.ALPHANUMERIC,
            max_length=3,
            description="PIN Security Type (MC)"
        ),
        57: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Authorization Life Cycle Code (MC)"
        ),
        58: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=11,
            description="Authorizing Agent Institution ID (MC)"
        ),
        59: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Transport Data (MC)"
        ),
        63: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Network Data (MC)"
        ),
        71: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=8,
            description="Message Number (MC)"
        ),
        84: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Data - Private Use (MC)"
        ),
        105: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="MC Reserved"
        ),
        122: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Card Issuer Reference Data (MC)"
        ),
        126: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Switch Private Data (MC)"
        ),
    },

    CardNetwork.JCB: {
        # JCB specific fields
        42: FieldDefinition(
            field_type=FieldType.ALPHANUMERIC,
            max_length=15,
            description="Card Acceptor ID Code (JCB)"
        ),
        48: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - Private (JCB)"
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=255,
            description="ICC System Related Data (JCB)"
        ),
        61: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Internal Data (JCB)"
        ),
        62: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Private Data (JCB)"
        ),
        63: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="SMS Private Data (JCB)"
        ),
        114: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Regional Data (JCB)"
        ),
    },

    CardNetwork.DISCOVER: {
        # Discover specific fields
        44: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=99,
            description="Additional Response Data (Discover)"
        ),
        48: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - Private (Discover)"
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="ICC Data (Discover Format)"
        ),
        62: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Network Specific Data (Discover)"
        ),
        63: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Protocol Specific Data (Discover)"
        ),
        95: FieldDefinition(
            field_type=FieldType.BINARY,
            max_length=56,
            description="Card Issuer Reference Data (Discover)"
        ),
        111: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Network Details (Discover)"
        ),
    },

    CardNetwork.UNIONPAY: {
        # Previous UnionPay fields remain...
        # Additional UnionPay specific fields
        33: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=28,
            description="Forwarding Institution ID (UnionPay)"
        ),
        40: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=3,
            description="Service Restriction Code (UnionPay)"
        ),
        41: FieldDefinition(
            field_type=FieldType.ALPHANUMERIC,
            max_length=8,
            description="Terminal ID (UnionPay Format)"
        ),
        42: FieldDefinition(
            field_type=FieldType.ALPHANUMERIC,
            max_length=15,
            description="Merchant ID (UnionPay Format)"
        ),
        48: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - Private (UnionPay)"
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="ICC Data (UnionPay Format)"
        ),
        60: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Reserved National (UnionPay)"
        ),
        63: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data (UnionPay)"
        ),
        102: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=28,
            description="Account Identifier 1 (UnionPay)"
        ),
        103: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=28,
            description="Account Identifier 2 (UnionPay)"
        ),
        113: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="UnionPay Reserved"
        ),
    },

    CardNetwork.AMEX: {
        # Previous AMEX fields remain...
        # Additional AMEX specific fields
        23: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=3,
            description="Card Sequence Number (AMEX)"
        ),
        48: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Transaction Level Data (AMEX)"
        ),
        60: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Network Data (AMEX)"
        ),
        61: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Other Terminal Data (AMEX)"
        ),
        63: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Card Level Results (AMEX)"
        ),
        76: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Confirmations/Authorizations (AMEX)"
        ),
        112: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data (AMEX)"
        ),
        124: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Sundry Data (AMEX)"
        ),
        125: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Extended Response Data (AMEX)"
        ),
    }
}