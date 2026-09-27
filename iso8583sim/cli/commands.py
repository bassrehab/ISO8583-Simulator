import code
import readline
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from .. import __version__
from ..core.builder import ISO8583Builder
from ..core.describe import describe_message
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

    def interact(self, banner: str | None = None, exitmsg: str | None = None) -> None:
        """Start the interactive shell"""
        if banner is None:
            banner = self._get_default_banner()

        try:
            super().interact(banner, exitmsg)
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
    console.print(f"[cyan]ISO8583 Simulator[/] [green]v{__version__}[/]")


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
    against: str | None = typer.Option(
        None, "--against", "-a", help="Check against other networks: comma separated names, or 'all'"
    ),
):
    """Validate an ISO 8583 message"""
    try:
        # Parse message first
        iso_version = ISO8583Version(version)
        parser = ISO8583Parser(version=iso_version)
        card_network = CardNetwork(network.upper()) if network else None
        parsed = parser.parse(message, network=card_network)
        validator = ISO8583Validator()

        if against:
            targets = (
                list(CardNetwork)
                if against.strip().lower() == "all"
                else [CardNetwork(name.strip().upper()) for name in against.split(",") if name.strip()]
            )
            results = validator.validate_for_networks(parsed, targets)
        else:
            errors = validator.validate_message(parsed)
    except Exception as e:
        console.print(f"[red]Error validating message: {escape(str(e))}")
        raise typer.Exit(1) from None

    # subhadipmitra@: Report and exit outside the try block. typer.Exit is an Exception
    # subclass, so raising it inside the try would be caught and misreported as an error.
    if against:
        table = Table(title="Network Compliance")
        table.add_column("Network", style="cyan")
        table.add_column("Result")
        table.add_column("Issues")
        for net, net_errors in results.items():
            status = "[green]PASS[/]" if not net_errors else "[red]FAIL[/]"
            table.add_row(net.value, status, escape("; ".join(net_errors)) or "-")
        console.print(table)
        if any(results.values()):
            raise typer.Exit(1)
        return

    console.print(formatter.format_validation_results(errors))
    if errors:
        raise typer.Exit(1)


