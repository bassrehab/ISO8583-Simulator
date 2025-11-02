# iso8583sim/cli/formatter.py
import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree


class CLIFormatter:
    def __init__(self):
        self.console = Console()

    def format_message(self, message: dict[str, Any]) -> Panel:
        """Format ISO message for display"""
        content = []
        content.append(f"[cyan]MTI:[/] {message.get('mti', 'N/A')}")
        content.append(f"[cyan]Version:[/] {message.get('version', 'N/A')}")

        fields = message.get("fields", {})
        if fields:
            content.append("\n[cyan]Fields:[/]")
            for field_num, value in sorted(fields.items()):
                content.append(f"  Field {field_num}: {value}")

        return Panel("\n".join(content), title="ISO 8583 Message", border_style="cyan")

    def format_validation_results(self, errors: list[str]) -> Panel:
        """Format validation results"""
        if not errors:
            return Panel("[green]✓ Message is valid[/]", title="Validation Results", border_style="green")

        content = ["[red]The following errors were found:[/]"]
        for error in errors:
            content.append(f"[red]✗[/] {error}")

        return Panel("\n".join(content), title="Validation Results", border_style="red")

    def format_field_table(self, fields: dict[int, str]) -> Table:
        """Create table of message fields"""
        table = Table(title="Message Fields")
        table.add_column("Field Number", style="cyan")
        table.add_column("Description", style="green")
        table.add_column("Value", style="yellow")
        table.add_column("Length", style="magenta")

        for field_num, value in sorted(fields.items()):
            table.add_row(str(field_num), self.get_field_description(field_num), value, str(len(value)))

        return table

    def format_tree_view(self, message: dict[str, Any]) -> Tree:
        """Create tree view of message structure"""
        tree = Tree("ISO 8583 Message")
        tree.add(f"MTI: {message.get('mti', 'N/A')}")
        tree.add(f"Version: {message.get('version', 'N/A')}")

        fields_branch = tree.add("Fields")
        for field_num, value in sorted(message.get("fields", {}).items()):
            fields_branch.add(f"Field {field_num}: {value}")

        return tree

    @staticmethod
    def get_field_description(field_num: int) -> str:
        """Get description for field number"""
        # This could be expanded with a complete field description mapping
        descriptions = {
            0: "Message Type Indicator",
            2: "Primary Account Number",
            3: "Processing Code",
            4: "Amount, Transaction",
            11: "Systems Trace Audit Number",
            12: "Time, Local Transaction",
            13: "Date, Local Transaction",
            37: "Retrieval Reference Number",
            39: "Response Code",
            41: "Card Acceptor Terminal ID",
            42: "Card Acceptor ID Code",
        }
        return descriptions.get(field_num, "Field Description Not Available")

    def print_success(self, message: str):
        """Print success message"""
        self.console.print(f"[green]✓[/] {message}")

    def print_error(self, message: str):
        """Print error message"""
        self.console.print(f"[red]✗[/] {message}")

    def print_warning(self, message: str):
        """Print warning message"""
        self.console.print(f"[yellow]![/] {message}")

    def print_info(self, message: str):
        """Print info message"""
        self.console.print(f"[blue]i[/] {message}")

    def format_json(self, data: dict[str, Any]) -> str:
        """Format data as colored JSON"""
        # Just return the formatted JSON string
        return json.dumps(data, indent=2)

    def print_json(self, data: dict[str, Any]):
        """Print data as syntax-highlighted JSON"""
        # Use Syntax for display but don't return it
        syntax = Syntax(json.dumps(data, indent=2), "json", theme="monokai", line_numbers=True)
        self.console.print(syntax)
