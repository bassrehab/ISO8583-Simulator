"""Demo module with helper functions for notebooks and interactive use.

This module provides convenient functions for:
- Pretty-printing ISO 8583 messages
- Generating sample messages for different scenarios
- Explaining message components
"""

from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.emv import EMV_TAGS, build_emv_data, parse_emv_data
from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.types import (
    CardNetwork,
    ISO8583Message,
    get_field_definition,
)
from iso8583sim.core.validator import ISO8583Validator

# Shared instances for convenience
_builder = ISO8583Builder()
_parser = ISO8583Parser()
_validator = ISO8583Validator()


# Response code descriptions
RESPONSE_CODES = {
    "00": "Approved",
    "01": "Refer to card issuer",
    "02": "Refer to card issuer, special condition",
    "03": "Invalid merchant",
    "04": "Pick up card",
    "05": "Do not honor",
    "06": "Error",
    "10": "Partial approval",
    "12": "Invalid transaction",
    "13": "Invalid amount",
    "14": "Invalid card number",
    "15": "No such issuer",
    "30": "Format error",
    "41": "Lost card, pick up",
    "43": "Stolen card, pick up",
    "51": "Insufficient funds",
    "54": "Expired card",
    "55": "Incorrect PIN",
    "57": "Transaction not permitted",
    "61": "Exceeds withdrawal limit",
    "65": "Exceeds frequency limit",
    "75": "PIN tries exceeded",
    "91": "Issuer unavailable",
    "96": "System malfunction",
}

# Processing code descriptions
PROCESSING_CODES = {
    "00": "Purchase",
    "01": "Cash withdrawal",
    "09": "Purchase with cashback",
    "20": "Refund",
    "28": "Payment",
    "30": "Balance inquiry",
    "31": "Mini statement",
}


def pretty_print(message: ISO8583Message | str, show_raw: bool = False) -> None:
    """Pretty print an ISO 8583 message.

    Args:
        message: ISO8583Message object or raw message string
        show_raw: Whether to show the raw message bytes
    """
    if isinstance(message, str):
        message = _parser.parse(message)

    print("=" * 60)
    print(f"ISO 8583 Message - MTI: {message.mti}")
    print("=" * 60)

    # MTI breakdown
    mti = message.mti
    version_map = {"0": "1987", "1": "1993", "2": "2003"}
    class_map = {
        "1": "Authorization",
        "2": "Financial",
        "3": "File Action",
        "4": "Reversal",
        "5": "Reconciliation",
        "6": "Administrative",
        "7": "Fee Collection",
        "8": "Network Mgmt",
        "9": "Reserved",
    }
    function_map = {
        "0": "Request",
        "1": "Response",
        "2": "Advice",
        "3": "Advice Response",
        "4": "Notification",
        "5": "Notification Ack",
    }
    origin_map = {"0": "Acquirer", "1": "Acquirer Repeat", "2": "Issuer", "3": "Issuer Repeat", "4": "Other"}

    print("\nMTI Breakdown:")
    print(f"  Version:  {mti[0]} ({version_map.get(mti[0], 'Unknown')})")
    print(f"  Class:    {mti[1]} ({class_map.get(mti[1], 'Unknown')})")
    print(f"  Function: {mti[2]} ({function_map.get(mti[2], 'Unknown')})")
    print(f"  Origin:   {mti[3]} ({origin_map.get(mti[3], 'Unknown')})")

    if message.bitmap:
        print(f"\nBitmap: {message.bitmap}")

    print(f"\nFields ({len(message.fields) - 1} data elements):")
    print("-" * 60)

    for field_num in sorted(message.fields.keys()):
        if field_num == 0:
            continue  # Skip MTI

        value = message.fields[field_num]
        try:
            field_def = get_field_definition(field_num)
            desc = field_def.description[:35]
            ftype = field_def.field_type.name
        except (KeyError, AttributeError):
            desc = "Unknown"
            ftype = "?"

        # Mask PAN if present
        display_value = value
        if field_num == 2 and len(value) > 8:
            display_value = value[:6] + "*" * (len(value) - 10) + value[-4:]

        print(f"  F{field_num:03d} [{ftype:5s}] {desc:35s} = {display_value}")

    if show_raw and message.raw_message:
        print(f"\nRaw Message ({len(message.raw_message)} bytes):")
        print(message.raw_message)

    print("=" * 60)


