# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""REST API for iso8583sim, built with FastAPI.

Run with `iso8583sim web` or `uvicorn iso8583sim.web.app:app`. Interactive docs are served
at /docs and the OpenAPI schema at /openapi.json.

Set ISO8583SIM_PUBLIC=1 to run it as a public demo: LLM features are turned off, so nobody
can spend the server's API keys, and browsers on any site may call it (CORS).
"""

from __future__ import annotations

import os
from typing import Annotated, Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .. import __version__
from ..core.builder import ISO8583Builder
from ..core.convert import convert_message
from ..core.describe import decode_emv_tags, describe_message, field_entries
from ..core.parser import ISO8583Parser
from ..core.samples import sample_message
from ..core.types import CardNetwork, ISO8583Error, ISO8583Message, ISO8583Version
from ..core.validator import ISO8583Validator

# subhadipmitra@: Input size limits. The longest field is LLLVAR (999 characters, or 1998
# when binary data is written as hex), so real messages stay far below these. They stop a
# single request from making the server parse megabytes of data.
MAX_MESSAGE_LENGTH = 32_768
MAX_FIELD_LENGTH = 1_998
MAX_DESCRIPTION_LENGTH = 2_000

# Request and response models


class FieldValue(BaseModel):
    number: int
    name: str
    value: str


class MessageRequest(BaseModel):
    message: str = Field(
        ...,
        max_length=MAX_MESSAGE_LENGTH,
        description="Raw ISO 8583 message: MTI, hex bitmap, then field data",
    )
    network: CardNetwork | None = Field(None, description="Card network. Detected from the PAN when omitted.")
    version: ISO8583Version = ISO8583Version.V1987


class ParseResponse(BaseModel):
    mti: str
    version: ISO8583Version
    network: CardNetwork | None
    bitmap: str | None
    fields: list[FieldValue]
    emv: list[dict[str, Any]] | None = None


class BuildRequest(BaseModel):
    mti: str = Field(..., pattern=r"^\d{4}$", examples=["0100"])
    # subhadipmitra@: JSON object keys are strings. Pydantic converts "2" to 2 here, which is
    # what ISO8583Message expects, so clients can send {"2": "4111..."} naturally.
    fields: dict[int, Annotated[str, Field(max_length=MAX_FIELD_LENGTH)]] = Field(
        ..., max_length=128, examples=[{"2": "4111111111111111", "3": "000000", "4": "000000001000"}]
    )
    network: CardNetwork | None = None
    version: ISO8583Version = ISO8583Version.V1987


class BuildResponse(BaseModel):
    message: str
    length: int


class ValidateRequest(MessageRequest):
    against: list[CardNetwork] | None = Field(
        None, description="Also check these networks' rules. An empty list checks every network."
    )


class NetworkResult(BaseModel):
    passed: bool
    errors: list[str]


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[str]
    networks: dict[CardNetwork, NetworkResult] | None = None


class ExplainRequest(MessageRequest):
    llm: bool = Field(False, description="Use an LLM instead of the rule-based summary")
    provider: str | None = Field(None, description="LLM provider: anthropic, openai, google or ollama")
    model: str | None = None


class ExplainResponse(BaseModel):
    summary: str
    source: str = Field(..., description='"rules", or "llm:<provider>/<model>"')
    mti: str
    fields: list[FieldValue]


class GenerateRequest(BaseModel):
    message_type: Literal["auth", "financial", "echo"] = "auth"
    network: CardNetwork | None = None
    pan: str | None = Field(None, pattern=r"^\d{12,19}$")
    amount_minor_units: int = Field(1000, ge=0, le=999_999_999_999)
    currency: str = Field("840", pattern=r"^\d{3}$")
    stan: str = Field("123456", pattern=r"^\d{6}$")
    description: str | None = Field(
        None,
        max_length=MAX_DESCRIPTION_LENGTH,
        description="Describe the message in plain English and let an LLM build it. Overrides the other fields.",
    )
    provider: str | None = None
    model: str | None = None


class GenerateResponse(BaseModel):
    message: str
    mti: str
    network: CardNetwork | None
    fields: list[FieldValue]
    source: str


class ConvertRequest(MessageRequest):
    target_version: ISO8583Version


class ConvertResponse(BaseModel):
    message: str
    mti: str
    dropped: dict[int, str]
    notes: list[str]
    lossless: bool


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str


def _parse(request: MessageRequest) -> ISO8583Message:
    return ISO8583Parser(version=request.version).parse(request.message.rstrip("\r\n"), network=request.network)


def _public_from_env() -> bool:
    return os.environ.get("ISO8583SIM_PUBLIC", "").strip().lower() in {"1", "true", "yes"}


def _llm(provider: str | None, model: str | None, public: bool) -> Any:
    """Get an LLM provider, or raise 503 when none is available."""
    from ..llm import LLMError, get_provider

    if public:
        # subhadipmitra@: Checked before looking for a provider, so a public server never
        # calls an LLM even if a key happens to be set in its environment.
        raise HTTPException(
            status_code=403,
            detail="LLM features are turned off on this public server. Run `iso8583sim web` locally to use them.",
        )

    try:
        return get_provider(provider, model=model) if model else get_provider(provider)
    except LLMError as e:
        # subhadipmitra@: A missing key or package is a server configuration problem, not a
        # bad request, so it is reported as 503 Service Unavailable.
        raise HTTPException(status_code=503, detail=str(e)) from None


def create_app(public: bool | None = None) -> FastAPI:
    """Create the REST API application.

    Args:
        public: Run as a public demo, with LLM features off and CORS open to any origin.
            Defaults to the ISO8583SIM_PUBLIC environment variable.
    """
    if public is None:
        public = _public_from_env()
    app = FastAPI(
        title="ISO8583 Simulator API",
        version=__version__,
        description=(
            "Parse, build, validate, explain, generate and convert ISO 8583 messages. "
            "Intended for testing: there is no authentication. Only use test card numbers."
        ),
    )
    if public:
        # subhadipmitra@: The API has no cookies or credentials, so allowing every origin only
        # lets browser apps call it the same way curl already can.
        app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

    @app.exception_handler(ISO8583Error)
    @app.exception_handler(ValueError)
    async def _bad_input(_: Request, exc: Exception) -> JSONResponse:
        # subhadipmitra@: Parse, build and conversion errors come from the message itself, so
        # they are client errors (422) with the library's explanation, not 500s.
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    # subhadipmitra@: The endpoints are async so they run on the event loop. FastAPI runs plain
    # def endpoints in a thread pool, and Pyodide (Cloudflare Python Workers, where the public
    # demo runs) has no threads. Parsing and building take microseconds, so they don't block
    # anything. Only the LLM calls, which wait on the network, are sent to a thread.
    @app.get("/health", response_model=HealthResponse, tags=["Meta"])
    async def health() -> dict[str, Any]:
        """Liveness check."""
        return {"status": "ok", "version": __version__}

    @app.post("/parse", response_model=ParseResponse, tags=["Messages"])
    async def parse(request: MessageRequest) -> dict[str, Any]:
        """Parse a raw message into its MTI, bitmap and named fields."""
        parsed = _parse(request)
        result: dict[str, Any] = {
            "mti": parsed.mti,
            "version": parsed.version,
            "network": parsed.network,
            "bitmap": parsed.bitmap,
            "fields": field_entries(parsed),
        }
        if 55 in parsed.fields:
            result["emv"] = decode_emv_tags(parsed.fields[55])
        return result

    @app.post("/build", response_model=BuildResponse, tags=["Messages"])
    async def build(request: BuildRequest) -> dict[str, Any]:
        """Build a raw message from an MTI and field values."""
        message = ISO8583Message(
            mti=request.mti, fields=dict(request.fields), version=request.version, network=request.network
        )
        raw = ISO8583Builder(version=request.version).build(message)
        return {"message": raw, "length": len(raw)}

    @app.post("/validate", response_model=ValidateResponse, tags=["Messages"])
    async def validate(request: ValidateRequest) -> dict[str, Any]:
        """Validate a message, optionally against other networks' rules too.

        A message that fails to parse is reported as invalid (200), not as an error.
        """
        try:
            parsed = _parse(request)
        except ISO8583Error as e:
            return {"valid": False, "errors": [f"Parse error: {e}"]}
        validator = ISO8583Validator()
        errors = validator.validate_message(parsed)
        result: dict[str, Any] = {"valid": not errors, "errors": errors}
        if request.against is not None:
            checks = validator.validate_for_networks(parsed, request.against or None)
            result["networks"] = {net: {"passed": not errs, "errors": errs} for net, errs in checks.items()}
        return result

    @app.post("/explain", response_model=ExplainResponse, tags=["Messages"])
    async def explain(request: ExplainRequest) -> dict[str, Any]:
        """Explain a message in plain English, with rules (default) or an LLM."""
        parsed = _parse(request)
        if not request.llm:
            return {
                "summary": describe_message(parsed)["summary"],
                "source": "rules",
                "mti": parsed.mti,
                "fields": field_entries(parsed),
            }

        from ..llm import LLMError, MessageExplainer

        llm = _llm(request.provider, request.model, public)
        try:
            summary = await run_in_threadpool(MessageExplainer(provider=llm).explain, parsed)
        except LLMError as e:
            raise HTTPException(status_code=502, detail=str(e)) from None
        return {
            "summary": summary,
            "source": f"llm:{llm.name.lower()}/{llm.model}",
            "mti": parsed.mti,
            "fields": field_entries(parsed),
        }

    @app.post("/generate", response_model=GenerateResponse, tags=["Messages"])
    async def generate(request: GenerateRequest) -> dict[str, Any]:
        """Generate a valid test message from options, or from a description with an LLM."""
        if request.description:
            from ..llm import LLMError, MessageGenerator

            llm = _llm(request.provider, request.model, public)
            try:
                message = await run_in_threadpool(MessageGenerator(provider=llm).generate, request.description)
            except LLMError as e:
                # subhadipmitra@: The upstream model failed or produced an invalid message,
                # which is a bad gateway from the client's point of view.
                raise HTTPException(status_code=502, detail=str(e)) from None
            source = f"llm:{llm.name.lower()}/{llm.model}"
        else:
            message = sample_message(
                request.message_type,
                request.network,
                request.pan,
                request.amount_minor_units,
                request.currency,
                request.stan,
            )
            source = "template"

        raw = ISO8583Builder().build(message)
        return {
            "message": raw,
            "mti": message.mti,
            "network": message.network,
            "fields": field_entries(message),
            "source": source,
        }

    @app.post("/convert", response_model=ConvertResponse, tags=["Messages"])
    async def convert(request: ConvertRequest) -> dict[str, Any]:
        """Convert a message to another ISO 8583 version, listing dropped fields and notes."""
        parsed = _parse(request)
        result = convert_message(parsed, request.target_version)
        # subhadipmitra@: Same rule as the CLI and MCP server. A network guessed from the PAN
        # is not enforced on the output.
        if request.network is None:
            result.message.network = None
        raw = ISO8583Builder(version=request.target_version).build(result.message)
        return {
            "message": raw,
            "mti": result.message.mti,
            "dropped": result.dropped,
            "notes": result.notes,
            "lossless": result.lossless,
        }

    return app


app = create_app()
