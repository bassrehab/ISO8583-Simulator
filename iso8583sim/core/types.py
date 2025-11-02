# iso8583sim/core/types.py

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache


class ISO8583Version(Enum):
    """ISO 8583 protocol versions"""

    V1987 = "1987"  # Original version
    V1993 = "1993"  # First revision
    V2003 = "2003"  # Second revision


class FieldType(Enum):
    """Field data types in ISO 8583"""

    NUMERIC = "n"  # Numbers only (0-9)
    ALPHA = "a"  # Letters only (A-Z, a-z)
    ALPHANUMERIC = "an"  # Letters and numbers
    BINARY = "b"  # Binary/hex data
    SPECIAL = "s"  # Special characters
    TRACK2 = "z"  # Track 2 magnetic stripe data
    LLVAR = "ll"  # Variable length (max 99)
    LLLVAR = "lll"  # Variable length (max 999)

    def __str__(self) -> str:
        """String representation returns the value"""
        return self.value


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

    AUTHORIZATION = "1"  # Authorization message
    FINANCIAL = "2"  # Financial message
    FILE_ACTIONS = "3"  # File action message
    REVERSAL = "4"  # Reversal message
    RECONCILIATION = "5"  # Reconciliation message
    ADMINISTRATIVE = "6"  # Administrative message
    FEE_COLLECTION = "7"  # Fee collection message
    NETWORK_MANAGEMENT = "8"  # Network management message


class MessageFunction(Enum):
    """Message function identifiers (position 3 of MTI)"""

    REQUEST = "0"  # Request message
    RESPONSE = "1"  # Response message
    ADVICE = "2"  # Advice message
    ADVICE_RESPONSE = "3"  # Response to advice
    NOTIFICATION = "4"  # Notification message
    NETWORK_REQUEST = "8"  # Network management request
    NETWORK_RESPONSE = "9"  # Network management response


class MessageOrigin(Enum):
    """Message origin identifiers (position 4 of MTI)"""

    ACQUIRER = "0"  # Acquirer
    ACQUIRER_REPEAT = "1"  # Acquirer repeat
    ISSUER = "2"  # Issuer
    ISSUER_REPEAT = "3"  # Issuer repeat
    OTHER = "4"  # Other
    OTHER_REPEAT = "5"  # Other repeat


@dataclass(slots=True)
class FieldDefinition:
    """Definition of an ISO 8583 field"""

    field_type: FieldType  # Data type of the field
    max_length: int  # Maximum length in characters/digits
    description: str  # Field description
    field_number: int | None = None  # Field number in ISO8583 message
    encoding: str = "ascii"  # Character encoding
    min_length: int | None = None  # Minimum length (if different from max)
    padding_char: str | None = None  # Character used for padding
    padding_direction: str = "left"  # Direction of padding ('left' or 'right')

    def __post_init__(self):
        """Validate field definition attributes after initialization"""
        # Validate field type
        if not isinstance(self.field_type, FieldType):
            raise ValueError(f"Invalid field type: {self.field_type}")

        # Validate max_length
        if not isinstance(self.max_length, int) or self.max_length <= 0:
            raise ValueError(f"Invalid max length: {self.max_length}")

        # Validate min_length if provided
        if self.min_length is not None:
            if not isinstance(self.min_length, int) or self.min_length < 0:
                raise ValueError(f"Invalid min length: {self.min_length}")
            if self.min_length > self.max_length:
                raise ValueError("min_length cannot be greater than max_length")

        # Validate padding_direction
        if self.padding_direction not in ["left", "right"]:
            raise ValueError(f"Invalid padding direction: {self.padding_direction}")

        # Set min_length to max_length for fixed-length fields
        if self.min_length is None and self.field_type not in [FieldType.LLVAR, FieldType.LLLVAR]:
            self.min_length = self.max_length

        # Validate padding char length
        if self.padding_char is not None and len(self.padding_char) != 1:
            raise ValueError("padding_char must be a single character")

        # Validate encoding
        if not isinstance(self.encoding, str):
            raise ValueError("encoding must be a string")


