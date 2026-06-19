# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-06-19

### Added
- `lc fetch <number>` — fetch any LeetCode problem by number; creates a local directory
  with `question.md`, `solution.<ext>`, `test_cases.json`, and `.meta.json`
- `lc run <number>` — run solution locally against sample test cases using a Jinja2
  test harness subprocess; supports Python, JavaScript, C++, and Java
- `lc submit <number>` — submit solution to LeetCode and poll for full results including
  runtime percentile, memory percentile, and hidden test count
- `lc login` — store LeetCode session credentials securely in the OS native keychain
  (Windows Credential Manager / macOS Keychain / libsecret on Linux)
- `lc config` — view and update TOML configuration; generate `.vscode/tasks.json`
- Bundled slug fallback map (3963 entries) for offline problem-number-to-slug resolution
- Multi-language support: Python 3, JavaScript (Node.js), C++ (g++), Java (JDK)
- Exponential backoff retry on LeetCode rate-limit responses (HTTP 429)
- Rate limiter with configurable max retries via `.leet2local.toml`
