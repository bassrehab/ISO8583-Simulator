"""EMV (Europay, Mastercard, Visa) TLV data handling.

This module provides functions for parsing and building EMV Tag-Length-Value
encoded data, commonly found in ISO 8583 Field 55.
"""

from __future__ import annotations

# EMV Tag definitions
EMV_TAGS: dict[str, str] = {
    # Template tags
    "70": "EMV Proprietary Template",
    "71": "Issuer Script Template 1",
    "72": "Issuer Script Template 2",
    "77": "Response Message Template Format 2",
    "80": "Response Message Template Format 1",
    # Primitive tags
    "42": "Issuer Identification Number (IIN)",
    "4F": "Application Identifier (AID)",
    "50": "Application Label",
    "57": "Track 2 Equivalent Data",
    "5A": "Application PAN",
    "5F20": "Cardholder Name",
    "5F24": "Application Expiration Date",
    "5F25": "Application Effective Date",
    "5F28": "Issuer Country Code",
    "5F2A": "Transaction Currency Code",
    "5F2D": "Language Preference",
    "5F34": "PAN Sequence Number",
    "82": "Application Interchange Profile (AIP)",
    "84": "Dedicated File (DF) Name",
    "87": "Application Priority Indicator",
    "88": "Short File Identifier (SFI)",
    "89": "Authorization Code",
    "8A": "Authorization Response Code",
    "8C": "Card Risk Management Data Object List 1 (CDOL1)",
    "8D": "Card Risk Management Data Object List 2 (CDOL2)",
    "8E": "Cardholder Verification Method (CVM) List",
    "8F": "Certification Authority Public Key Index",
    "90": "Issuer Public Key Certificate",
    "91": "Issuer Authentication Data",
    "92": "Issuer Public Key Remainder",
    "93": "Signed Static Application Data",
    "94": "Application File Locator (AFL)",
    "95": "Terminal Verification Results (TVR)",
    "97": "Transaction Certificate Data Object List (TDOL)",
    "98": "Transaction Certificate (TC) Hash Value",
    "99": "Transaction PIN Data",
    "9A": "Transaction Date",
    "9B": "Transaction Status Information (TSI)",
    "9C": "Transaction Type",
    "9D": "Directory Definition File (DDF) Name",
    "9F01": "Acquirer Identifier",
    "9F02": "Amount, Authorized (Numeric)",
    "9F03": "Amount, Other (Numeric)",
    "9F04": "Amount, Other (Binary)",
    "9F05": "Application Discretionary Data",
    "9F06": "Application Identifier (AID) - Terminal",
    "9F07": "Application Usage Control",
    "9F08": "Application Version Number - Card",
    "9F09": "Application Version Number - Terminal",
    "9F0B": "Cardholder Name Extended",
    "9F0D": "Issuer Action Code - Default",
    "9F0E": "Issuer Action Code - Denial",
    "9F0F": "Issuer Action Code - Online",
    "9F10": "Issuer Application Data",
    "9F11": "Issuer Code Table Index",
    "9F12": "Application Preferred Name",
    "9F13": "Last Online ATC Register",
    "9F14": "Lower Consecutive Offline Limit",
    "9F15": "Merchant Category Code",
    "9F16": "Merchant Identifier",
    "9F17": "PIN Try Counter",
    "9F18": "Issuer Script Identifier",
    "9F1A": "Terminal Country Code",
    "9F1B": "Terminal Floor Limit",
    "9F1C": "Terminal Identification",
    "9F1D": "Terminal Risk Management Data",
    "9F1E": "Interface Device (IFD) Serial Number",
    "9F1F": "Track 1 Discretionary Data",
    "9F20": "Track 2 Discretionary Data",
    "9F21": "Transaction Time",
    "9F22": "Certification Authority Public Key Index - Terminal",
    "9F23": "Upper Consecutive Offline Limit",
    "9F26": "Application Cryptogram",
    "9F27": "Cryptogram Information Data",
    "9F32": "Issuer Public Key Exponent",
    "9F33": "Terminal Capabilities",
    "9F34": "Cardholder Verification Method (CVM) Results",
    "9F35": "Terminal Type",
    "9F36": "Application Transaction Counter (ATC)",
    "9F37": "Unpredictable Number",
    "9F38": "Processing Options Data Object List (PDOL)",
    "9F39": "POS Entry Mode",
    "9F3A": "Amount, Reference Currency",
    "9F3B": "Application Reference Currency",
    "9F3C": "Transaction Reference Currency Code",
    "9F3D": "Transaction Reference Currency Exponent",
    "9F40": "Additional Terminal Capabilities",
    "9F41": "Transaction Sequence Counter",
    "9F42": "Application Currency Code",
    "9F43": "Application Reference Currency Exponent",
    "9F44": "Application Currency Exponent",
    "9F45": "Data Authentication Code",
    "9F46": "ICC Public Key Certificate",
    "9F47": "ICC Public Key Exponent",
    "9F48": "ICC Public Key Remainder",
    "9F49": "Dynamic Data Authentication Data Object List (DDOL)",
    "9F4A": "Static Data Authentication Tag List",
    "9F4B": "Signed Dynamic Application Data",
    "9F4C": "ICC Dynamic Number",
    "9F4D": "Log Entry",
    "9F4E": "Merchant Name and Location",
    "9F4F": "Log Format",
    "9F53": "Transaction Category Code",
    "9F5B": "Issuer Script Results",
    "9F66": "Terminal Transaction Qualifiers (TTQ)",
    "9F6C": "Card Transaction Qualifiers (CTQ)",
    "9F6E": "Form Factor Indicator",
    "DF01": "Proprietary Data Element",
}


