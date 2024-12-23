import typer
import json
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from rich.panel import Panel
from rich.syntax import Syntax

from ..core.types import ISO8583Message, ISO8583Version
from ..core.parser import ISO8583Parser
from ..core.builder import ISO8583Builder
from ..core.validator import ISO8583Validator

app = typer.Typer(
    name="iso8583sim",
    help="ISO 8583 Message Simulator - Parse, Build, and Test ISO 8583 messages",
    add_completion=False
)

console = Console()


@app.command("parse")
def parse_message(
        message: str = typer.Argument(..., help="ISO 8583 message string to parse"),
        version: str = typer.Option(
            "1987",
            "--version",
            "-v",
            help="ISO 8583 version (1987, 1993, 2003)"
        ),
        output: Optional[Path] = typer.Option(
            None,
            "--output",
            "-o",
            help="Output file for parsed message (JSON format)"
        )
):
    """Parse an ISO 8583 message and display its contents"""
    try:
        # Initialize parser
        iso_version = ISO8583Version(version)
        parser = ISO8583Parser(version=iso_version)

        # Parse message
        parsed = parser.parse(message)

        # Display results in a table
        table = Table(title="Parsed ISO 8583 Message")
        table.add_column("Field", style="cyan")
        table.add_column("Description", style="green")
        table.add_column("Value", style="yellow")

        # Add MTI
        table.add_row("MTI", "Message Type Indicator", parsed.mti)

        # Add other fields
        for field_num, value in sorted(parsed.fields.items()):
            if field_num != 0:  # Skip MTI as it's already shown
                description = ISO8583_FIELDS[field_num].description
                table.add_row(f"Field {field_num}", description, value)

        console.print(table)

        # Save to file if requested
        if output:
            result = {
                "mti": parsed.mti,
                "version": version,
                "fields": parsed.fields
            }
            output.write_text(json.dumps(result, indent=2))
            console.print(f"\n[green]Results saved to {output}")

    except Exception as e:
        console.print(f"[red]Error parsing message: {str(e)}")
        raise typer.Exit(1)


@app.command("build")
def build_message(
        mti: str = typer.Option(..., "--mti", "-m", help="Message Type Indicator"),
        fields_file: Path = typer.Option(
            ...,
            "--fields",
            "-f",
            help="JSON file containing field values"
        ),
        version: str = typer.Option(
            "1987",
            "--version",
            "-v",
            help="ISO 8583 version (1987, 1993, 2003)"
        ),
        output: Optional[Path] = typer.Option(
            None,
            "--output",
            "-o",
            help="Output file for built message"
        )
):
    """Build an ISO 8583 message from field values"""
    try:
        # Load fields from JSON
        fields_data = json.loads(fields_file.read_text())

        # Initialize builder
        iso_version = ISO8583Version(version)
        builder = ISO8583Builder(version=iso_version)

        # Create and build message
        message = builder.create_message(mti, fields_data)
        result = builder.build(message)

        # Display result
        console.print("\n[bold cyan]Built ISO 8583 Message:[/]")
        console.print(Panel(result, title="Message"))

        # Save to file if requested
        if output:
            output.write_text(result)
            console.print(f"\n[green]Message saved to {output}")

    except Exception as e:
        console.print(f"[red]Error building message: {str(e)}")
        raise typer.Exit(1)


@app.command("validate")
def validate_message(
        message: str = typer.Argument(..., help="ISO 8583 message to validate"),
        version: str = typer.Option(
            "1987",
            "--version",
            "-v",
            help="ISO 8583 version (1987, 1993, 2003)"
        )
):
    """Validate an ISO 8583 message"""
    try:
        # Parse message first
        iso_version = ISO8583Version(version)
        parser = ISO8583Parser(version=iso_version)
        parsed = parser.parse(message)

        # Validate
        validator = ISO8583Validator()
        errors = validator.validate_message(parsed)

        if errors:
            console.print("\n[red]Message Validation Failed:[/]")
            for error in errors:
                console.print(f"❌ {error}")
        else:
            console.print("\n[green]Message Validation Successful ✓[/]")

    except Exception as e:
        console.print(f"[red]Error validating message: {str(e)}")
        raise typer.Exit(1)


@app.command("generate")
def generate_message(
        type: str = typer.Option(
            ...,
            "--type",
            "-t",
            help="Message type (auth, financial, reversal)"
        ),
        pan: str = typer.Option(
            "4111111111111111",
            "--pan",
            "-p",
            help="Primary Account Number"
        ),
        amount: str = typer.Option(
            "000000001000",
            "--amount",
            "-a",
            help="Transaction amount"
        ),
        currency: str = typer.Option(
            "840",
            "--currency",
            "-c",
            help="Currency code (ISO 4217)"
        ),
):
    """Generate a sample ISO 8583 message"""
    try:
        # Determine MTI based on type
        mti_map = {
            "auth": "0100",
            "financial": "0200",
            "reversal": "0400"
        }

        if type not in mti_map:
            raise ValueError(f"Invalid message type. Choose from: {', '.join(mti_map.keys())}")

        mti = mti_map[type]

        # Create common fields
        fields = {
            2: pan,  # PAN
            3: "000000",  # Processing code
            4: amount,  # Amount
            49: currency,  # Currency code
            11: str(datetime.now().strftime("%H%M%S")),  # STAN
            12: datetime.now().strftime("%H%M%S"),  # Time
            13: datetime.now().strftime("%m%d"),  # Date
            41: "TEST1234",  # Terminal ID
            42: "MERCHANT123456789"  # Merchant ID
        }

        # Build message
        builder = ISO8583Builder()
        message = builder.create_message(mti, fields)
        result = builder.build(message)

        # Display result
        console.print("\n[bold cyan]Generated ISO 8583 Message:[/]")
        console.print(Panel(result, title=f"{type.title()} Message"))

    except Exception as e:
        console.print(f"[red]Error generating message: {str(e)}")
        raise typer.Exit(1)


@app.command("shell")
def interactive_shell():
    """Start an interactive ISO 8583 shell"""
    import code
    import readline
    import rlcompleter

    # Create instances of core components
    parser = ISO8583Parser()
    builder = ISO8583Builder()
    validator = ISO8583Validator()

    # Create banner
    banner = """
    ISO 8583 Interactive Shell
    -------------------------
    Available objects:
    - parser: ISO8583Parser instance
    - builder: ISO8583Builder instance
    - validator: ISO8583Validator instance

    Example:
    >>> msg = parser.parse("0100...")
    >>> result = builder.build(msg)
    >>> errors = validator.validate_message(msg)
    """

    # Start interactive shell
    code.InteractiveConsole(locals=locals()).interact(banner=banner)


if __name__ == "__main__":
    app()
