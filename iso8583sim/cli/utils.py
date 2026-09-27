# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

# iso8583sim/cli/utils.py
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import typer


def load_json_file(file_path: Path) -> dict[str, Any]:
    """Load and validate JSON file"""
    try:
        with open(file_path) as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise typer.BadParameter(f"Invalid JSON file: {file_path}") from None
    except FileNotFoundError:
        raise typer.BadParameter(f"File not found: {file_path}") from None


def save_json_file(data: dict[str, Any], file_path: Path):
    """Save data to JSON file"""
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        raise typer.BadParameter(f"Error saving file: {e}") from None


def generate_output_filename(prefix: str, suffix: str = "") -> str:
    """Generate unique output filename with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}{suffix}"


def ensure_directory(directory: Path):
    """Ensure directory exists"""
    directory.mkdir(parents=True, exist_ok=True)


def validate_file_path(file_path: Path, create_dir: bool = True) -> Path:
    """Validate and prepare file path"""
    if create_dir:
        ensure_directory(file_path.parent)
    return file_path


def format_amount(amount: str, exponent: int = 2) -> str:
    """Format an amount for field 4: 12 digits in minor units.

    Args:
        amount: Minor units as digits ("1000" is 10.00), or a decimal amount ("10.00")
        exponent: Number of decimal places in the currency (2 for USD, 0 for JPY)

    Returns:
        The amount as a 12-digit, zero-padded string
    """
    value = amount.strip()
    # subhadipmitra@: Plain digits are already minor units, as the --amount help and the docs
    # say. This used to multiply every input by 100, and generate applied it twice, so the
    # default 000000001000 (10.00) went out as 100000.00.
    if value.isdigit():
        minor = int(value)
    else:
        # subhadipmitra@: A decimal amount is scaled with Decimal, not float, so "0.29" is
        # exactly 29 minor units rather than 28.999... truncated to 28.
        try:
            major = Decimal(value)
        except InvalidOperation:
            raise typer.BadParameter(
                f"Invalid amount {amount!r}: use minor units (1000) or a decimal (10.00)"
            ) from None
        if not major.is_finite() or major < 0:
            raise typer.BadParameter(f"Invalid amount {amount!r}: must be zero or more") from None
        scaled = major.scaleb(exponent)
        if scaled != scaled.to_integral_value():
            raise typer.BadParameter(
                f"Invalid amount {amount!r}: this currency has {exponent} decimal places"
            ) from None
        minor = int(scaled)

    if minor >= 10**12:
        raise typer.BadParameter(f"Invalid amount {amount!r}: field 4 holds at most 12 digits")
    return f"{minor:012d}"


def validate_pan(pan: str) -> str:
    """Validate PAN using Luhn algorithm"""
    if not pan.isdigit():
        raise typer.BadParameter("PAN must contain only digits")

    # Luhn algorithm check
    digits = [int(d) for d in pan]
    checksum = 0
    for i in range(len(digits) - 2, -1, -1):
        d = digits[i]
        if i % 2 == len(digits) % 2:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d

    if (checksum + digits[-1]) % 10 != 0:
        raise typer.BadParameter("Invalid PAN (failed Luhn check)")

    return pan


def create_template_message(
    mti: str, pan: str | None = None, amount: str | None = None, terminal_id: str | None = None
) -> dict[str, Any]:
    """Create template message with common fields"""
    now = datetime.now()

    fields: dict[int, str] = {
        11: now.strftime("%H%M%S"),  # STAN
        12: now.strftime("%H%M%S"),  # Time
        13: now.strftime("%m%d"),  # Date
    }

    if pan:
        fields[2] = validate_pan(pan)

    # subhadipmitra@: The amount arrives already formatted for field 4 (see format_amount),
    # so it is stored as is. Formatting it again here was what doubled the scaling bug.
    if amount:
        fields[4] = amount

    if terminal_id:
        fields[41] = terminal_id

    return {"mti": mti, "fields": fields}


def get_response_code_description(code: str) -> str:
    """Get description for response code"""
    descriptions = {
        "00": "Approved",
        "01": "Refer to card issuer",
        "02": "Refer to card issuer, special condition",
        "03": "Invalid merchant",
        "04": "Pick up card",
        "05": "Do not honor",
        "06": "Error",
        "07": "Pick up card, special condition",
        "08": "Honor with identification",
        "09": "Request in progress",
        "10": "Approved, partial",
        "11": "Approved, VIP",
        "12": "Invalid transaction",
        "13": "Invalid amount",
        "14": "Invalid card number",
        "15": "No such issuer",
    }
    return descriptions.get(code, "Unknown response code")
