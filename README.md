# markdown_webscraper_mcp

`markdown_webscraper_mcp` is a standalone MCP server that uses:

- `fastmcp>=3.2.4` for MCP server/tool wiring
- `markdown-webscraper>=0.1.4` for web scraping and markdown conversion

It supports both single URL scraping and wildcard recursive scraping (configurable), with non-blocking async job start + status polling.

## Features

- MCP tools:
  - `get_website(url, dir_path)`
  - `get_status_website(url, dir_path)`
  - `get_wildcard_website(url, dir_path)` (only when enabled)
- Immediate async response on start:
  - `{ "status": "fetching website and converting to markdown in progress!" }`
- Status responses:
  - completed: `{ "status": "fetch completed and markdown saved!" }`
  - timeout: `{ "status": "fetching timed out!" }`
  - failure: `{ "status": "failed to fetch!" }`
- Transport config via `mcp_server_url` supporting:
  - `stdio://`
  - `http://host:port/path`
  - `https://host:port/path` (server still runs HTTP transport; TLS should be terminated by proxy)

## Installation

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

For tests:

```bash
pip install -e '.[test]'
```

## Configuration

Create `config.json`:

```json
{
  "mcp_server_name": "My Webscraping MCP Server",
  "mcp_server_url": "http://localhost:8888/mcp",
  "enable_wildcard_scraping": true,
  "remove_header_footer": true,
  "markdown_convert": true,
  "time_delay": 2,
  "total_timeout": 180
}
```

## Run Server

```bash
. .venv/bin/activate
markdown-webscraper-mcp --config config.json
```

or:

```bash
python -m markdown_webscraper_mcp.cli --config config.json
```

## Tool API

### `get_website(url, dir_path)`

- Starts non-blocking scrape for a single URL (`individual_websites=[url]`)
- Returns immediate in-progress status

### `get_wildcard_website(url, dir_path)`

- Starts non-blocking recursive scrape (`wildcard_websites=[url]`)
- Available only when `enable_wildcard_scraping=true`

### `get_status_website(url, dir_path)`

- Polls the latest job status for that `(url, dir_path)` pair

## Output Structure

For each `dir_path`:

- raw downloads under `dir_path/raw_html/`
- markdown output under `dir_path/markdown/`

## Test Commands

Run unit tests:

```bash
. .venv/bin/activate
pytest tests/unit -q
```

Run integration test:

```bash
. .venv/bin/activate
RUN_INTEGRATION=1 pytest tests/integration/test_mcp_live_scrape.py -m integration -q
```

## Build Package

```bash
. .venv/bin/activate
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```
