"""Prompt templates for ISO8583 LLM operations.

This module contains the system prompts and templates used by
MessageExplainer and MessageGenerator.
"""

from __future__ import annotations

# System prompt with ISO8583 context
ISO8583_SYSTEM_PROMPT = """You are an expert in ISO 8583 financial messaging protocol. You have deep knowledge of:

1. **Message Structure**:
   - MTI (Message Type Indicator): 4-digit code where:
     - Digit 1: Version (0=1987, 1=1993, 2=2003)
     - Digit 2: Message class (1=Auth, 2=Financial, 4=Reversal, 8=Network)
     - Digit 3: Function (0=Request, 1=Response, 2=Advice)
     - Digit 4: Origin (0=Acquirer, 1=Repeat, 2=Issuer)
   - Bitmap: 64/128 bits indicating which fields are present
   - Data Elements: Fields 2-128 with specific formats

2. **Common Fields**:
   - F2: Primary Account Number (PAN) - Card number
   - F3: Processing Code - Transaction type (00=Purchase, 01=Cash, 20=Refund)
   - F4: Transaction Amount - In minor units (cents)
   - F11: STAN - System Trace Audit Number
   - F12/13: Transaction Time/Date
   - F14: Expiration Date (YYMM)
   - F22: POS Entry Mode (05=Chip, 02=Swipe, 01=Manual)
   - F35: Track 2 Data
   - F38: Authorization Code
   - F39: Response Code (00=Approved, 51=Insufficient Funds)
   - F41: Terminal ID
   - F42: Merchant ID
   - F43: Merchant Name/Location
   - F49: Currency Code (840=USD, 978=EUR)
   - F55: EMV/Chip Data (TLV encoded)

3. **Card Networks**:
   - VISA: PANs starting with 4
   - Mastercard: PANs starting with 51-55 or 2221-2720
   - AMEX: PANs starting with 34 or 37
   - Discover: PANs starting with 6011 or 65
   - UnionPay: PANs starting with 62

4. **Response Codes** (Field 39):
   - 00: Approved
   - 01: Refer to issuer
   - 05: Do not honor
   - 12: Invalid transaction
   - 14: Invalid card number
   - 51: Insufficient funds
   - 54: Expired card
   - 55: Incorrect PIN
   - 91: Issuer unavailable

Always provide accurate, technical explanations while being accessible to users who may not be ISO 8583 experts."""


# Template for explaining messages
EXPLAINER_PROMPT_TEMPLATE = """Analyze and explain this ISO 8583 message in plain English.

**Raw Message (if available):** {raw_message}

**Parsed Message:**
- MTI: {mti}
- Network: {network}
- Fields:
{fields}

Please explain:
1. What type of transaction this is (based on MTI and processing code)
2. The key details (amount, card type, merchant, etc.)
3. Any notable aspects or potential issues
4. The expected response or outcome

Keep the explanation concise but informative. Use bullet points for clarity."""


# Template for explaining a specific field
FIELD_EXPLAINER_TEMPLATE = """Explain this ISO 8583 field value:

Field {field_number}: {field_name}
Value: {value}

Provide:
1. What this field represents
2. How to interpret the specific value
3. Any relevant context (e.g., if it's a code, what the code means)"""


# Template for explaining errors
ERROR_EXPLAINER_TEMPLATE = """Explain this ISO 8583 validation/parsing error:

**Error:** {error}

**Message Context:**
- MTI: {mti}
- Fields present: {fields}

Explain:
1. What the error means
2. Why it occurred
3. How to fix it"""


# Template for generating messages
GENERATOR_PROMPT_TEMPLATE = """Generate an ISO 8583 message based on this description:

**Description:** {description}

Generate a valid ISO 8583 message with the following JSON structure:
```json
{{
  "mti": "0100",
  "fields": {{
    "2": "4111111111111111",
    "3": "000000",
    ...
  }}
}}
```

Requirements:
1. Use appropriate MTI for the transaction type
2. Include all required fields for the transaction
3. Use realistic but test-safe values (e.g., test PANs like 4111111111111111)
4. Format amounts in cents (e.g., $100.00 = "000000010000")
5. Use proper field lengths and formats

Return ONLY the JSON object, no additional text."""