@app.command("convert")
def convert_message_version(
    message: str = typer.Argument(..., help="ISO 8583 message to convert"),
    source: str = typer.Option("1987", "--from", "-f", help="Version of the input message (1987, 1993, 2003)"),
    target: str = typer.Option(..., "--to", "-t", help="Version to convert to (1987, 1993, 2003)"),
    network: str | None = typer.Option(None, "--network", "-n", help="Card network (VISA, MASTERCARD, AMEX, etc.)"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file for the converted message"),
):
    """Convert a message to another ISO 8583 version"""
    from ..core.convert import convert_message

    try:
        parsed = ISO8583Parser(version=ISO8583Version(source)).parse(
            message, network=CardNetwork(network.upper()) if network else None
        )
        target_version = ISO8583Version(target)
        result = convert_message(parsed, target_version)
        # subhadipmitra@: The parser guesses a network from the PAN when none is given. Only
        # enforce network rules on the output if the user asked for a network, so that
        # converting never rejects a message the input version accepted.
        if not network:
            result.message.network = None
        raw = ISO8583Builder(version=target_version).build(result.message)
    except Exception as e:
        console.print(f"[red]Error converting message: {escape(str(e))}")
        raise typer.Exit(1) from None

    console.print(
        Panel(raw, title=f"Converted {parsed.mti} ({source}) to {result.message.mti} ({target})", border_style="cyan")
    )
    for note in result.notes:
        console.print(f"[yellow]Note:[/] {escape(note)}")
    # subhadipmitra@: Dropped fields are warnings, not errors. The converted message is still
    # valid, but the user needs to know it is missing data they may have to regenerate.
    for number, reason in sorted(result.dropped.items()):
        console.print(f"[red]Dropped field {number}:[/] {escape(reason)}")

    if output:
        output.write_text(raw)
        console.print(f"\n[green]Message saved to {output}")


@app.command("explain")
def explain_message(
    message: str = typer.Argument(..., help="ISO 8583 message to explain"),
    version: str = typer.Option("1987", "--version", "-v", help="ISO 8583 version (1987, 1993, 2003)"),
    network: str | None = typer.Option(None, "--network", "-n", help="Card network (VISA, MASTERCARD, AMEX, etc.)"),
    provider: str | None = typer.Option(
        None, "--provider", "-p", help="LLM provider (anthropic, openai, google, ollama). Auto-detected if omitted"
    ),
    model: str | None = typer.Option(None, "--model", "-m", help="Model name for the provider"),
    verbose: bool = typer.Option(False, "--verbose", help="Ask the LLM for more technical detail"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Rule-based summary that needs no LLM or API key"),
):
    """Explain an ISO 8583 message in plain English"""
    # subhadipmitra@: Parse here, not inside MessageExplainer, so --version and --network are
    # honoured. The explainer's own parser always assumes 1987 with network auto-detection.
    try:
        parser = ISO8583Parser(version=ISO8583Version(version))
        card_network = CardNetwork(network.upper()) if network else None
        parsed = parser.parse(message, network=card_network)
    except Exception as e:
        console.print(f"[red]Error parsing message: {str(e)}")
        raise typer.Exit(1) from None

    # subhadipmitra@: --no-llm uses the same rule-based summary as the MCP server's
    # explain_message tool, so the command stays useful offline and without an API key.
    if no_llm:
        description = describe_message(parsed)
        console.print(Panel(description["summary"], title=f"Message {parsed.mti}", border_style="cyan"))
        console.print(formatter.format_field_table(parsed.fields))
        return

    # subhadipmitra@: Import the LLM module lazily so commands that don't use an LLM
    # start fast and never touch provider SDKs.
    from ..llm import LLMError, MessageExplainer, get_provider

    try:
        # subhadipmitra@: Only pass model when given. Otherwise each provider keeps its own
        # default model, and get_provider(None) auto-detects the first configured provider.
        llm = get_provider(provider, model=model) if model else get_provider(provider)
        with console.status(f"Asking {llm.name} ({llm.model})..."):
            explanation = MessageExplainer(provider=llm).explain(parsed, verbose=verbose)
    except LLMError as e:
        # subhadipmitra@: Provider errors (no key, package missing, API failure) already carry
        # an actionable message, so show it as is and point to the offline option. escape()
        # keeps install hints like iso8583sim[google] from being read as Rich markup.
        console.print(f"[red]{escape(str(e))}")
        console.print("\n[yellow]Tip:[/] use --no-llm for a rule-based explanation that needs no API key.")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error explaining message: {str(e)}")
        raise typer.Exit(1) from None

    console.print(Panel(explanation, title=f"Message {parsed.mti} ({llm.name})", border_style="cyan"))


@app.command("generate")
def generate_message(
    type: str | None = typer.Option(None, "--type", "-t", help="Message type (auth, financial, reversal)"),
    pan: str = typer.Option("4111111111111111", "--pan", "-p", help="Primary Account Number"),
    amount: str = typer.Option("000000001000", "--amount", "-a", help="Transaction amount"),
    currency: str = typer.Option("840", "--currency", "-c", help="Currency code (ISO 4217)"),
    network: str | None = typer.Option(None, "--network", "-n", help="Card network (VISA, MASTERCARD, AMEX, etc.)"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file for generated message"),
    llm: str | None = typer.Option(
        None, "--llm", "-l", help='Describe the message in plain English, e.g. "$50 Mastercard refund at ACME"'
    ),
    provider: str | None = typer.Option(
        None, "--provider", help="LLM provider for --llm (anthropic, openai, google, ollama)"
    ),
    model: str | None = typer.Option(None, "--model", help="Model name for --llm"),
):
    """Generate a sample ISO 8583 message from a template or, with --llm, from a description"""
    # subhadipmitra@: --type became optional so that --llm can be used on its own. One of
    # the two is still required, which is checked here rather than by Typer.
    if llm:
        _generate_with_llm(llm, provider, model, output)
        return
    if not type:
        console.print("[red]Give a message type with --type, or describe the message with --llm")
        raise typer.Exit(1)

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


@app.command("mcp")
def mcp_server():
    """Run the MCP server over stdio for AI assistants (Claude, Cursor, etc.)"""
    # subhadipmitra@: The MCP SDK is an optional extra, so import it only when this command
    # runs. Without the extra, the user gets an install hint instead of a traceback.
    try:
        from ..mcp import main as run_mcp
    except ImportError:
        # subhadipmitra@: \\[ escapes the bracket so Rich doesn't swallow [mcp] as markup.
        console.print("[red]The MCP server needs the mcp extra: pip install 'iso8583sim\\[mcp]'")
        raise typer.Exit(1) from None
    run_mcp()


def _generate_with_llm(description: str, provider: str | None, model: str | None, output: Path | None) -> None:
    """Generate a message from a natural language description using an LLM"""
    from ..llm import LLMError, MessageGenerator, get_provider

    try:
        llm = get_provider(provider, model=model) if model else get_provider(provider)
        with console.status(f"Asking {llm.name} ({llm.model})..."):
            # subhadipmitra@: generate() validates the LLM output and retries common fixes,
            # so anything that reaches the builder is already a valid message.
            message = MessageGenerator(provider=llm).generate(description)
        result = ISO8583Builder().build(message)
    except LLMError as e:
        console.print(f"[red]{escape(str(e))}")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error generating message: {str(e)}")
        raise typer.Exit(1) from None

    console.print(Panel(result, title=f"Generated Message {message.mti} ({llm.name})", border_style="cyan"))
    console.print(formatter.format_field_table(message.fields))

    if output:
        output.write_text(result)
        console.print(f"\n[green]Message saved to {output}")


@app.command("web")
def web_server(
    host: str = typer.Option("127.0.0.1", "--host", help="Address to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    reload: bool = typer.Option(False, "--reload", help="Restart on code changes (development)"),
):
    """Run the REST API server (interactive docs at /docs)"""
    # subhadipmitra@: FastAPI and uvicorn are in the optional web extra, so import them only
    # when this command runs and give an install hint if they're missing.
    try:
        import uvicorn

        import iso8583sim.web.app  # noqa: F401
    except ImportError:
        console.print("[red]The REST API needs the web extra: pip install 'iso8583sim\\[web]'")
        raise typer.Exit(1) from None

    # subhadipmitra@: Default to localhost. The API has no authentication, so listening on
    # all interfaces should be a deliberate choice (--host 0.0.0.0).
    console.print(f"[cyan]Serving the ISO8583 Simulator API on http://{host}:{port} (docs at /docs)")
    uvicorn.run("iso8583sim.web.app:app", host=host, port=port, reload=reload)


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
