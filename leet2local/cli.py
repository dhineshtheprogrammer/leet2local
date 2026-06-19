from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Reconfigure stdout/stderr to UTF-8 on Windows so Unicode symbols render correctly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

app = typer.Typer(
    name="lc",
    help="[bold green]Leet2Local[/bold green] -- Solve LeetCode problems in your local IDE.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()


# ---------------------------------------------------------------------------
# lc login
# ---------------------------------------------------------------------------

@app.command()
def login(
    username: Optional[str] = typer.Option(
        None, "--username", "-u",
        help="LeetCode username or email. Omit to use the cookie-paste method instead.",
    ),
    password: Optional[str] = typer.Option(
        None, "--password", "-p",
        help="Password. If --username is given but --password is omitted, you will be prompted.",
        hide_input=True,
    ),
):
    """Log in to LeetCode.

    \b
    Two methods are supported:
      lc login                          # paste cookies from browser DevTools
      lc login -u you@email.com        # username + password (prompts for password)
      lc login -u you@email.com -p pw  # fully non-interactive
    """
    from .auth import run_login_flow
    run_login_flow(username=username, password=password)


# ---------------------------------------------------------------------------
# lc fetch
# ---------------------------------------------------------------------------

@app.command()
def fetch(
    number: int = typer.Argument(..., help="LeetCode problem number (e.g. 1, 42)"),
    lang: Optional[str] = typer.Option(
        None,
        "--lang",
        "-l",
        help="Language: python | javascript | cpp | java",
    ),
):
    """Fetch a LeetCode problem and create local files."""
    from .config import load_config
    from .fetcher import fetch_problem

    config = load_config()
    effective_lang = lang or config.settings.default_language

    valid_langs = {"python", "javascript", "cpp", "java"}
    if effective_lang not in valid_langs:
        console.print(f"[red]Unsupported language:[/red] {effective_lang!r}. Choose from: {', '.join(sorted(valid_langs))}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task(f"Fetching problem #{number}...", total=None)
        try:
            problem, dir_path = fetch_problem(number, effective_lang)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    tc_count = len(problem.sample_test_cases)
    console.print(
        Panel(
            f"[bold]{problem.frontend_id}. {problem.title}[/bold]  "
            f"[{'green' if problem.difficulty == 'Easy' else 'yellow' if problem.difficulty == 'Medium' else 'red'}]"
            f"{problem.difficulty}[/]\n\n"
            f"[dim]Created:[/dim] {dir_path}\n"
            f"[dim]Test cases:[/dim] {tc_count} sample case{'s' if tc_count != 1 else ''}",
            title="[green]✓ Fetched[/green]",
            border_style="green",
        )
    )


# ---------------------------------------------------------------------------
# lc run
# ---------------------------------------------------------------------------

@app.command()
def run(
    number: int = typer.Argument(..., help="LeetCode problem number"),
):
    """Run solution locally against sample test cases."""
    from .config import load_config
    from .runner import run_local

    config = load_config()

    if config.settings.run_mode == "remote":
        _run_remote_interpret(number)
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("Running tests...", total=None)
        try:
            results = run_local(number)
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    _render_test_results(results)


def _run_remote_interpret(number: int) -> None:
    console.print("[yellow]Remote run mode is not yet implemented. Falling back to local.[/yellow]")
    from .runner import run_local
    try:
        results = run_local(number)
        _render_test_results(results)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _render_test_results(results) -> None:
    table = Table(title="Test Results", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Status", width=8)
    table.add_column("Input")
    table.add_column("Expected")
    table.add_column("Got")

    all_pass = all(r.passed for r in results)
    for r in results:
        if r.passed:
            status = "[green]PASS[/green]"
            got_cell = f"[green]{r.got}[/green]"
            expected_cell = str(r.expected)
        elif r.error:
            status = "[red]ERROR[/red]"
            got_cell = f"[red]{r.error}[/red]"
            expected_cell = str(r.expected) if r.expected is not None else ""
        else:
            status = "[red]FAIL[/red]"
            got_cell = f"[red]{r.got}[/red]"
            expected_cell = str(r.expected)

        table.add_row(str(r.index), status, r.input_repr, expected_cell, got_cell)

    console.print(table)
    if all_pass:
        console.print(f"[bold green]✓ All {len(results)} test(s) passed[/bold green]")
    else:
        failed = sum(1 for r in results if not r.passed)
        console.print(f"[bold red]✗ {failed}/{len(results)} test(s) failed[/bold red]")


# ---------------------------------------------------------------------------
# lc submit
# ---------------------------------------------------------------------------

@app.command()
def submit(
    number: int = typer.Argument(..., help="LeetCode problem number"),
):
    """Submit solution to LeetCode and get full test results."""
    from .auth import AuthError
    from .submitter import submit_remote

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("Submitting to LeetCode...", total=None)
        try:
            result = submit_remote(number)
        except AuthError as e:
            console.print(f"[red]Auth error:[/red] {e}")
            raise typer.Exit(1)
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Submission error:[/red] {e}")
            raise typer.Exit(1)

    _render_submission_result(result)


def _render_submission_result(result) -> None:
    if result.status_display == "Timeout":
        console.print("[yellow]Submission timed out waiting for results.[/yellow]")
        return

    color = "green" if result.accepted else "red"
    title = f"[{color}]{result.status_display}[/{color}]"

    details: list[str] = []
    if result.accepted:
        if result.runtime:
            pct = f" (beats {result.runtime_percentile:.1f}%)" if result.runtime_percentile else ""
            details.append(f"Runtime: {result.runtime}{pct}")
        if result.memory:
            pct = f" (beats {result.memory_percentile:.1f}%)" if result.memory_percentile else ""
            details.append(f"Memory:  {result.memory}{pct}")
        if result.total_correct and result.total_testcases:
            details.append(f"Tests:   {result.total_correct}/{result.total_testcases}")
    else:
        if result.compile_error:
            details.append(f"Compile Error:\n{result.compile_error}")
        else:
            if result.last_testcase:
                details.append(f"Failed input: {result.last_testcase}")
            if result.expected_output:
                details.append(f"Expected: {result.expected_output}")
            if result.code_output:
                details.append(f"Got:      {result.code_output}")

    body = "\n".join(details) if details else ""
    console.print(Panel(body, title=title, border_style=color))


# ---------------------------------------------------------------------------
# lc config
# ---------------------------------------------------------------------------

config_app = typer.Typer(help="View or modify configuration.")
app.add_typer(config_app, name="config")


@config_app.callback(invoke_without_command=True)
def config_show(
    ctx: typer.Context,
    set_val: Optional[str] = typer.Option(
        None, "--set", help="Set a config value, e.g. settings.default_language=javascript"
    ),
    vscode_init: bool = typer.Option(False, "--vscode-init", help="Generate .vscode/tasks.json"),
):
    """Show current configuration."""
    if ctx.invoked_subcommand:
        return

    if set_val:
        if "=" not in set_val:
            console.print("[red]Error:[/red] Use format [bold]key=value[/bold], e.g. settings.default_language=javascript")
            raise typer.Exit(1)
        key, value = set_val.split("=", 1)
        from .config import set_config_value
        try:
            set_config_value(key.strip(), value.strip())
            console.print(f"[green]✓[/green] Set [bold]{key}[/bold] = {value}")
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        return

    if vscode_init:
        _generate_vscode_tasks()
        return

    from .config import load_config
    import tomllib, io
    import tomli_w

    cfg = load_config()
    raw = {
        "settings": cfg.settings.model_dump(),
        "api": cfg.api.model_dump(),
        "runtime": cfg.runtime.model_dump(),
        "display": cfg.display.model_dump(),
    }
    toml_str = tomli_w.dumps(raw)
    console.print(Panel(toml_str, title="Current Configuration", border_style="blue"))


def _generate_vscode_tasks() -> None:
    tasks = {
        "version": "2.0.0",
        "tasks": [
            {
                "label": "LC: Fetch Problem",
                "type": "shell",
                "command": "lc fetch ${input:problemNumber} --lang ${input:language}",
                "group": "build",
                "presentation": {"reveal": "always", "panel": "shared"},
                "problemMatcher": [],
            },
            {
                "label": "LC: Run Local",
                "type": "shell",
                "command": "lc run ${input:problemNumber}",
                "group": "test",
                "presentation": {"reveal": "always", "panel": "shared"},
                "problemMatcher": [],
            },
            {
                "label": "LC: Submit",
                "type": "shell",
                "command": "lc submit ${input:problemNumber}",
                "group": "test",
                "presentation": {"reveal": "always", "panel": "shared"},
                "problemMatcher": [],
            },
        ],
        "inputs": [
            {
                "id": "problemNumber",
                "type": "promptString",
                "description": "LeetCode problem number",
            },
            {
                "id": "language",
                "type": "pickString",
                "description": "Language",
                "options": ["python", "javascript", "cpp", "java"],
                "default": "python",
            },
        ],
    }

    vscode_dir = Path(".vscode")
    vscode_dir.mkdir(exist_ok=True)
    tasks_path = vscode_dir / "tasks.json"
    tasks_path.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    console.print(f"[green]✓[/green] Generated [bold]{tasks_path}[/bold]")
    console.print(
        "[dim]Bind shortcuts in keybindings.json:[/dim]\n"
        "  Ctrl+Shift+R → LC: Run Local\n"
        "  Ctrl+Shift+S → LC: Submit"
    )
