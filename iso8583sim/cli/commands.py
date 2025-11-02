import code
import readline
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel

from ..core.builder import ISO8583Builder
from ..core.parser import ISO8583Parser
from ..core.types import (
    CardNetwork,
    ISO8583Message,
    ISO8583Version,
)
from ..core.validator import ISO8583Validator
from .config import ConfigManager
from .formatter import CLIFormatter
from .utils import (
    create_template_message,
    format_amount,
    load_json_file,
    save_json_file,
    validate_pan,
)

# Initialize Typer app
app = typer.Typer(
    name="iso8583sim",
    help="ISO 8583 Message Simulator - Parse, Build, and Test ISO 8583 messages",
    add_completion=False,
)

# Initialize shared objects
console = Console()
formatter = CLIFormatter()
config_manager = ConfigManager()


class ISO8583Shell(code.InteractiveConsole):
    """Enhanced interactive shell for ISO8583 simulation"""

    def __init__(self, locals: dict[str, Any], history_file: Path):
        super().__init__(locals)
        self.history_file = history_file
        self.console = Console()
        self._setup_readline()

    def _setup_readline(self):
        """Setup readline with history and tab completion"""
        # Enable tab completion
        readline.parse_and_bind("tab: complete")

        # Load history if exists
        if self.history_file.exists():
            readline.read_history_file(str(self.history_file))

        # Set history length
        readline.set_history_length(1000)

    def interact(self, banner=None):
        """Start the interactive shell"""
        if banner is None:
            banner = self._get_default_banner()

        try:
            super().interact(banner)
        finally:
            # Save history on exit
            readline.write_history_file(str(self.history_file))

    def _get_default_banner(self) -> str:
        """Generate default banner with help text"""
        return """
[bold cyan]ISO 8583 Interactive Shell[/]
[green]Available objects:[/]
  - [yellow]parser[/]: ISO8583Parser instance
  - [yellow]builder[/]: ISO8583Builder instance
  - [yellow]validator[/]: ISO8583Validator instance
  - [yellow]formatter[/]: CLIFormatter instance

[green]Example usage:[/]
  >>> msg = parser.parse("0100...")
  >>> result = builder.build(msg)
  >>> errors = validator.validate_message(msg)
  >>> formatter.print_json(msg.fields)

[green]Special commands:[/]
  - [yellow]?obj[/]: Get help about an object
  - [yellow]dir(obj)[/]: List object attributes
  - [yellow]help(obj)[/]: Detailed help about an object

[cyan]Type 'exit()' or press Ctrl+D to exit[/]
"""

    def push(self, line: str) -> bool:
        """Process input line with error handling"""
        try:
            return super().push(line)
        except Exception as e:
            self.console.print(f"[red]Error:[/] {str(e)}")
            return False

    def raw_input(self, prompt=""):
        """Override raw_input to use rich formatting"""
        return super().raw_input(f"[cyan]{prompt}[/]")


@app.command()
def version():
    """Display version information"""
    console.print("[cyan]ISO8583 Simulator[/] [green]v0.1.0[/]")


@app.command("parse")
def parse_message(
    message: str = typer.Argument(..., help="ISO 8583 message string to parse"),
    version: str = typer.Option("1987", "--version", "-v", help="ISO 8583 version (1987, 1993, 2003)"),
    network: str | None = typer.Option(None, "--network", "-n", help="Card network (VISA, MASTERCARD, AMEX, etc.)"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file for parsed message (JSON format)"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json, tree)"),
):
    """Parse an ISO 8583 message and display its contents"""
    try:
        # Initialize parser
        iso_version = ISO8583Version(version)
        parser = ISO8583Parser(version=iso_version)

        # Parse message with optional network
        card_network = CardNetwork(network.upper()) if network else None
        parsed = parser.parse(message, network=card_network)

        # Format and display result based on format option
        if format == "table":
            table = formatter.format_field_table(parsed.fields)
            console.print(table)
        elif format == "json":
            formatter.print_json(parsed.fields)
        elif format == "tree":
            tree = formatter.format_tree_view(parsed.__dict__)
            console.print(tree)
        else:
            raise ValueError(f"Unknown format option: {format}")

        # Save to file if requested
        if output:
            result = {"mti": parsed.mti, "version": version, "network": network, "fields": parsed.fields}
            save_json_file(result, output)
            console.print(f"\n[green]Results saved to {output}")

    except Exception as e:
        console.print(f"[red]Error parsing message: {str(e)}")
        raise typer.Exit(1) from None