# Template for suggesting missing fields
FIELD_SUGGESTER_TEMPLATE = """Analyze this partial ISO 8583 message and suggest missing fields:

**Current Message:**
- MTI: {mti}
- Network: {network}
- Fields present:
{fields}

Based on the MTI and network, suggest values for commonly required missing fields.
Return as JSON:
```json
{{
  "suggested_fields": {{
    "11": "123456",
    ...
  }},
  "reasoning": "explanation of why these fields are suggested"
}}
```"""


def format_fields_for_prompt(fields: dict[int, str], max_fields: int = 20) -> str:
    """Format message fields for inclusion in prompts.

    Args:
        fields: Dictionary of field numbers to values
        max_fields: Maximum number of fields to include

    Returns:
        Formatted string representation of fields
    """
    lines = []
    sorted_fields = sorted(fields.items())

    for i, (num, value) in enumerate(sorted_fields):
        if i >= max_fields:
            lines.append(f"  ... and {len(sorted_fields) - max_fields} more fields")
            break
        # Mask PAN if present
        display_value = value
        if num == 2 and len(value) > 8:
            display_value = value[:6] + "*" * (len(value) - 10) + value[-4:]
        lines.append(f"  F{num:03d}: {display_value}")

    return "\n".join(lines)


def format_explainer_prompt(
    mti: str,
    fields: dict[int, str],
    network: str | None = None,
    raw_message: str | None = None,
) -> str:
    """Format the explainer prompt with message details.

    Args:
        mti: Message Type Indicator
        fields: Message fields
        network: Optional detected network
        raw_message: Optional raw message string

    Returns:
        Formatted prompt string
    """
    return EXPLAINER_PROMPT_TEMPLATE.format(
        mti=mti,
        network=network or "Unknown",
        fields=format_fields_for_prompt(fields),
        raw_message=raw_message[:100] + "..." if raw_message and len(raw_message) > 100 else raw_message or "N/A",
    )


def format_generator_prompt(description: str) -> str:
    """Format the generator prompt with the user's description.

    Args:
        description: Natural language description of desired message

    Returns:
        Formatted prompt string
    """
    return GENERATOR_PROMPT_TEMPLATE.format(description=description)


def format_field_explainer_prompt(field_number: int, value: str, field_name: str = "Unknown") -> str:
    """Format the field explainer prompt.

    Args:
        field_number: The field number
        value: The field value
        field_name: Optional field name/description

    Returns:
        Formatted prompt string
    """
    return FIELD_EXPLAINER_TEMPLATE.format(
        field_number=field_number,
        field_name=field_name,
        value=value,
    )


def format_error_explainer_prompt(error: str, mti: str, fields: dict[int, str]) -> str:
    """Format the error explainer prompt.

    Args:
        error: The error message
        mti: Message Type Indicator
        fields: Message fields

    Returns:
        Formatted prompt string
    """
    return ERROR_EXPLAINER_TEMPLATE.format(
        error=error,
        mti=mti,
        fields=list(fields.keys()),
    )


__all__ = [
    "ISO8583_SYSTEM_PROMPT",
    "EXPLAINER_PROMPT_TEMPLATE",
    "GENERATOR_PROMPT_TEMPLATE",
    "FIELD_EXPLAINER_TEMPLATE",
    "ERROR_EXPLAINER_TEMPLATE",
    "FIELD_SUGGESTER_TEMPLATE",
    "format_fields_for_prompt",
    "format_explainer_prompt",
    "format_generator_prompt",
    "format_field_explainer_prompt",
    "format_error_explainer_prompt",
]
