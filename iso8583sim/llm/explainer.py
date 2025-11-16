"""Message Explainer using LLM to provide human-readable explanations."""

from __future__ import annotations

from iso8583sim.core.parser import ISO8583Parser
from iso8583sim.core.types import ISO8583Message, get_field_definition
from iso8583sim.llm.base import LLMProvider
from iso8583sim.llm.prompts import (
    ISO8583_SYSTEM_PROMPT,
    format_error_explainer_prompt,
    format_explainer_prompt,
    format_field_explainer_prompt,
)
from iso8583sim.llm.providers import get_provider


class MessageExplainer:
    """Explains ISO 8583 messages in plain English using an LLM.

    This class uses an LLM provider to generate human-readable explanations
    of ISO 8583 messages, making them easier to understand for developers
    and analysts.

    Example:
        >>> explainer = MessageExplainer()  # Auto-detects provider
        >>> message = parser.parse("0100...")
        >>> print(explainer.explain(message))
        "This is a VISA authorization request for $100.00..."

        >>> # Or explain a raw message string
        >>> print(explainer.explain("0100702406C120E09000..."))

        >>> # Use a specific provider
        >>> explainer = MessageExplainer(provider="anthropic")
    """

    def __init__(self, provider: LLMProvider | str | None = None):
        """Initialize the MessageExplainer.

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

        self._parser = ISO8583Parser()

    @property
    def provider(self) -> LLMProvider:
        """Return the LLM provider being used."""
        return self._provider

    def explain(self, message: ISO8583Message | str, verbose: bool = False) -> str:
        """Explain an ISO 8583 message in plain English.

        Args:
            message: ISO8583Message object or raw message string to explain
            verbose: If True, include more technical details

        Returns:
            Human-readable explanation of the message
        """
        # Parse if string
        if isinstance(message, str):
            parsed = self._parser.parse(message)
            raw_message = message
        else:
            parsed = message
            raw_message = message.raw_message

        # Format prompt
        network = parsed.network.value if parsed.network else None
        prompt = format_explainer_prompt(
            mti=parsed.mti,
            fields=parsed.fields,
            network=network,
            raw_message=raw_message,
        )

        if verbose:
            prompt += "\n\nPlease include additional technical details about field formats and validation."

        # Get explanation from LLM
        return self._provider.complete(prompt, system=ISO8583_SYSTEM_PROMPT)

    def explain_field(self, field_number: int, value: str) -> str:
        """Explain a specific ISO 8583 field value.

        Args:
            field_number: The field number (e.g., 2, 39, 55)
            value: The field value to explain

        Returns:
            Human-readable explanation of the field and its value
        """
        # Get field definition for context
        field_def = get_field_definition(field_number)
        field_name = field_def.description if field_def else f"Field {field_number}"

        prompt = format_field_explainer_prompt(
            field_number=field_number,
            value=value,
            field_name=field_name,
        )

        return self._provider.complete(prompt, system=ISO8583_SYSTEM_PROMPT)

    def explain_error(self, error: str, message: ISO8583Message | str) -> str:
        """Explain a validation or parsing error in context.

        Args:
            error: The error message to explain
            message: The message that caused the error

        Returns:
            Human-readable explanation of the error and how to fix it
        """
        # Parse if string
        if isinstance(message, str):
            try:
                parsed = self._parser.parse(message)
            except Exception:
                # If parsing fails, create minimal context
                parsed = ISO8583Message(mti="????", fields={})
        else:
            parsed = message

        prompt = format_error_explainer_prompt(
            error=error,
            mti=parsed.mti,
            fields=parsed.fields,
        )

        return self._provider.complete(prompt, system=ISO8583_SYSTEM_PROMPT)

    def explain_response_code(self, code: str) -> str:
        """Explain an ISO 8583 response code.

        Args:
            code: The response code (e.g., "00", "51", "05")

        Returns:
            Human-readable explanation of the response code
        """
        prompt = f"""Explain ISO 8583 response code "{code}".

Include:
1. What this code means
2. Common scenarios when this response is returned
3. Recommended actions for the merchant/cardholder"""

        return self._provider.complete(prompt, system=ISO8583_SYSTEM_PROMPT)


__all__ = ["MessageExplainer"]
