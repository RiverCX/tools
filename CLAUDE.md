# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup (uv recommended)
uv venv && uv pip install -e .[dev]

# Run
lt                              # Analyze LLM request traces (auto-finds full.json)
lt <log_file> -o report_dir     # Analyze specific log (supports .json and .log formats)
lt --session <id>               # Filter by session ID

# Dev
black . && ruff check . && mypy .
pytest
```

## Architecture

```
llm_trace_analyzer/  (CLI: lt)
├── loader.py      # LogLoader - parses LLM_IO_TRACE logs (JSON Lines or text), auto-find full.json
├── parser.py      # TraceParser - merges fragmented request bodies
├── analyzer.py    # ChainAnalyzer - links requests/responses, identifies subagents
├── models.py      # LLMRequest, LLMResponse, LLMChain, AnalysisResult
├── reporter.py    # HTMLReporter - generates multi-session reports
├── templates.py   # HTML/CSS templates
├── constants.py   # TraceEventType enum
└── main.py        # CLI entry point
```

Key patterns:
- Entry points defined in `pyproject.toml` `[project.scripts]`
- Package exports main class via `__init__.py`
- Reports use embedded HTML templates (no external template engine)

## Default Search Paths

- `~/.office-claw/.jiuwenclaw/service_default/.logs/full.json` (fallback: `full.log`)

## Data Flow

Log → LogLoader → TraceParser → ChainAnalyzer → AnalysisResult → HTMLReporter

Parses `[LLM_IO_TRACE]` entries with:
- Request body fragments (`body_part 1/N → N/N`) merged by TraceParser
- Request-response pairing by iteration number
- Subagent session identification (`subagent_<task_id>`)
- Parent-child session linking via spawn_subagent timestamps

## Gotchas

- **Windows paths** - use backslashes in PowerShell/CMD
- **OfficeClaw dependency** - requires `LOG_LEVEL=debug` for LLM_IO_TRACE logging
- **Test fixtures** - tests use `tests/fixtures/llm_trace_b2fbb87bbeeb.log` as sample data, fixtures defined in `conftest.py`