def explain_field(field_number: int, value: str | None = None) -> None:
    """Explain a specific field's definition and optionally its value.

    Args:
        field_number: The field number to explain
        value: Optional field value to interpret
    """
    field_def = get_field_definition(field_number)
    if field_def is None:
        print(f"Field {field_number}: Unknown field")
        return

    print(f"Field {field_number}: {field_def.description}")
    print("-" * 50)
    print(f"  Type: {field_def.field_type.name}")
    print(f"  Max Length: {field_def.max_length}")

    # Special field interpretations
    if value:
        print(f"  Value: {value}")

        if field_number == 3:  # Processing code
            proc_type = PROCESSING_CODES.get(value[:2], "Unknown")
            print(f"  Interpretation: {proc_type}")

        elif field_number == 39:  # Response code
            resp_desc = RESPONSE_CODES.get(value, "Unknown")
            print(f"  Interpretation: {resp_desc}")

        elif field_number == 22:  # POS entry mode
            entry_modes = {
                "00": "Unknown",
                "01": "Manual",
                "02": "Mag stripe",
                "05": "Chip",
                "07": "Contactless chip",
                "09": "E-commerce",
                "91": "Contactless mag stripe",
            }
            entry = entry_modes.get(value[:2], "Unknown")
            pin_cap = {"0": "Unknown", "1": "Can accept PIN", "2": "Cannot accept PIN"}.get(value[2:3], "?")
            print(f"  Entry Mode: {entry}")
            print(f"  PIN Capability: {pin_cap}")

        elif field_number == 49:  # Currency
            currencies = {"840": "USD", "978": "EUR", "826": "GBP", "124": "CAD", "036": "AUD"}
            curr = currencies.get(value, "Unknown")
            print(f"  Currency: {curr}")


def generate_auth_request(
    pan: str = "4111111111111111",
    amount: int = 1000,
    stan: str = "123456",
    terminal_id: str = "TERM0001",
    merchant_id: str = "MERCHANT123456 ",
    network: CardNetwork | None = None,
) -> ISO8583Message:
    """Generate a sample authorization request.

    Args:
        pan: Primary Account Number
        amount: Transaction amount in cents
        stan: System Trace Audit Number
        terminal_id: Terminal ID (8 chars)
        merchant_id: Merchant ID (15 chars)
        network: Optional network type

    Returns:
        ISO8583Message object
    """
    return ISO8583Message(
        mti="0100",
        network=network,
        fields={
            0: "0100",
            2: pan,
            3: "000000",
            4: f"{amount:012d}",
            11: stan,
            14: "2612",
            22: "051",
            41: terminal_id,
            42: merchant_id,
            49: "840",
        },
    )


def generate_financial_request(
    pan: str = "4111111111111111",
    amount: int = 5000,
    stan: str = "654321",
    processing_code: str = "000000",
) -> ISO8583Message:
    """Generate a sample financial request (0200).

    Args:
        pan: Primary Account Number
        amount: Transaction amount in cents
        stan: System Trace Audit Number
        processing_code: Processing code (default: purchase)

    Returns:
        ISO8583Message object
    """
    return ISO8583Message(
        mti="0200",
        fields={
            0: "0200",
            2: pan,
            3: processing_code,
            4: f"{amount:012d}",
            11: stan,
            12: "143022",
            13: "1215",
            14: "2612",
            22: "051",
            41: "TERM0001",
            42: "MERCHANT123456 ",
            49: "840",
        },
    )


def generate_reversal(original: ISO8583Message, new_stan: str = "999999") -> ISO8583Message:
    """Generate a reversal message for an original transaction.

    Args:
        original: The original transaction message
        new_stan: New STAN for the reversal

    Returns:
        ISO8583Message reversal
    """
    return ISO8583Message(
        mti="0400",
        fields={
            0: "0400",
            2: original.fields.get(2, ""),
            3: original.fields.get(3, "000000"),
            4: original.fields.get(4, "000000000000"),
            11: new_stan,
            37: original.fields.get(37, ""),
            38: original.fields.get(38, ""),
            41: original.fields.get(41, ""),
            42: original.fields.get(42, ""),
        },
    )