@app.command("build")
def build_message(
    mti: str = typer.Option(..., "--mti", "-m", help="Message Type Indicator"),
    fields_file: Path = typer.Option(..., "--fields", "-f", help="JSON file containing field values"),
    version: str = typer.Option("1987", "--version", "-v", help="ISO 8583 version (1987, 1993, 2003)"),
    network: str | None = typer.Option(None, "--network", "-n", help="Card network (VISA, MASTERCARD, AMEX, etc.)"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file for built message"),
):
    """Build an ISO 8583 message from field values"""
    try:
        # Load fields from JSON and convert string keys to integers
        fields_data = {int(k): v for k, v in load_json_file(fields_file).items()}

        # Initialize builder
        iso_version = ISO8583Version(version)
        builder = ISO8583Builder(version=iso_version)

        # Create message with optional network
        card_network = CardNetwork(network.upper()) if network else None
        message = ISO8583Message(mti=mti, fields=fields_data, version=iso_version, network=card_network)

        # Build message
        result = builder.build(message)

        # Display result
        panel = Panel(result, title="Built ISO 8583 Message", border_style="cyan")
        console.print(panel)

        # Save to file if requested
        if output:
            output.write_text(result)
            console.print(f"\n[green]Message saved to {output}")

    except Exception as e:
        console.print(f"[red]Error building message: {str(e)}")
        raise typer.Exit(1) from None


@app.command("validate")
def validate_message(
    message: str = typer.Argument(..., help="ISO 8583 message to validate"),
    version: str = typer.Option("1987", "--version", "-v", help="ISO 8583 version (1987, 1993, 2003)"),
    network: str | None = typer.Option(None, "--network", "-n", help="Card network (VISA, MASTERCARD, AMEX, etc.)"),
):
    """Validate an ISO 8583 message"""
    try:
        # Parse message first
        iso_version = ISO8583Version(version)
        parser = ISO8583Parser(version=iso_version)
        card_network = CardNetwork(network.upper()) if network else None
        parsed = parser.parse(message, network=card_network)

        # Validate
        validator = ISO8583Validator()
        errors = validator.validate_message(parsed)

        # Display results
        panel = formatter.format_validation_results(errors)
        console.print(panel)

        if errors:
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error validating message: {str(e)}")
        raise typer.Exit(1) from None


@app.command("generate")
def generate_message(
    type: str = typer.Option(..., "--type", "-t", help="Message type (auth, financial, reversal)"),
    pan: str = typer.Option("4111111111111111", "--pan", "-p", help="Primary Account Number"),
    amount: str = typer.Option("000000001000", "--amount", "-a", help="Transaction amount"),
    currency: str = typer.Option("840", "--currency", "-c", help="Currency code (ISO 4217)"),
    network: str | None = typer.Option(None, "--network", "-n", help="Card network (VISA, MASTERCARD, AMEX, etc.)"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file for generated message"),
):
    """Generate a sample ISO 8583 message"""
    try:
        # Create message template
        message = create_template_message(get_mti_for_type(type), pan=validate_pan(pan), amount=format_amount(amount))

        # Add network if specified
        if network:
            message["network"] = CardNetwork(network.upper())

        # Add currency
        message["fields"][49] = currency

        # Build message
        builder = ISO8583Builder()
        iso_message = ISO8583Message(**message)
        result = builder.build(iso_message)

        # Display result
        panel = Panel(result, title=f"Generated {type.title()} Message", border_style="cyan")
        console.print(panel)

        # Save to file if requested
        if output:
            output.write_text(result)
            console.print(f"\n[green]Message saved to {output}")

    except Exception as e:
        console.print(f"[red]Error generating message: {str(e)}")
        raise typer.Exit(1) from None


@app.command("shell")
def interactive_shell():
    """Start an interactive ISO 8583 shell"""
    try:
        # Create instances of core components
        parser = ISO8583Parser()
        builder = ISO8583Builder()
        validator = ISO8583Validator()

        # Get history file from config
        config = config_manager.get_config()
        history_file = Path(config.history_file).expanduser()

        # Create shell with local objects
        locals_dict = {
            "parser": parser,
            "builder": builder,
            "validator": validator,
            "formatter": formatter,
            "ISO8583Message": ISO8583Message,
            "ISO8583Version": ISO8583Version,
            "CardNetwork": CardNetwork,
        }

        # Create and start shell
        shell = ISO8583Shell(locals_dict, history_file)
        shell.interact()

    except Exception as e:
        console.print(f"[red]Error starting interactive shell: {str(e)}")
        raise typer.Exit(1) from None


def get_mti_for_type(type: str) -> str:
    """Get MTI for message type"""
    mti_map = {"auth": "0100", "financial": "0200", "reversal": "0400", "network": "0800"}

    if type not in mti_map:
        raise ValueError(f"Invalid message type. Choose from: {', '.join(mti_map.keys())}")

    return mti_map[type]


def main():
    """Entry point for the CLI"""
    app()


if __name__ == "__main__":
    main()
