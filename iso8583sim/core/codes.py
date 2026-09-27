"""Reference tables and lookups for ISO 8583 code values."""

from .types import CardNetwork

# Response code descriptions (field 39)
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

# Processing code descriptions (first two digits of field 3)
PROCESSING_CODES = {
    "00": "Purchase",
    "01": "Cash withdrawal",
    "09": "Purchase with cashback",
    "20": "Refund",
    "28": "Payment",
    "30": "Balance inquiry",
    "31": "Mini statement",
}

# Network management codes (field 70)
NETWORK_MANAGEMENT_CODES = {
    "001": "Sign-on",
    "002": "Sign-off",
    "161": "Key exchange",
    "301": "Echo test",
}

# Common ISO 4217 currency codes (field 49)
# subhadipmitra@: Each entry is (alpha code, minor unit exponent). The exponent says where the
# decimal point goes in field 4, which is sent in minor units: 1000 is 10.00 USD but 1000 JPY.
CURRENCY_CODES = {
    "036": ("AUD", 2),
    "124": ("CAD", 2),
    "156": ("CNY", 2),
    "344": ("HKD", 2),
    "356": ("INR", 2),
    "392": ("JPY", 0),
    "410": ("KRW", 0),
    "458": ("MYR", 2),
    "554": ("NZD", 2),
    "608": ("PHP", 2),
    "702": ("SGD", 2),
    "756": ("CHF", 2),
    "764": ("THB", 2),
    "826": ("GBP", 2),
    "840": ("USD", 2),
    "978": ("EUR", 2),
}


def detect_network_from_pan(pan: str) -> CardNetwork | None:
    """Detect the card network from a PAN's issuer identification prefix.

    Args:
        pan: Primary Account Number (digits only)

    Returns:
        The matching CardNetwork, or None if the prefix is not recognised
    """
    # subhadipmitra@: Network ranges are defined on the first six digits (the BIN), so shorter
    # or non-numeric input cannot be classified.
    if not pan.isdigit() or len(pan) < 6:
        return None

    two = int(pan[:2])
    three = int(pan[:3])
    four = int(pan[:4])

    if pan.startswith("4"):
        return CardNetwork.VISA
    # subhadipmitra@: Mastercard also issues from the 2-series range 2221 to 2720, which the
    # old prefix check missed.
    if 51 <= two <= 55 or 2221 <= four <= 2720:
        return CardNetwork.MASTERCARD
    if two in (34, 37):
        return CardNetwork.AMEX
    # subhadipmitra@: Discover issues from 6011, 644 to 649 and 65. None of these overlap
    # UnionPay's 62, so the order of the two checks doesn't matter.
    if four == 6011 or two == 65 or 644 <= three <= 649:
        return CardNetwork.DISCOVER
    # subhadipmitra@: JCB is 3528 to 3589, not every 35 prefix.
    if 3528 <= four <= 3589:
        return CardNetwork.JCB
    if two == 62:
        return CardNetwork.UNIONPAY
    return None