def parse_emv_data(data: str) -> dict[str, str]:
    """Parse EMV TLV data into a dictionary of tags and values.

    Args:
        data: Hex-encoded EMV TLV data

    Returns:
        Dictionary mapping tag strings to value strings (hex-encoded)

    Raises:
        ValueError: If data is malformed
    """
    result: dict[str, str] = {}
    pos = 0
    data = data.upper()

    while pos < len(data):
        # Parse tag (1 or 2 bytes)
        if pos + 2 > len(data):
            break

        tag_byte1 = int(data[pos : pos + 2], 16)
        pos += 2

        # Check if tag is 2 bytes (if low 5 bits of first byte are all 1s)
        if (tag_byte1 & 0x1F) == 0x1F:
            if pos + 2 > len(data):
                break
            tag = f"{tag_byte1:02X}{data[pos:pos+2]}"
            pos += 2
        else:
            tag = f"{tag_byte1:02X}"

        # Parse length (1, 2, or 3 bytes)
        if pos + 2 > len(data):
            break

        length_byte1 = int(data[pos : pos + 2], 16)
        pos += 2

        if length_byte1 <= 0x7F:
            # Short form: length is in this byte
            length = length_byte1
        elif length_byte1 == 0x81:
            # Long form: next byte is length
            if pos + 2 > len(data):
                break
            length = int(data[pos : pos + 2], 16)
            pos += 2
        elif length_byte1 == 0x82:
            # Long form: next 2 bytes are length
            if pos + 4 > len(data):
                break
            length = int(data[pos : pos + 4], 16)
            pos += 4
        else:
            # Invalid length encoding
            break

        # Parse value
        value_end = pos + (length * 2)
        if value_end > len(data):
            # Truncated value - take what we have
            value_end = len(data)

        value = data[pos:value_end]
        pos = value_end

        result[tag] = value

    return result