@dataclass(slots=True)
class ISO8583Message:
    """Represents a complete ISO 8583 message"""

    mti: str  # Message Type Indicator
    fields: dict[int, str]  # Message fields
    version: ISO8583Version = ISO8583Version.V1987  # Protocol version
    network: CardNetwork | None = None  # Card network
    raw_message: str | None = None  # Raw message string
    bitmap: str | None = None  # Message bitmap

    def __post_init__(self):
        """Initialize fields after creation"""
        # Ensure fields dictionary exists
        if not self.fields:
            self.fields = {}
        # Add MTI as field 0
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


# Custom exceptions for ISO8583 operations
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


# Standard ISO8583 field definitions - Core Fields (0-49)
ISO8583_FIELDS: dict[int, FieldDefinition] = {
    # Message Header Fields (0-9)
    0: FieldDefinition(
        field_type=FieldType.NUMERIC, max_length=4, description="Message Type Indicator (MTI)", padding_char=None
    ),
    2: FieldDefinition(
        field_type=FieldType.LLVAR, max_length=19, description="Primary Account Number (PAN)", padding_char=None
    ),
    3: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Processing Code",
        padding_char="0",
        padding_direction="left",
    ),
    4: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Amount, Transaction",
        padding_char="0",
        padding_direction="left",
    ),
    5: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Amount, Settlement",
        padding_char="0",
        padding_direction="left",
    ),
    6: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Amount, Cardholder Billing",
        padding_char="0",
        padding_direction="left",
    ),
    7: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Transmission Date & Time (MMDDhhmmss)",
        padding_char="0",
        padding_direction="left",
    ),
    8: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=8,
        description="Amount, Cardholder Billing Fee",
        padding_char="0",
        padding_direction="left",
    ),
    9: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=8,
        description="Conversion Rate, Settlement",
        padding_char="0",
        padding_direction="left",
    ),
    # Transaction Detail Fields (10-19)
    10: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=8,
        description="Conversion Rate, Cardholder Billing",
        padding_char="0",
        padding_direction="left",
    ),
    11: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Systems Trace Audit Number (STAN)",
        padding_char="0",
        padding_direction="left",
    ),
    12: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Time, Local Transaction (hhmmss)",
        padding_char="0",
        padding_direction="left",
    ),
    13: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Date, Local Transaction (MMDD)",
        padding_char="0",
        padding_direction="left",
    ),
    14: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Date, Expiration (YYMM)",
        padding_char="0",
        padding_direction="left",
    ),
    15: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Date, Settlement (MMDD)",
        padding_char="0",
        padding_direction="left",
    ),
    16: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Date, Conversion (MMDD)",
        padding_char="0",
        padding_direction="left",
    ),
    17: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Date, Capture (MMDD)",
        padding_char="0",
        padding_direction="left",
    ),
    18: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Merchant Type/Merchant Category Code",
        padding_char="0",
        padding_direction="left",
    ),
    19: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Acquiring Institution Country Code",
        padding_char="0",
        padding_direction="left",
    ),
    # POS Entry and Card Data Fields (20-39)
    22: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Point of Service Entry Mode",
        padding_char="0",
        padding_direction="left",
    ),
    23: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Card Sequence Number",
        padding_char="0",
        padding_direction="left",
    ),
    24: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Function Code",
        padding_char="0",
        padding_direction="left",
    ),
    25: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=2,
        description="Point of Service Condition Code",
        padding_char="0",
        padding_direction="left",
    ),
    26: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=2,
        description="Point of Service PIN Capture Code",
        padding_char="0",
        padding_direction="left",
    ),
    28: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=9,
        description="Amount, Transaction Fee",
        padding_char="0",
        padding_direction="left",
    ),
    32: FieldDefinition(
        field_type=FieldType.LLVAR, max_length=11, description="Acquiring Institution ID Code", padding_char=None
    ),
    33: FieldDefinition(
        field_type=FieldType.LLVAR, max_length=11, description="Forwarding Institution ID Code", padding_char=None
    ),
    35: FieldDefinition(field_type=FieldType.LLVAR, max_length=37, description="Track 2 Data", padding_char=None),
    36: FieldDefinition(field_type=FieldType.LLLVAR, max_length=104, description="Track 3 Data", padding_char=None),
    37: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=12,
        description="Retrieval Reference Number",
        padding_char=" ",
        padding_direction="right",
    ),
    38: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=6,
        description="Authorization ID Response",
        padding_char=" ",
        padding_direction="right",
    ),
    39: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=2,
        description="Response Code",
        padding_char="0",
        padding_direction="left",
    ),
    # Terminal and Merchant Fields (40-49)
    41: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=8,
        description="Card Acceptor Terminal ID",
        padding_char=" ",
        padding_direction="right",
    ),
    42: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=15,
        description="Card Acceptor ID Code",
        padding_char=" ",
        padding_direction="right",
    ),
    43: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=40,
        description="Card Acceptor Name/Location",
        padding_char=" ",
        padding_direction="right",
    ),
    44: FieldDefinition(
        field_type=FieldType.LLVAR, max_length=25, description="Additional Response Data", padding_char=None
    ),
    45: FieldDefinition(field_type=FieldType.LLVAR, max_length=76, description="Track 1 Data", padding_char=None),
    48: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Additional Data - Private", padding_char=None
    ),
    49: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Currency Code, Transaction",
        padding_char="0",
        padding_direction="left",
    ),
    # Currency and Security Fields (50-59)
    50: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Currency Code, Settlement",
        padding_char="0",
        padding_direction="left",
    ),
    51: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Currency Code, Cardholder Billing",
        padding_char="0",
        padding_direction="left",
    ),
    52: FieldDefinition(
        field_type=FieldType.BINARY,
        max_length=8,  # 8 bytes = 16 hex chars
        description="Personal Identification Number (PIN) Data",
        padding_char=None,
    ),
    53: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=16,
        description="Security Related Control Information",
        padding_char="0",
        padding_direction="left",
    ),
    54: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=120, description="Additional Amounts", padding_char=None
    ),
    55: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="ICC System Related Data", padding_char=None
    ),
    56: FieldDefinition(field_type=FieldType.LLVAR, max_length=35, description="Reserved ISO", padding_char=None),
    57: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved National", padding_char=None
    ),
    58: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved National", padding_char=None
    ),
    59: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved National", padding_char=None
    ),
    # Reserved and Private Fields (60-79)
    60: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved National", padding_char=None
    ),
    61: FieldDefinition(field_type=FieldType.LLLVAR, max_length=999, description="Reserved Private", padding_char=None),
    62: FieldDefinition(field_type=FieldType.LLLVAR, max_length=999, description="Reserved Private", padding_char=None),
    63: FieldDefinition(field_type=FieldType.LLLVAR, max_length=999, description="Reserved Private", padding_char=None),
    64: FieldDefinition(
        field_type=FieldType.BINARY,
        max_length=8,  # 8 bytes = 16 hex chars
        description="Message Authentication Code (MAC)",
        padding_char=None,
    ),
    65: FieldDefinition(
        field_type=FieldType.BINARY,
        max_length=8,  # 8 bytes = 16 hex chars
        description="Extended Bitmap Indicator",
        padding_char=None,
    ),
    66: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=1,
        description="Settlement Code",
        padding_char="0",
        padding_direction="left",
    ),
    67: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=2,
        description="Extended Payment Code",
        padding_char="0",
        padding_direction="left",
    ),
    68: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Receiving Institution Country Code",
        padding_char="0",
        padding_direction="left",
    ),
    69: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Settlement Institution Country Code",
        padding_char="0",
        padding_direction="left",
    ),
    # Network Management Fields (70-79)
    70: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=3,
        description="Network Management Information Code",
        padding_char="0",
        padding_direction="left",
    ),
    71: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Message Number",
        padding_char="0",
        padding_direction="left",
    ),
    72: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=4,
        description="Last Message Number",
        padding_char="0",
        padding_direction="left",
    ),
    73: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=6,
        description="Action Date (YYMMDD)",
        padding_char="0",
        padding_direction="left",
    ),
    74: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Credits, Number",
        padding_char="0",
        padding_direction="left",
    ),
    75: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Credits, Reversal Number",
        padding_char="0",
        padding_direction="left",
    ),
    76: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Debits, Number",
        padding_char="0",
        padding_direction="left",
    ),
    77: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Debits, Reversal Number",
        padding_char="0",
        padding_direction="left",
    ),
    78: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Transfer, Number",
        padding_char="0",
        padding_direction="left",
    ),
    79: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Transfer, Reversal Number",
        padding_char="0",
        padding_direction="left",
    ),
    # Reconciliation Fields (80-89)
    80: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Inquiries, Number",
        padding_char="0",
        padding_direction="left",
    ),
    81: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=10,
        description="Authorizations, Number",
        padding_char="0",
        padding_direction="left",
    ),
    82: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Credits, Processing Fee Amount",
        padding_char="0",
        padding_direction="left",
    ),
    83: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Credits, Transaction Fee Amount",
        padding_char="0",
        padding_direction="left",
    ),
    84: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Debits, Processing Fee Amount",
        padding_char="0",
        padding_direction="left",
    ),
    85: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=12,
        description="Debits, Transaction Fee Amount",
        padding_char="0",
        padding_direction="left",
    ),
    86: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=16,
        description="Credits, Amount",
        padding_char="0",
        padding_direction="left",
    ),
    87: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=16,
        description="Credits, Reversal Amount",
        padding_char="0",
        padding_direction="left",
    ),
    88: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=16,
        description="Debits, Amount",
        padding_char="0",
        padding_direction="left",
    ),
    89: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=16,
        description="Debits, Reversal Amount",
        padding_char="0",
        padding_direction="left",
    ),
    # Administrative and Security Fields (90-99)
    90: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=42,
        description="Original Data Elements",
        padding_char="0",
        padding_direction="left",
    ),
    91: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=1,
        description="File Update Code",
        padding_char=" ",
        padding_direction="right",
    ),
    92: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=2,
        description="File Security Code",
        padding_char="0",
        padding_direction="left",
    ),
    93: FieldDefinition(
        field_type=FieldType.NUMERIC,
        max_length=5,
        description="Response Indicator",
        padding_char="0",
        padding_direction="left",
    ),
    94: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=7,
        description="Service Indicator",
        padding_char=" ",
        padding_direction="right",
    ),
    95: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=42,
        description="Replacement Amounts",
        padding_char=" ",
        padding_direction="right",
    ),
    96: FieldDefinition(
        field_type=FieldType.BINARY,
        max_length=8,  # 8 bytes = 16 hex chars
        description="Message Security Code",
        padding_char=None,
    ),
    97: FieldDefinition(
        field_type=FieldType.BINARY, max_length=17, description="Amount, Net Settlement", padding_char=None
    ),
    98: FieldDefinition(
        field_type=FieldType.ALPHANUMERIC,
        max_length=25,
        description="Payee",
        padding_char=" ",
        padding_direction="right",
    ),
    99: FieldDefinition(
        field_type=FieldType.LLVAR, max_length=11, description="Settlement Institution ID Code", padding_char=None
    ),
    # Additional Settlement Fields (100-104)
    100: FieldDefinition(
        field_type=FieldType.LLVAR, max_length=11, description="Receiving Institution ID Code", padding_char=None
    ),
    101: FieldDefinition(field_type=FieldType.LLVAR, max_length=17, description="File Name", padding_char=None),
    102: FieldDefinition(
        field_type=FieldType.LLVAR, max_length=28, description="Account Identification 1", padding_char=None
    ),
    103: FieldDefinition(
        field_type=FieldType.LLVAR, max_length=28, description="Account Identification 2", padding_char=None
    ),
    104: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=100, description="Transaction Description", padding_char=None
    ),
    # ISO Reserved Fields (105-111)
    105: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for ISO Use", padding_char=None
    ),
    106: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for ISO Use", padding_char=None
    ),
    107: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for ISO Use", padding_char=None
    ),
    108: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for ISO Use", padding_char=None
    ),
    109: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for ISO Use", padding_char=None
    ),
    110: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for ISO Use", padding_char=None
    ),
    111: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for ISO Use", padding_char=None
    ),
    # National Use Fields (112-119)
    112: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for National Use", padding_char=None
    ),
    113: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for National Use", padding_char=None
    ),
    114: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for National Use", padding_char=None
    ),
    115: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for National Use", padding_char=None
    ),
    116: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for National Use", padding_char=None
    ),
    117: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for National Use", padding_char=None
    ),
    118: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for National Use", padding_char=None
    ),
    119: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for National Use", padding_char=None
    ),
    # Private Use Fields (120-127)
    120: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for Private Use", padding_char=None
    ),
    121: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for Private Use", padding_char=None
    ),
    122: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for Private Use", padding_char=None
    ),
    123: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for Private Use", padding_char=None
    ),
    124: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for Private Use", padding_char=None
    ),
    125: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for Private Use", padding_char=None
    ),
    126: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for Private Use", padding_char=None
    ),
    127: FieldDefinition(
        field_type=FieldType.LLLVAR, max_length=999, description="Reserved for Private Use", padding_char=None
    ),
    # Message Authentication Field (128)
    128: FieldDefinition(
        field_type=FieldType.BINARY,
        max_length=8,  # 8 bytes = 16 hex chars
        description="Message Authentication Code",
        padding_char=None,
    ),
}

