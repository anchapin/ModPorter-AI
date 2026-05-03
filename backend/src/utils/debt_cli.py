"""
CLI tool for technical debt tracking.

Usage:
  python -m debt_cli scan                # Scan current directory
  python -m debt_cli scan --path /path   # Scan specific directory
  python -m debt_cli report              # Generate markdown report
  python -m debt_cli critical            # Show critical items only
  python -m debt_cli issue 687           # Show items for issue #687
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click
import structlog

from .debt_tracker import DebtTracker

logger = structlog.get_logger()


@click.group()
def cli():
    """Technical Debt Tracking Tool."""
    pass


@cli.command()
@click.option(
    "--path",
    default=".",
    help="Root path to scan for debt markers.",
    type=click.Path(exists=True),
)
@click.option(
    "--pattern",
    default="**/*.py",
    help="File glob pattern to scan.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON.",
)
def scan(path: str, pattern: str, output_json: bool):
    """Scan directory for technical debt markers."""
    tracker = DebtTracker(path)

    click.echo(f"Scanning {path} for debt markers...", err=True)
    items = tracker.scan_directory(pattern=pattern)

    if output_json:
        output = [item.to_dict() for item in items]
        click.echo(json.dumps(output, indent=2, default=str))
    else:
        if not items:
            click.echo("No technical debt markers found.")
            return

        click.echo(f"\nFound {len(items)} technical debt items:\n")

        for item in sorted(items, key=lambda x: (x.severity.value, x.file_path)):
            severity_color = {
                "critical": "red",
                "high": "yellow",
                "medium": "cyan",
                "low": "white",
            }.get(item.severity.value, "white")

            click.echo(
                click.style(
                    f"[{item.severity.value.upper()}]",
                    fg=severity_color,
                    bold=True,
                ),
                nl=False,
            )
            click.echo(f" {item}")


@cli.command()
@click.option(
    "--path",
    default=".",
    help="Root path to scan.",
    type=click.Path(exists=True),
)
@click.option(
    "--output",
    default=None,
    help="Output file path for markdown report.",
)
def report(path: str, output: Optional[str]):
    """Generate markdown report of technical debt."""
    tracker = DebtTracker(path)

    click.echo("Scanning and generating report...", err=True)
    tracker.scan_directory()

    if output is None:
        output = Path(path) / "TECHNICAL_DEBT_REPORT.md"

    markdown = tracker.export_markdown(str(output))

    if output:
        click.echo(f"Report written to {output}", err=True)
    else:
        click.echo(markdown)


@cli.command()
@click.option(
    "--path",
    default=".",
    help="Root path to scan.",
    type=click.Path(exists=True),
)
def critical(path: str):
    """Show all critical severity technical debt items."""
    tracker = DebtTracker(path)

    click.echo("Scanning for critical debt items...", err=True)
    tracker.scan_directory()

    critical_items = tracker.get_critical_items()

    if not critical_items:
        click.echo("No critical technical debt items found.")
        return

    click.echo(f"\nFound {len(critical_items)} critical items:\n")

    for item in sorted(critical_items, key=lambda x: x.file_path):
        click.echo(click.style(f"[CRITICAL]", fg="red", bold=True) + f" {item}")
        click.echo(f"Context:\n{item.context}\n")


@cli.command()
@click.argument("issue_number", type=int)
@click.option(
    "--path",
    default=".",
    help="Root path to scan.",
    type=click.Path(exists=True),
)
def issue(issue_number: int, path: str):
    """Show technical debt items for a specific GitHub issue."""
    tracker = DebtTracker(path)

    click.echo(f"Scanning for issue #{issue_number}...", err=True)
    tracker.scan_directory()

    items = tracker.filter_by_issue(issue_number)

    if not items:
        click.echo(f"No technical debt items found for issue #{issue_number}")
        return

    click.echo(f"\nFound {len(items)} items for issue #{issue_number}:\n")

    for item in sorted(items, key=lambda x: (x.file_path, x.line_number)):
        click.echo(f"[{item.severity.value.upper()}] {item.description}")
        click.echo(f"  Location: {item.file_path}:{item.line_number}")
        click.echo(f"  Category: {item.category.value}")
        click.echo(f"  GitHub: {item.github_issue_link()}\n")


@cli.command()
@click.option(
    "--path",
    default=".",
    help="Root path to scan.",
    type=click.Path(exists=True),
)
def summary(path: str):
    """Show summary of technical debt."""
    tracker = DebtTracker(path)

    click.echo("Scanning and summarizing...", err=True)
    tracker.scan_directory()

    summary_data = tracker.get_summary()

    click.echo("\n" + "=" * 50)
    click.echo("TECHNICAL DEBT SUMMARY")
    click.echo("=" * 50 + "\n")

    click.echo(f"Total Items: {summary_data['total']}\n")

    if summary_data["by_severity"]:
        click.echo("By Severity:")
        for severity in ["critical", "high", "medium", "low"]:
            count = summary_data["by_severity"].get(severity, 0)
            if count > 0:
                click.echo(f"  {severity.capitalize():12} {count:3}")
        click.echo()

    if summary_data["by_category"]:
        click.echo("By Category:")
        for category, count in sorted(summary_data["by_category"].items(), key=lambda x: -x[1]):
            click.echo(f"  {category.replace('_', ' ').title():20} {count:3}")
        click.echo()

    if summary_data["by_issue"]:
        click.echo(f"Top Issues ({min(5, len(summary_data['by_issue']))} shown):")
        for issue, data in sorted(
            summary_data["by_issue"].items(),
            key=lambda x: -x[1]["count"],
        )[:5]:
            click.echo(f"  {issue:6} {data['count']:3} items")


if __name__ == "__main__":
    cli()
