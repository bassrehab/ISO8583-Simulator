"""Message Generator using LLM to create ISO 8583 messages from natural language."""

from __future__ import annotations

import json
import re

from iso8583sim.core.builder import ISO8583Builder
from iso8583sim.core.types import ISO8583Message
from iso8583sim.core.validator import ISO8583Validator
from iso8583sim.llm.base import GenerationError, LLMProvider
from iso8583sim.llm.prompts import ISO8583_SYSTEM_PROMPT, format_generator_prompt
from iso8583sim.llm.providers import get_provider


class MessageGenerator:
    """Generates ISO 8583 messages from natural language descriptions.

    This class uses an LLM to interpret natural language descriptions
    and generate valid ISO 8583 messages.

    Example:
        >>> generator = MessageGenerator()
        >>> message = generator.generate("$100 VISA purchase at a gas station")
        >>> print(message.mti)  # "0100"
        >>> print(message.fields[4])  # "000000010000"

        >>> # Generate without validation
        >>> message = generator.generate("refund $50", validate=False)
    """

    def __init__(self, provider: LLMProvider | str | None = None):
        """Initialize the MessageGenerator.

        Args:
            provider: LLM provider to use. Can be:
                - LLMProvider instance: Use directly
                - str: Provider name ('anthropic', 'openai', 'google', 'ollama')
                - None: Auto-detect available provider
        """
        if isinstance(provider, LLMProvider):
            self._provider = provider
        elif isinstance(provider, str):
            self._provider = get_provider(provider)
        else:
            self._provider = get_provider()

        self._builder = ISO8583Builder()
        self._validator = ISO8583Validator()

    @property
    def provider(self) -> LLMProvider:
        """Return the LLM provider being used."""
        return self._provider

    def generate(self, description: str, validate: bool = True) -> ISO8583Message:
        """Generate an ISO 8583 message from a natural language description.

        Args:
            description: Natural language description of the desired message
                        (e.g., "$100 VISA purchase at a gas station in NYC")
            validate: Whether to validate the generated message

        Returns:
            Valid ISO8583Message object

        Raises:
            GenerationError: If the message cannot be generated or validated
        """
        prompt = format_generator_prompt(description)

        # Get response from LLM
        response = self._provider.complete(prompt, system=ISO8583_SYSTEM_PROMPT)

        # Parse JSON from response
        try:
            message_data = self._extract_json(response)
        except json.JSONDecodeError as e:
            raise GenerationError(f"Failed to parse LLM response as JSON: {e}\nResponse: {response}") from e

        # Validate structure
        if "mti" not in message_data or "fields" not in message_data:
            raise GenerationError(f"Invalid message structure. Expected 'mti' and 'fields'. Got: {message_data.keys()}")

        # Create message
        try:
            # Convert field keys to integers
            fields = {}
            for key, value in message_data["fields"].items():
                field_num = int(key)
                fields[field_num] = str(value)

            # Ensure field 0 matches MTI
            fields[0] = message_data["mti"]

            message = ISO8583Message(
                mti=message_data["mti"],
                fields=fields,
            )
        except (KeyError, ValueError, TypeError) as e:
            raise GenerationError(f"Failed to create message from LLM response: {e}") from e

        # Validate if requested
        if validate:
            errors = self._validator.validate_message(message)
            if errors:
                # Try to fix common issues
                message = self._fix_common_issues(message, errors)
                errors = self._validator.validate_message(message)
                if errors:
                    raise GenerationError(f"Generated message failed validation: {errors}")

        return message

    def _extract_json(self, response: str) -> dict:
        """Extract JSON from LLM response.

        Handles responses that include markdown code blocks or extra text.

        Args:
            response: Raw LLM response

        Returns:
            Parsed JSON dictionary
        """
        # Try to find JSON in code block
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Try to find raw JSON
        json_match = re.search(r"\{[^{}]*\"mti\"[^{}]*\"fields\"[^{}]*\{.*?\}.*?\}", response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))

        # Try parsing the whole response
        return json.loads(response.strip())

    def _fix_common_issues(self, message: ISO8583Message, errors: list[str]) -> ISO8583Message:
        """Attempt to fix common validation issues.

        Args:
            message: The message with issues
            errors: List of validation errors

        Returns:
            Fixed message (may still have errors)
        """
        fields = message.fields.copy()

        for error in errors:
            # Fix field length issues
            if "length must be" in error.lower():
                # Extract field number and required length
                match = re.search(r"field\s+(\d+).*length.*?(\d+)", error.lower())
                if match:
                    field_num = int(match.group(1))
                    required_len = int(match.group(2))
                    if field_num in fields:
                        value = fields[field_num]
                        if len(value) < required_len:
                            # Pad with spaces or zeros based on field type
                            if value.isdigit():
                                fields[field_num] = value.zfill(required_len)
                            else:
                                fields[field_num] = value.ljust(required_len)
                        elif len(value) > required_len:
                            fields[field_num] = value[:required_len]

        return ISO8583Message(
            mti=message.mti,
            fields=fields,
            version=message.version,
            network=message.network,
        )

    def suggest_fields(self, partial_message: ISO8583Message) -> dict[int, str]:
        """Suggest missing fields for a partial message.

        Args:
            partial_message: Partial ISO8583Message with some fields populated

        Returns:
            Dictionary of suggested field values
        """
        # Format current fields
        fields_str = "\n".join(f"  F{num}: {value}" for num, value in sorted(partial_message.fields.items()))

        prompt = f"""Analyze this partial ISO 8583 message and suggest values for commonly required missing fields.

**Current Message:**
- MTI: {partial_message.mti}
- Network: {partial_message.network.value if partial_message.network else "Unknown"}
- Fields present:
{fields_str}

Suggest values for missing required fields. Return as JSON:
```json
{{
  "suggested_fields": {{
    "11": "123456",
    ...
  }},
  "reasoning": "explanation"
}}
```"""

        response = self._provider.complete(prompt, system=ISO8583_SYSTEM_PROMPT)

        try:
            data = self._extract_json(response)
            suggested = data.get("suggested_fields", {})
            # Convert keys to integers
            return {int(k): str(v) for k, v in suggested.items()}
        except (json.JSONDecodeError, KeyError, ValueError):
            return {}


__all__ = ["MessageGenerator"]
