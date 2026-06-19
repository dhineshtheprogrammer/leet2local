from __future__ import annotations

import httpx
import keyring
import typer

_SERVICE = "leet2local"
_SESSION_KEY = "LEETCODE_SESSION"
_CSRF_KEY = "csrftoken"

_LOGIN_URL = "https://leetcode.com/accounts/login/"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


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
        "User-Agent": _USER_AGENT,
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


# ---------------------------------------------------------------------------
# Credential-based login
# ---------------------------------------------------------------------------

def login_with_credentials(username: str, password: str) -> None:
    """Login with username/email + password, store resulting session cookies."""
    with httpx.Client(
        follow_redirects=True,
        timeout=20,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        # Step 1: GET login page to obtain the initial CSRF token cookie
        resp = client.get(_LOGIN_URL)
        resp.raise_for_status()

        csrf = client.cookies.get("csrftoken")
        if not csrf:
            raise AuthError(
                "Could not obtain CSRF token from LeetCode login page. "
                "LeetCode may be blocking automated access — try the cookie method instead."
            )

        # Step 2: POST credentials as form data
        resp = client.post(
            _LOGIN_URL,
            data={
                "csrfmiddlewaretoken": csrf,
                "login": username,
                "password": password,
                "next": "/",
            },
            headers={
                "Referer": _LOGIN_URL,
                "X-CSRFToken": csrf,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        # Step 3: Extract post-login cookies
        session = client.cookies.get("LEETCODE_SESSION")
        new_csrf = client.cookies.get("csrftoken") or csrf

        if not session:
            # LeetCode returns 200 even on bad credentials (shows the login page again)
            raise AuthError(
                "Login failed — invalid username/password, or LeetCode triggered a CAPTCHA.\n"
                "If credentials are correct, log in via your browser first to clear the CAPTCHA,\n"
                "then re-run [bold]lc login[/bold] using the cookie method."
            )

    save_credentials(session, new_csrf)


# ---------------------------------------------------------------------------
# Interactive login flows
# ---------------------------------------------------------------------------

def run_login_flow(username: str | None = None, password: str | None = None) -> None:
    """Interactive login. Uses credential flow if username provided, cookie flow otherwise."""
    from rich.console import Console

    console = Console(legacy_windows=False)

    if username is not None:
        _credential_flow(console, username, password)
    else:
        _cookie_flow(console)


def _credential_flow(console, username: str, password: str | None) -> None:
    from rich.panel import Panel

    if not password:
        password = typer.prompt("Password", hide_input=True)

    console.print(f"[dim]Logging in as [bold]{username}[/bold]...[/dim]")

    try:
        login_with_credentials(username, password)
    except AuthError as e:
        console.print(f"[red]✗ Login failed:[/red] {e}")
        raise typer.Exit(1)
    except httpx.HTTPError as e:
        console.print(f"[red]✗ Network error:[/red] {e}")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"Logged in as [bold]{username}[/bold]\n"
            "Session stored securely in OS keychain.",
            title="[green]✓ Login successful[/green]",
            border_style="green",
        )
    )


def _cookie_flow(console) -> None:
    from rich.panel import Panel

    console.print(
        Panel(
            "[bold]How to get your cookies:[/bold]\n"
            "1. Log in to [link=https://leetcode.com]leetcode.com[/link] in your browser\n"
            "2. Open DevTools → Application → Cookies → leetcode.com\n"
            "3. Copy the values for [cyan]LEETCODE_SESSION[/cyan] and [cyan]csrftoken[/cyan]",
            title="LeetCode Login (cookie method)",
            border_style="blue",
        )
    )

    session = typer.prompt("Paste your LEETCODE_SESSION cookie value", hide_input=True).strip()
    csrf = typer.prompt("Paste your csrftoken cookie value", hide_input=True).strip()

    if not session or not csrf:
        console.print("[red]Error:[/red] Both values are required.")
        raise typer.Exit(1)

    console.print("[dim]Validating session...[/dim]")
    save_credentials(session, csrf)

    if validate_session():
        console.print(
            Panel(
                "Session stored securely in OS keychain.",
                title="[green]✓ Login successful[/green]",
                border_style="green",
            )
        )
    else:
        keyring.delete_password(_SERVICE, _SESSION_KEY)
        keyring.delete_password(_SERVICE, _CSRF_KEY)
        console.print(
            "[red]✗[/red] Session validation failed. "
            "Make sure you are logged in to LeetCode and copied the correct cookies."
        )
        raise typer.Exit(1)
