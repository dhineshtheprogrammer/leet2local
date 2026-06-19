# Leet2Local

[![PyPI](https://img.shields.io/pypi/v/leet2local)](https://pypi.org/project/leet2local/)
[![Python](https://img.shields.io/pypi/pyversions/leet2local)](https://pypi.org/project/leet2local/)
[![CI](https://github.com/dhineshtheprogrammer/leet2local/actions/workflows/ci.yml/badge.svg)](https://github.com/dhineshtheprogrammer/leet2local/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A CLI tool that brings LeetCode problems into your local IDE. Fetch problem descriptions, solve in your editor, run tests locally, and submit directly to LeetCode — all from the terminal.

```
lc fetch 1 --lang python
lc run 1
lc submit 1
```

---

## Features

- **Fetch any problem** by number — creates a local directory with the description, code stub, and sample test cases
- **Run locally** — executes your solution against sample test cases without touching LeetCode servers
- **Submit remotely** — sends your code to LeetCode and polls for full results including hidden test cases, runtime, and memory percentile
- **Multi-language** — Python, JavaScript, C++, and Java
- **VS Code integration** — generates `tasks.json` for keyboard-shortcut access to all commands
- **Secure auth** — session cookies stored in OS native keychain (Windows Credential Manager / macOS Keychain)

---

## Installation

**Requirements:** Python 3.11+

```bash
pip install leet2local
```

Or install from source:

```bash
git clone https://github.com/dhineshtheprogrammer/leet2local.git
cd Leet2Local
pip install -e .
```

For development (includes pytest and ruff):

```bash
pip install -e ".[dev]"
```

---

## Quick Start

### 1. Log in

Get your session cookies from your browser after logging in to leetcode.com:

1. Open DevTools → Application → Cookies → `leetcode.com`
2. Copy `LEETCODE_SESSION` and `csrftoken`

```bash
lc login
```

### 2. Fetch a problem

```bash
lc fetch 1              # Two Sum, defaults to Python
lc fetch 42 --lang cpp  # Trapping Rain Water in C++
```

This creates:

```
./leetcode/1-two-sum/
├── question.md        # Problem description in Markdown
├── solution.py        # Code stub from LeetCode
└── test_cases.json    # Sample inputs and expected outputs
```

### 3. Write your solution

Open `solution.py` in your editor and implement the function.

### 4. Run locally

```bash
lc run 1
```

```
┌─ Test Results ──────────────────────────────────┐
│ #  │ Status │ Details                           │
│ 0  │  PASS  │                                   │
│ 1  │  PASS  │                                   │
│ 2  │  FAIL  │ got: [] expected: [0, 1]          │
└────────────────────────────────────────────────-┘
✗ 1/3 test(s) failed
```

### 5. Submit to LeetCode

```bash
lc submit 1
```

```
┌─ Accepted ──────────────────────────────────────┐
│ Runtime: 52 ms (beats 87.3%)                    │
│ Memory:  16.4 MB (beats 62.1%)                  │
│ Tests:   54/54                                  │
└─────────────────────────────────────────────────┘
```

---

## Commands

| Command | Description |
|---|---|
| `lc login` | Store LeetCode session cookies securely |
| `lc fetch <number> [--lang]` | Fetch problem and create local files |
| `lc run <number>` | Run solution against sample test cases |
| `lc submit <number>` | Submit to LeetCode and get full results |
| `lc config` | Show current configuration |
| `lc config --set key=value` | Update a config value |
| `lc config --vscode-init` | Generate `.vscode/tasks.json` |

---

## Language Support

| Language | Flag | Runtime Required |
|---|---|---|
| Python 3 | `--lang python` | `python` |
| JavaScript | `--lang javascript` | `node` |
| C++ | `--lang cpp` | `g++` |
| Java | `--lang java` | `javac`, `java` |

Set your default language so you don't need `--lang` on every fetch:

```bash
lc config --set settings.default_language=javascript
```

---

## Configuration

On first run, create `.leet2local.toml` in your project root:

```toml
[settings]
default_language = "python"   # python | javascript | cpp | java
problems_dir = "./leetcode"   # where problem directories are created
run_mode = "local"            # local | remote

[api]
graphql_endpoint = "https://leetcode.com/graphql"
request_timeout = 30
max_retries = 5

[runtime]
python_cmd = "python"
node_cmd = "node"
java_cmd = "java"
javac_cmd = "javac"
cpp_compiler = "g++"
runner_timeout = 10           # seconds per test execution

[display]
show_difficulty = true
show_tags = false             # hide tags to avoid spoilers
syntax_highlight = true
```

Config is loaded from the nearest `.leet2local.toml` walking up from the current directory, falling back to `~/.config/leet2local/config.toml`.

---

## VS Code Integration

Generate keyboard-shortcut tasks:

```bash
lc config --vscode-init
```

This creates `.vscode/tasks.json` with three tasks. Add to your `keybindings.json`:

```json
[
  { "key": "ctrl+shift+r", "command": "workbench.action.tasks.runTask", "args": "LC: Run Local" },
  { "key": "ctrl+shift+s", "command": "workbench.action.tasks.runTask", "args": "LC: Submit" }
]
```

---

## How It Works

```
lc fetch 1
  └─ GraphQL: questionList (slug resolution)
  └─ GraphQL: questionData (description, stub, test cases)
  └─ HTML → Markdown (BeautifulSoup + markdownify)
  └─ Write question.md, solution.py, test_cases.json

lc run 1
  └─ Read test_cases.json
  └─ Render Jinja2 test harness template
  └─ subprocess → python harness.py
  └─ Parse LEET_PASS / LEET_FAIL / LEET_ERROR output lines

lc submit 1
  └─ GraphQL: submitCode mutation → submission_id
  └─ Poll: checkSubmission every 2s
  └─ Display Rich result table
```

---

## Project Structure

```
Leet2Local/
├── leet2local/
│   ├── cli.py              # Typer CLI entry point
│   ├── auth.py             # Login, keyring credential storage
│   ├── fetcher.py          # GraphQL client, file creation
│   ├── runner.py           # Local runner dispatcher
│   ├── submitter.py        # Remote submission + polling
│   ├── html_parser.py      # HTML → Markdown conversion
│   ├── models.py           # Pydantic data models
│   ├── config.py           # TOML config management
│   ├── queries.py          # GraphQL query strings
│   ├── rate_limiter.py     # Tenacity retry decorator
│   └── runners/
│       ├── base.py         # Abstract Runner base class
│       ├── python_runner.py
│       ├── javascript_runner.py
│       ├── cpp_runner.py
│       └── java_runner.py
├── templates/              # Jinja2 test harness templates
├── scripts/
│   └── generate_slug_map.py  # Build slug fallback map
└── tests/
```

---

## Limitations

- **Sample test cases only** for local runs — hidden test cases require `lc submit`
- LeetCode's API is unofficial and undocumented; field names may change
- C++ and Java require the respective compilers installed and on PATH
- `lc submit` requires a valid session cookie (obtained via `lc login`)

---

## Development

```bash
# Run tests
pytest

# Lint
ruff check .

# Regenerate slug fallback map (run once, requires internet)
python scripts/generate_slug_map.py
```

---

## License

MIT
