"""Valid sample messages for tests and demos."""

from __future__ import annotations

from .codes import detect_network_from_pan
from .types import CardNetwork, ISO8583Message

# subhadipmitra@: Well-known public test card numbers. They pass Luhn checks and are
# never real accounts, so generated messages are safe to share and paste into chats.
SAMPLE_PANS = {
    CardNetwork.VISA: "4111111111111111",
    CardNetwork.MASTERCARD: "5555555555554444",
    CardNetwork.AMEX: "378282246310005",
    CardNetwork.DISCOVER: "6011111111111117",
    CardNetwork.JCB: "3530111333300000",
    CardNetwork.UNIONPAY: "6200000000000005",
}

MESSAGE_TYPES = {"auth": "0100", "financial": "0200", "echo": "0800"}


def sample_message(
    message_type: str = "auth",
    network: CardNetwork | None = None,
    pan: str | None = None,
    amount_minor_units: int = 1000,
    currency: str = "840",
    stan: str = "123456",
) -> ISO8583Message:
    """Create a valid 1987 test message.

    Args:
        message_type: "auth" (0100), "financial" (0200) or "echo" (0800)
        network: Card network. Detected from the PAN when omitted.
        pan: Card number. A well-known test PAN for the network is used when omitted.
        amount_minor_units: Amount in minor units (1000 = 10.00)
        currency: ISO 4217 numeric currency code
        stan: System trace audit number

    Returns:
        The message, ready to build
    """
    if message_type not in MESSAGE_TYPES:
        raise ValueError(f"Unknown message_type {message_type!r}. Use one of: {', '.join(MESSAGE_TYPES)}.")
    mti = MESSAGE_TYPES[message_type]

    if message_type == "echo":
        return ISO8583Message(mti=mti, fields={7: "1215143022", 11: stan, 70: "301"})

    card = pan or SAMPLE_PANS[network or CardNetwork.VISA]
    network = network or detect_network_from_pan(card)
    # subhadipmitra@: This field set covers the union of every network's required fields
    # (NETWORK_REQUIRED_FIELDS), including 24 (NII) and 25 (POS condition code), so the
    # message validates whichever network is chosen.
    fields = {
        2: card,
        3: "000000",
        4: f"{amount_minor_units:012d}",
        11: stan,
        14: "2612",
        22: "051",
        24: "001",
        25: "00",
        41: "TERM0001",
        42: "MERCHANT123456 ",
        49: currency,
    }
    if message_type == "financial":
        fields.update({12: "143022", 13: "1215"})
    return ISO8583Message(mti=mti, fields=fields, network=network)