# Network-specific field definitions
NETWORK_SPECIFIC_FIELDS = {
    CardNetwork.VISA: {
        # Message Data Fields
        24: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=3,
            description="Function Code (VISA)",
            padding_char="0",
            padding_direction="left",
        ),
        44: FieldDefinition(
            field_type=FieldType.LLVAR, max_length=99, description="Additional Response Data (VISA)", padding_char=None
        ),
        46: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=204, description="Fee Amounts (VISA)", padding_char=None
        ),
        47: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - National (VISA)",
            padding_char=None,
        ),
        48: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - Private (VISA Installments)",
            padding_char=None,
        ),
        # Network Management Fields
        60: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Advised Echo Data (VISA)", padding_char=None
        ),
        62: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Card Issuer Data (VISA)", padding_char=None
        ),
        63: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="SMS Fields (VISA)", padding_char=None
        ),
        66: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=204, description="Settlement Code (VISA)", padding_char=None
        ),
        67: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=2,
            description="Extended Payment Code (VISA)",
            padding_char="0",
            padding_direction="left",
        ),
        71: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=8,
            description="Message Number (VISA)",
            padding_char="0",
            padding_direction="left",
        ),
        72: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Data Record (VISA)", padding_char=None
        ),
        73: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=6,
            description="Action Date (VISA)",
            padding_char="0",
            padding_direction="left",
        ),
        92: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=3,
            description="File Security Code (VISA)",
            padding_char="0",
            padding_direction="left",
        ),
        93: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=6,
            description="Transaction Identifier (VISA)",
            padding_char="0",
            padding_direction="left",
        ),
        # Extended Data Fields
        104: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Transaction Specific Data (VISA)",
            padding_char=None,
        ),
        120: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Record Data (VISA)", padding_char=None
        ),
        121: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Issuer Authorization Data (VISA)",
            padding_char=None,
        ),
        123: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Verification Data (VISA)", padding_char=None
        ),
        124: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Network Control Data (VISA)", padding_char=None
        ),
        125: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="POS Configuration Data (VISA)", padding_char=None
        ),
    },
    CardNetwork.MASTERCARD: {
        # Card Data Fields
        24: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=3,
            description="Function Code (MC)",
            padding_char="0",
            padding_direction="left",
        ),
        34: FieldDefinition(
            field_type=FieldType.LLVAR, max_length=28, description="Extended PAN (MC)", padding_char=None
        ),
        45: FieldDefinition(
            field_type=FieldType.LLVAR, max_length=76, description="Track 1 Data (MC Format)", padding_char=None
        ),
        # Transaction Data Fields
        48: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - Private (MC Format)",
            padding_char=None,
        ),
        51: FieldDefinition(
            field_type=FieldType.ALPHANUMERIC,
            max_length=3,
            description="PIN Security Type (MC)",
            padding_char=" ",
            padding_direction="right",
        ),
        54: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=120, description="Additional Amounts (MC Format)", padding_char=None
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=510,
            description="ICC System Related Data (MC EMV Tags)",
            padding_char=None,
        ),
        56: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=4096, description="Original Data Elements (MC)", padding_char=None
        ),
        # Network Management Fields
        57: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Authorization Life Cycle Code (MC)",
            padding_char=None,
        ),
        58: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=11,
            description="Authorizing Agent Institution ID (MC)",
            padding_char=None,
        ),
        59: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Transport Data (MC)", padding_char=None
        ),
        63: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Network Data (MC)", padding_char=None
        ),
        71: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=8,
            description="Message Number (MC)",
            padding_char="0",
            padding_direction="left",
        ),
        84: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Data - Private Use (MC)", padding_char=None
        ),
        91: FieldDefinition(
            field_type=FieldType.ALPHANUMERIC,
            max_length=1,
            description="File Update Code (MC)",
            padding_char=" ",
            padding_direction="right",
        ),
        92: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=2,
            description="File Security Code (MC)",
            padding_char="0",
            padding_direction="left",
        ),
        94: FieldDefinition(
            field_type=FieldType.ALPHANUMERIC,
            max_length=7,
            description="Service Indicator (MC)",
            padding_char=" ",
            padding_direction="right",
        ),
        95: FieldDefinition(
            field_type=FieldType.BINARY,
            max_length=28,  # 56 hex chars = 28 bytes
            description="Card Issuer Reference Data (MC)",
            padding_char=None,
        ),
        # Extended Data Fields
        105: FieldDefinition(field_type=FieldType.LLLVAR, max_length=999, description="MC Reserved", padding_char=None),
        122: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Card Issuer Reference Data (MC)",
            padding_char=None,
        ),
        126: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Switch Private Data (MC)", padding_char=None
        ),
    },
    CardNetwork.AMEX: {
        # Card and Transaction Data Fields
        23: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=3,
            description="Card Sequence Number (AMEX)",
            padding_char="0",
            padding_direction="left",
        ),
        44: FieldDefinition(
            field_type=FieldType.LLVAR, max_length=99, description="Additional Response Data (AMEX)", padding_char=None
        ),
        47: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - National (AMEX)",
            padding_char=None,
        ),
        48: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Transaction Level Data (AMEX)", padding_char=None
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="ICC Data (AMEX Format)", padding_char=None
        ),
        # Network Management Fields
        60: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Network Data (AMEX)", padding_char=None
        ),
        61: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Other Terminal Data (AMEX)", padding_char=None
        ),
        63: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Card Level Results (AMEX)", padding_char=None
        ),
        76: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Confirmations/Authorizations (AMEX)",
            padding_char=None,
        ),
        # Extended Data Fields
        112: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Additional Data (AMEX)", padding_char=None
        ),
        124: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Sundry Data (AMEX)", padding_char=None
        ),
        125: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Extended Response Data (AMEX)", padding_char=None
        ),
    },
    CardNetwork.DISCOVER: {
        # Message Data Fields
        44: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=99,
            description="Additional Response Data (Discover)",
            padding_char=None,
        ),
        48: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - Private (Discover)",
            padding_char=None,
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="ICC Data (Discover Format)", padding_char=None
        ),
        # Network Management Fields
        62: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Network Specific Data (Discover)",
            padding_char=None,
        ),
        63: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Protocol Specific Data (Discover)",
            padding_char=None,
        ),
        95: FieldDefinition(
            field_type=FieldType.BINARY,
            max_length=28,  # 56 hex chars = 28 bytes
            description="Card Issuer Reference Data (Discover)",
            padding_char=None,
        ),
        111: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Network Details (Discover)", padding_char=None
        ),
    },
    CardNetwork.UNIONPAY: {
        # Card and Institution Fields
        33: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=28,
            description="Forwarding Institution ID (UnionPay)",
            padding_char=None,
        ),
        40: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=3,
            description="Service Restriction Code (UnionPay)",
            padding_char="0",
            padding_direction="left",
        ),
        41: FieldDefinition(
            field_type=FieldType.ALPHANUMERIC,
            max_length=8,
            description="Terminal ID (UnionPay Format)",
            padding_char=" ",
            padding_direction="right",
        ),
        42: FieldDefinition(
            field_type=FieldType.ALPHANUMERIC,
            max_length=15,
            description="Merchant ID (UnionPay Format)",
            padding_char=" ",
            padding_direction="right",
        ),
        # Transaction Data Fields
        48: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - Private (UnionPay)",
            padding_char=None,
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="ICC Data (UnionPay Format)", padding_char=None
        ),
        # Network Management Fields
        60: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Reserved National (UnionPay)", padding_char=None
        ),
        63: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Additional Data (UnionPay)", padding_char=None
        ),
        90: FieldDefinition(
            field_type=FieldType.NUMERIC,
            max_length=42,
            description="Original Data Elements (UnionPay)",
            padding_char="0",
            padding_direction="left",
        ),
        100: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=11,
            description="Receiving Institution ID (UnionPay)",
            padding_char=None,
        ),
        102: FieldDefinition(
            field_type=FieldType.LLVAR, max_length=28, description="Account Identifier 1 (UnionPay)", padding_char=None
        ),
        103: FieldDefinition(
            field_type=FieldType.LLVAR, max_length=28, description="Account Identifier 2 (UnionPay)", padding_char=None
        ),
        113: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="UnionPay Reserved", padding_char=None
        ),
    },
    CardNetwork.JCB: {
        # Terminal and Merchant Fields
        42: FieldDefinition(
            field_type=FieldType.ALPHANUMERIC,
            max_length=15,
            description="Card Acceptor ID Code (JCB)",
            padding_char=" ",
            padding_direction="right",
        ),
        48: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Additional Data - Private (JCB)",
            padding_char=None,
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=255, description="ICC System Related Data (JCB)", padding_char=None
        ),
        # Network Management Fields
        61: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Internal Data (JCB)", padding_char=None
        ),
        62: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Private Data (JCB)", padding_char=None
        ),
        63: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="SMS Private Data (JCB)", padding_char=None
        ),
        114: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Regional Data (JCB)", padding_char=None
        ),
    },
}