def generate_network_message(message_type: str = "echo") -> ISO8583Message:
    """Generate a network management message.

    Args:
        message_type: Type of message - 'echo', 'signon', 'signoff', 'key_exchange'

    Returns:
        ISO8583Message object
    """
    codes = {
        "echo": "301",
        "signon": "001",
        "signoff": "002",
        "key_exchange": "161",
    }

    return ISO8583Message(
        mti="0800",
        fields={
            0: "0800",
            7: "1215143022",
            11: "000001",
            70: codes.get(message_type, "301"),
        },
    )


def generate_emv_auth(
    pan: str = "4111111111111111",
    amount: int = 10000,
    cryptogram: str = "AABBCCDD11223344",
) -> ISO8583Message:
    """Generate an EMV chip card authorization.

    Args:
        pan: Primary Account Number
        amount: Transaction amount in cents
        cryptogram: Application cryptogram (8 bytes hex)

    Returns:
        ISO8583Message with EMV data
    """
    emv_data = build_emv_data(
        {
            "9F26": cryptogram,
            "9F27": "80",  # ARQC
            "9F10": "06010A03A4B800",
            "9F37": "12345678",
            "9F36": "0001",
            "95": "0000000000",
            "9A": "251215",
            "9C": "00",
            "5F2A": "0840",
            "82": "1980",
            "9F1A": "0840",
        }
    )

    return ISO8583Message(
        mti="0100",
        fields={
            0: "0100",
            2: pan,
            3: "000000",
            4: f"{amount:012d}",
            11: "123456",
            14: "2612",
            22: "051",
            23: "001",
            35: f"{pan}=26125010000000000000",
            41: "TERM0001",
            42: "MERCHANT123456 ",
            49: "840",
            55: emv_data,
        },
    )


def build_and_parse(message: ISO8583Message) -> ISO8583Message:
    """Build a message to raw format and parse it back.

    Useful for testing roundtrip.

    Args:
        message: ISO8583Message to process

    Returns:
        Parsed message
    """
    raw = _builder.build(message)
    return _parser.parse(raw)


def validate(message: ISO8583Message | str) -> None:
    """Validate a message and print results.

    Args:
        message: ISO8583Message or raw message string
    """
    if isinstance(message, str):
        message = _parser.parse(message)

    errors = _validator.validate_message(message)

    print("Validation Result:")
    print("-" * 40)
    print(f"Valid: {'YES' if not errors else 'NO'}")

    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")


def explain_emv(emv_hex: str) -> None:
    """Parse and explain EMV data.

    Args:
        emv_hex: Hex-encoded EMV TLV data
    """
    parsed = parse_emv_data(emv_hex)

    print("EMV Data Analysis:")
    print("=" * 60)

    for tag, value in parsed.items():
        tag_name = EMV_TAGS.get(tag, "Unknown")
        print(f"\nTag {tag}: {tag_name}")
        print(f"  Value: {value}")
        print(f"  Length: {len(value)//2} bytes")

        # Special interpretations
        if tag == "9F27":  # CID
            cid_types = {"00": "AAC (Decline)", "40": "TC (Offline Approved)", "80": "ARQC (Go Online)"}
            print(f"  Meaning: {cid_types.get(value, 'Unknown')}")

        elif tag == "9C":  # Transaction type
            txn_types = {"00": "Purchase", "01": "Cash", "09": "Cashback", "20": "Refund"}
            print(f"  Meaning: {txn_types.get(value, 'Unknown')}")

        elif tag == "5F2A":  # Currency
            currencies = {"0840": "USD", "0978": "EUR", "0826": "GBP"}
            print(f"  Currency: {currencies.get(value, 'Unknown')}")


# Export all public functions
__all__ = [
    "pretty_print",
    "explain_field",
    "generate_auth_request",
    "generate_financial_request",
    "generate_reversal",
    "generate_network_message",
    "generate_emv_auth",
    "build_and_parse",
    "validate",
    "explain_emv",
    "RESPONSE_CODES",
    "PROCESSING_CODES",
]