def build_emv_data(tags: dict[str, str]) -> str:
    """Build EMV TLV data from a dictionary of tags and values.

    Args:
        tags: Dictionary mapping tag strings to value strings (hex-encoded)

    Returns:
        Hex-encoded EMV TLV data string
    """
    result = []

    for tag, value in tags.items():
        # Normalize tag and value
        tag = tag.upper()
        value = value.upper()

        # Add tag
        result.append(tag)

        # Calculate length (in bytes)
        length = len(value) // 2

        # Encode length
        if length <= 0x7F:
            result.append(f"{length:02X}")
        elif length <= 0xFF:
            result.append(f"81{length:02X}")
        else:
            result.append(f"82{length:04X}")

        # Add value
        result.append(value)

    return "".join(result)


def get_tag_name(tag: str) -> str:
    """Get the description of an EMV tag.

    Args:
        tag: Tag identifier (hex string)

    Returns:
        Description of the tag, or "Unknown" if not found
    """
    return EMV_TAGS.get(tag.upper(), "Unknown")


def explain_tvr(tvr_hex: str) -> list[str]:
    """Explain Terminal Verification Results.

    Args:
        tvr_hex: 5-byte TVR as hex string (10 characters)

    Returns:
        List of issues/flags that are set
    """
    issues = []

    if len(tvr_hex) < 10:
        tvr_hex = tvr_hex.ljust(10, "0")

    tvr_bytes = bytes.fromhex(tvr_hex)

    # Byte 1
    byte1_flags = [
        (0x80, "Offline data authentication not performed"),
        (0x40, "SDA failed"),
        (0x20, "ICC data missing"),
        (0x10, "Card appears on terminal exception file"),
        (0x08, "DDA failed"),
        (0x04, "CDA failed"),
    ]

    # Byte 2
    byte2_flags = [
        (0x80, "ICC and terminal have different application versions"),
        (0x40, "Expired application"),
        (0x20, "Application not yet effective"),
        (0x10, "Requested service not allowed for card product"),
        (0x08, "New card"),
    ]

    # Byte 3
    byte3_flags = [
        (0x80, "Cardholder verification was not successful"),
        (0x40, "Unrecognized CVM"),
        (0x20, "PIN Try Limit exceeded"),
        (0x10, "PIN entry required and PIN pad not present or not working"),
        (0x08, "PIN entry required, PIN pad present, but PIN was not entered"),
        (0x04, "Online PIN entered"),
    ]

    # Byte 4
    byte4_flags = [
        (0x80, "Transaction exceeds floor limit"),
        (0x40, "Lower consecutive offline limit exceeded"),
        (0x20, "Upper consecutive offline limit exceeded"),
        (0x10, "Transaction selected randomly for online processing"),
        (0x08, "Merchant forced transaction online"),
    ]

    # Byte 5
    byte5_flags = [
        (0x80, "Default TDOL used"),
        (0x40, "Issuer authentication failed"),
        (0x20, "Script processing failed before final GENERATE AC"),
        (0x10, "Script processing failed after final GENERATE AC"),
    ]

    all_flags = [byte1_flags, byte2_flags, byte3_flags, byte4_flags, byte5_flags]

    for i, byte_flags in enumerate(all_flags):
        if i < len(tvr_bytes):
            for mask, description in byte_flags:
                if tvr_bytes[i] & mask:
                    issues.append(description)

    return issues


def explain_cid(cid_hex: str) -> str:
    """Explain Cryptogram Information Data.

    Args:
        cid_hex: CID byte as hex string

    Returns:
        Description of the cryptogram type
    """
    cid_value = int(cid_hex, 16) if cid_hex else 0
    cryptogram_type = (cid_value >> 6) & 0x03

    types = {
        0: "AAC (Application Authentication Cryptogram) - Transaction declined",
        1: "TC (Transaction Certificate) - Transaction approved offline",
        2: "ARQC (Authorization Request Cryptogram) - Online authorization requested",
        3: "RFU (Reserved for Future Use)",
    }

    return types.get(cryptogram_type, "Unknown")


__all__ = [
    "EMV_TAGS",
    "parse_emv_data",
    "build_emv_data",
    "get_tag_name",
    "explain_tvr",
    "explain_cid",
]