# Required fields by network (used for validation)
NETWORK_REQUIRED_FIELDS = {
    CardNetwork.VISA: [2, 3, 4, 11, 14, 22, 24, 25],
    CardNetwork.MASTERCARD: [2, 3, 4, 11, 22, 24, 25],
    CardNetwork.AMEX: [2, 3, 4, 11, 22, 25],
    CardNetwork.DISCOVER: [2, 3, 4, 11, 22],
    CardNetwork.JCB: [2, 3, 4, 11, 22, 25],
    CardNetwork.UNIONPAY: [2, 3, 4, 11, 22, 25, 49],
}

# Network-specific field format validations
NETWORK_FIELD_FORMATS = {
    CardNetwork.VISA: {
        44: r"^[0-9A-F]+$",  # Hex format for field 44
        105: r"^[A-Za-z0-9\s]+$",  # Alphanumeric with spaces
    },
    CardNetwork.MASTERCARD: {
        48: r"^MC[0-9]+$",  # MC prefix followed by numbers
        104: r"^MC\s.*$",  # MC prefix followed by space and any chars
    },
    CardNetwork.AMEX: {
        44: r"^[0-9A-F]+$",  # Hex format
        112: r"^AX.*$",  # AX prefix
    },
}

# Version-specific field variations
VERSION_SPECIFIC_FIELDS = {
    ISO8583Version.V1987: {
        # Base version - no overrides needed as this is our default
    },
    ISO8583Version.V1993: {
        # Field variations for 1993 version
        43: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=99,
            description="Card Acceptor Name/Location (1993)",
            padding_char=None,
        ),
        52: FieldDefinition(
            field_type=FieldType.BINARY,
            max_length=16,  # 16 bytes = 32 hex chars
            description="PIN Data (1993)",
            padding_char=None,
        ),
        53: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=48,
            description="Security Related Control Information (1993)",
            padding_char=None,
        ),
        54: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=255, description="Additional Amounts (1993)", padding_char=None
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=255, description="ICC System Related Data (1993)", padding_char=None
        ),
    },
    ISO8583Version.V2003: {
        # Field variations for 2003 version
        43: FieldDefinition(
            field_type=FieldType.LLVAR,
            max_length=256,
            description="Card Acceptor Name/Location (2003)",
            padding_char=None,
        ),
        52: FieldDefinition(
            field_type=FieldType.BINARY,
            max_length=32,  # 32 bytes = 64 hex chars
            description="PIN Data (2003)",
            padding_char=None,
        ),
        53: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=96,
            description="Security Related Control Information (2003)",
            padding_char=None,
        ),
        54: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=512, description="Additional Amounts (2003)", padding_char=None
        ),
        55: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="ICC System Related Data (2003)", padding_char=None
        ),
        56: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Original Data Elements (2003)", padding_char=None
        ),
        57: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Authorization Life Cycle Code (2003)",
            padding_char=None,
        ),
        58: FieldDefinition(
            field_type=FieldType.LLLVAR,
            max_length=999,
            description="Authorizing Agent Institution ID (2003)",
            padding_char=None,
        ),
        59: FieldDefinition(
            field_type=FieldType.LLLVAR, max_length=999, description="Transport Data (2003)", padding_char=None
        ),
    },
}


