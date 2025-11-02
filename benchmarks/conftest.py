"""Shared fixtures and utilities for benchmarks."""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.types import CardNetwork, ISO8583Message


def generate_test_messages(count: int, network: CardNetwork = None) -> list[str]:
    """Generate a batch of test messages for benchmarking.

    Args:
        count: Number of messages to generate
        network: Optional card network (VISA, MASTERCARD, etc.)

    Returns:
        List of raw ISO8583 message strings
    """
    builder = ISO8583Builder()
    messages = []

    # Base PAN prefix based on network
    pan_prefix = {
        CardNetwork.VISA: "4111111111",
        CardNetwork.MASTERCARD: "5111111111",
        CardNetwork.AMEX: "371111111111",
        None: "4111111111",
    }.get(network, "4111111111")

    for i in range(count):
        # Generate unique values for each message
        pan = f"{pan_prefix}{i:06d}"
        if len(pan) < 16:
            pan = pan.ljust(16, "0")
        elif len(pan) > 16:
            pan = pan[:16]

        fields = {
            0: "0100",
            2: pan,
            3: "000000",
            4: f"{(i % 100000):012d}",
            11: f"{i % 1000000:06d}",
            41: "TERM0001",
            42: "MERCHANT12345  ",
        }

        # Add network-required fields
        if network in (CardNetwork.VISA, CardNetwork.MASTERCARD):
            fields.update(
                {
                    14: "2512",  # Expiry
                    22: "051",  # POS entry mode
                    24: "001",  # Function code
                    25: "00",  # POS condition code
                }
            )

        msg = ISO8583Message(mti="0100", fields=fields, network=network)
        messages.append(builder.build(msg))

    return messages


def generate_emv_messages(count: int) -> list[str]:
    """Generate messages with EMV data for benchmarking."""
    builder = ISO8583Builder()
    messages = []

    emv_data = "9F0607A0000000031010"

    for i in range(count):
        msg = ISO8583Message(
            mti="0100",
            fields={
                0: "0100",
                2: f"411111111111{i:04d}",
                3: "000000",
                4: f"{(i % 100000):012d}",
                11: f"{i % 1000000:06d}",
                55: emv_data,
            },
        )
        messages.append(builder.build(msg))

    return messages
