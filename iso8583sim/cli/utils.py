# iso8583sim/cli/utils.py
import json
from datetime import datetime
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


def format_amount(amount: str) -> str:
    """Format numeric amount with proper padding"""
    try:
        # Remove any decimal points and convert to integer
        num = int(float(amount) * 100)
        # Return 12-digit zero-padded string
        return f"{num:012d}"
    except ValueError:
        raise typer.BadParameter("Invalid amount format") from None


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

    message = {
        "mti": mti,
        "fields": {
            11: now.strftime("%H%M%S"),  # STAN
            12: now.strftime("%H%M%S"),  # Time
            13: now.strftime("%m%d"),  # Date
        },
    }

    if pan:
        message["fields"][2] = validate_pan(pan)

    if amount:
        message["fields"][4] = format_amount(amount)

    if terminal_id:
        message["fields"][41] = terminal_id

    return message


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
