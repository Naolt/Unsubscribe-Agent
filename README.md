# Unsubscribe Agent

Automates unsubscribing from marketing/notification emails via a browser agent, with a Model Context Protocol (MCP) server exposing tools to trigger the flow.

## Currently Implemented Features

- Minimal unsubscribe automation using the browser-use agent.

- Handles common email providers (Gmail, Outlook, Yahoo) with a provider-agnostic flow.

- Supports finding messages, locating unsubscribe links/buttons, and completing opt-outs.

- Returns clear result messages for success, failure, or edge cases (e.g., user not subscribed).

- Manual login via login_to_provider tool (temporary placeholder).

- Basic MCP server exposing:

    - ping() for health check

    - unsubscribe(query: str) to trigger the agent flow

## Requirements
- Python 3.13+
- `uv` or `pip` to install deps
- A Google API Key(configure via `.env`)

## Setup
1. Install dependencies:
```bash
uv sync  # or: pip install -e .
```
2. Create `.env`:
```bash
cp .env.example .env  
# then edit and add your secrets (e.g., GOOGLE_API_KEY, etc.)
```

## Running locally (demo)
```bash
uv run main.py 
```
This runs a demo task: "Unsubscribe from atlassian".

The agent uses a tool `login_with_google` which currently prompts you in the console. Answer `y` after logging in the opened browser window.

## MCP Server
Start the MCP server via the FastMCP CLI (HTTP transport on port 8000):
```bash
fastmcp run mcp.py:mcp --transport http --port 8000
```

Tools exposed:
- `ping() -> str`: health check (returns `"pong"`).
- `unsubscribe(query: str) -> str`: triggers the unsubscribe flow for the given natural-language query and returns a concise result message.

### Example MCP usage
From an MCP client, call:
```text
unsubscribe("Unsubscribe from Atlassian marketing emails")
```

## Development notes
- The agent prompt is provider-agnostic and tries built-in unsubscribe controls or footer links.
- `unsubscribe_by_request()` returns:
  - on success: the agent’s final result text or `"Success"`
  - on failure: `"Failed: <error>"` or `"Failed"`
  - unknown/not completed: `"Result unavailable"`

## License
MIT