# Helper Functions


@lru_cache(maxsize=512)
def get_field_definition(
    field_number: int, network: CardNetwork | None = None, version: ISO8583Version = ISO8583Version.V1987
) -> FieldDefinition | None:
    """
    Get field definition considering network and version specifics.

    Args:
        field_number: The field number to look up
        network: Optional card network for network-specific definitions
        version: ISO8583 version

    Returns:
        FieldDefinition if found, None otherwise

    Priority order:
    1. Network-specific definition
    2. Version-specific definition
    3. Standard field definition

    Note: Results are cached for performance (lru_cache with 512 entries).
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
    """
    Check if MTI is valid.

    Args:
        mti: Message Type Indicator string

    Returns:
        bool: True if MTI is valid, False otherwise

    Validates:
    - Length is 4 digits
    - All characters are numeric
    - Each position contains valid values
    """
    if not mti or len(mti) != 4 or not mti.isdigit():
        return False

    # Validate version (position 1)
    version = mti[0]
    if version not in ["0", "1"]:
        return False

    # Validate message class (position 2)
    message_class = mti[1]
    if message_class not in [m.value for m in MessageClass]:
        return False

    # Validate message function (position 3)
    message_function = mti[2]
    if message_function not in [f.value for f in MessageFunction]:
        return False

    # Validate message origin (position 4)
    message_origin = mti[3]
    if message_origin not in [o.value for o in MessageOrigin]:
        return False

    return True


def get_network_required_fields(network: CardNetwork) -> list[int]:
    """
    Get list of required fields for a specific network.

    Args:
        network: Card network

    Returns:
        List of required field numbers
    """
    return NETWORK_REQUIRED_FIELDS.get(network, [])


def get_field_format_pattern(network: CardNetwork, field_number: int) -> str | None:
    """
    Get network-specific field format pattern.

    Args:
        network: Card network
        field_number: Field number

    Returns:
        Regex pattern string if exists, None otherwise
    """
    network_formats = NETWORK_FIELD_FORMATS.get(network, {})
    return network_formats.get(field_number)


def is_binary_field(field_def: FieldDefinition) -> bool:
    """
    Check if field is binary type.

    Args:
        field_def: Field definition

    Returns:
        bool: True if field is binary, False otherwise
    """
    return field_def.field_type == FieldType.BINARY
