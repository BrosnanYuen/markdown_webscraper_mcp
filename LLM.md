# LLM Tool Calling Guide

Use these tool calls against the `markdown_webscraper_mcp` server.

## Available tools

- `get_website {url, dir_path}`
- `get_status_website {url, dir_path}`
- `get_wildcard_website {url, dir_path}` (if enabled)

## Basic workflow

1. Call `get_website` or `get_wildcard_website`.
2. Expect immediate status:
   - `fetching website and converting to markdown in progress!`
3. Poll `get_status_website(url, dir_path)` until status becomes:
   - `fetch completed and markdown saved!`
   - or terminal error (`fetching timed out!`, `failed to fetch!`).

## Example tool calling

### Downloading a single url, converting that to .md, and placing it into dir_path

```text
Start scraping with get_website {url="https://www.ti.com/lit/ds/sprs590g/sprs590g.pdf", dir_path="/tmp/test/"}
After start, to get current status, poll get_status_website {url, dir_path} until completed.
```

### Wildcard download all urls given the same base url, converting that to .md, and placing it into dir_path

```text
Will fetch every item in the website that has the  same base url like "https://example.com/test"  "https://example.com/test/robot"  "https://example.com/test/laser"  "https://example.com/test/cat/dog" ...etc
Start scraping with get_wildcard_website {url="https://example.com/test", dir_path="/tmp/test/"}
To get current status, poll get_status_website {url, dir_path} until completed.
WILL TAKE A LONG TIME
```

## Expected status payloads

```json
{"status": "fetching website and converting to markdown in progress!"}
```

```json
{"status": "fetch completed and markdown saved!"}
```

```json
{"status": "fetching timed out!"}
```

```json
{"status": "failed to fetch!"}
```
