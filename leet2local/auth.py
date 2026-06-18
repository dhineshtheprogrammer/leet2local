from __future__ import annotations

import httpx
import keyring
import typer

_SERVICE = "leet2local"
_SESSION_KEY = "LEETCODE_SESSION"
_CSRF_KEY = "csrftoken"


class AuthError(Exception):
    pass


def save_credentials(session: str, csrf: str) -> None:
    keyring.set_password(_SERVICE, _SESSION_KEY, session)
    keyring.set_password(_SERVICE, _CSRF_KEY, csrf)


def load_credentials() -> tuple[str, str]:
    session = keyring.get_password(_SERVICE, _SESSION_KEY)
    csrf = keyring.get_password(_SERVICE, _CSRF_KEY)
    if not session or not csrf:
        raise AuthError(
            "Not logged in. Run [bold]lc login[/bold] first to store your session cookies."
        )
    return session, csrf


def get_auth_headers() -> dict[str, str]:
    session, csrf = load_credentials()
    return {
        "Cookie": f"LEETCODE_SESSION={session}; csrftoken={csrf}",
        "x-csrftoken": csrf,
        "Referer": "https://leetcode.com",
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }


def validate_session() -> bool:
    """Returns True if the stored session is valid."""
    try:
        headers = get_auth_headers()
    except AuthError:
        return False

    with httpx.Client(timeout=10) as client:
        resp = client.get("https://leetcode.com/api/problems/all/", headers=headers)
        return resp.status_code == 200


def run_login_flow() -> None:
    """Interactive login: prompt for cookies, validate, store."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console(legacy_windows=False)
    console.print(
        Panel(
            "[bold]How to get your cookies:[/bold]\n"
            "1. Log in to [link=https://leetcode.com]leetcode.com[/link] in your browser\n"
            "2. Open DevTools → Application → Cookies → leetcode.com\n"
            "3. Copy the values for [cyan]LEETCODE_SESSION[/cyan] and [cyan]csrftoken[/cyan]",
            title="LeetCode Login",
            border_style="blue",
        )
    )

    session = typer.prompt("Paste your LEETCODE_SESSION cookie value", hide_input=True)
    csrf = typer.prompt("Paste your csrftoken cookie value", hide_input=True)

    session = session.strip()
    csrf = csrf.strip()

    if not session or not csrf:
        console.print("[red]Error:[/red] Both values are required.")
        raise typer.Exit(1)

    console.print("[dim]Validating session...[/dim]")

    # Temporarily save to validate
    save_credentials(session, csrf)

    if validate_session():
        console.print("[green]✓[/green] Login successful. Credentials stored securely.")
    else:
        # Clear invalid credentials
        keyring.delete_password(_SERVICE, _SESSION_KEY)
        keyring.delete_password(_SERVICE, _CSRF_KEY)
        console.print(
            "[red]✗[/red] Session validation failed. "
            "Make sure you are logged in to LeetCode and copied the correct cookies."
        )
        raise typer.Exit(1)
