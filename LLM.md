# LLM Tool Calling Guide

Use these tool calls against the `markdown_webscraper_mcp` server.

## Available tools

- `get_website {url, dir_path}`
- `get_status_website {url, dir_path}`
- `get_wildcard_website {url, dir_path}` (if enabled)

## Basic workflow

1. Call `get_website` or `get_wildcard_website`.
2. Expect immediate status:
   - `fetching website and converting to markdown in progress!` with an `operation` field
3. Listen for MCP server notifications:
   - completion notification contains: `fetch completed and markdown saved!` plus `operation`
   - failure notification contains: `failed to fetch!` (or timeout status) plus `operation`

## Concurrency behavior

- Tool calls are asynchronous and non-blocking.
- Jobs are queued FIFO per MCP session.
- Each MCP session has its own dedicated worker thread.
- Status lookups are scoped to the calling session.

## Example tool calling

### Downloading a single url, converting that to .md, and placing it into dir_path

```text
Start scraping with get_website {url="https://www.ti.com/lit/ds/sprs590g/sprs590g.pdf", dir_path="/tmp/test/"}
After start, wait for completion notification from MCP server
```

### Wildcard download all urls given the same base url, converting that to .md, and placing it into dir_path

```text
Will fetch every item in the website that has the  same base url like "https://example.com/test"  "https://example.com/test/robot"  "https://example.com/test/laser"  "https://example.com/test/cat/dog" ...etc
Start scraping with get_wildcard_website {url="https://example.com/test", dir_path="/tmp/test/"}
After start, wait for completion notification from MCP server
WILL TAKE A LONG TIME
```

## Expected status payloads

```json
{"status": "fetching website and converting to markdown in progress!", "operation": "get_website"}
```

```json
{"status": "fetch completed and markdown saved!", "operation": "get_website"}
```

```json
{"status": "fetching timed out!", "operation": "get_website"}
```

```json
{"status": "failed to fetch!", "operation": "get_website"}
```
