# REST API

iso8583sim includes a REST API built with FastAPI, for tools and services that aren't written in Python.

!!! warning "For test environments"
    The API has no authentication. It listens on `127.0.0.1` by default. Don't expose it on a public network.

## Running

```bash
pip install iso8583sim[web]
iso8583sim web
```

The server starts on `http://127.0.0.1:8000`. Options: `--host`, `--port` and `--reload` (restart on code changes).

You can also run it with uvicorn directly:

```bash
uvicorn iso8583sim.web.app:app --port 8000
```

Interactive API docs are served at [`/docs`](http://127.0.0.1:8000/docs) and the OpenAPI schema at [`/openapi.json`](http://127.0.0.1:8000/openapi.json).

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness check, returns the package version |
| POST | `/parse` | Parse a raw message into its MTI, bitmap and named fields (EMV decoded when present) |
| POST | `/build` | Build a raw message from an MTI and field values |
| POST | `/validate` | Validate a message, and optionally check it against other networks' rules |
| POST | `/explain` | Plain English summary, rule-based by default or from an LLM with `"llm": true` |
| POST | `/generate` | Generate a valid test message from options, or from a description with an LLM |
| POST | `/convert` | Convert a message to another ISO 8583 version |

Common request fields:

- `message`: raw message string (MTI, hex bitmap, field data)
- `version`: `"1987"` (default), `"1993"` or `"2003"`
- `network`: `VISA`, `MASTERCARD`, `AMEX`, `DISCOVER`, `JCB` or `UNIONPAY`. Detected from the PAN when omitted.

## Examples

Generate a test message and explain it:

```bash
curl -s -X POST localhost:8000/generate \
  -H 'content-type: application/json' \
  -d '{"network": "MASTERCARD", "amount_minor_units": 2500}'
```

```json
{
  "message": "0100722405800...",
  "mti": "0100",
  "network": "MASTERCARD",
  "fields": [{"number": 2, "name": "Primary Account Number (PAN)", "value": "5555555555554444"}, "..."],
  "source": "template"
}
```

```bash
curl -s -X POST localhost:8000/explain \
  -H 'content-type: application/json' \
  -d '{"message": "0100722405800..."}'
```

```json
{
  "summary": "MTI 0100: authorization request from acquirer. Card network: MASTERCARD. Card: 555555******4444. Transaction type: Purchase. Amount: 25.00 USD. ...",
  "source": "rules",
  "mti": "0100",
  "fields": ["..."]
}
```

Build a message. Field numbers are JSON object keys, so they are strings:

```bash
curl -s -X POST localhost:8000/build \
  -H 'content-type: application/json' \
  -d '{"mti": "0800", "fields": {"7": "1215143022", "11": "000001", "70": "301"}}'
```

Check a message against every network (an empty `against` list means all):

```bash
curl -s -X POST localhost:8000/validate \
  -H 'content-type: application/json' \
  -d '{"message": "0100...", "against": []}'
```

## Errors

| Status | When |
|--------|------|
| 422 | Invalid request, or a message that can't be parsed, built or converted. `detail` explains why. |
| 502 | The LLM failed or returned an unusable message (`/explain` and `/generate` with an LLM) |
| 503 | No LLM provider is configured on the server |

`/validate` is the exception: a message that fails to parse is returned as `{"valid": false, "errors": ["Parse error: ..."]}` with status 200.

## Docker

The repository includes a `Dockerfile` that runs the API with the security extra installed:

```bash
docker build -t iso8583sim .
docker run --rm -p 8000:8000 iso8583sim
```

Inside the container the server listens on all interfaces so the port mapping works. `-p 127.0.0.1:8000:8000` keeps it reachable from your machine only.

To use LLM features, pass the provider's API key:

```bash
docker run --rm -p 8000:8000 -e ANTHROPIC_API_KEY iso8583sim
```

The image installs the `anthropic` extra only. Build with `--build-arg EXTRAS=web,security,llm` for all providers.
