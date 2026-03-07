# Ai-Agents

AI agents for understanding the PyTorch repository. This project includes an MCP server to pull GitHub issues.

## GitHub Issues MCP Server

An MCP (Model Context Protocol) server that exposes GitHub repository issues as tools for AI agents and Cursor IDE. Defaults to the [pytorch/pytorch](https://github.com/pytorch/pytorch) repository.

### Setup

1. **Create a virtual environment and install dependencies:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Create a GitHub Personal Access Token:**
   - Go to [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)
   - Create a token (classic or fine-grained) with `public_repo` scope for read-only access
   - Copy the token

3. **Configure authentication** (choose one):
   - **Option A:** Copy `.env.example` to `.env` and add your token:
     ```bash
     cp .env.example .env
     # Edit .env and set GITHUB_TOKEN=your_token_here
     ```
   - **Option B:** Add the token to `.cursor/mcp.json` in the `env` block:
     ```json
     "env": {
       "GITHUB_TOKEN": "your_token_here"
     }
     ```

4. **Restart Cursor** after configuring the MCP server (if using Cursor integration).

   If the MCP server fails to start, ensure Cursor uses the project's Python with dependencies installed. You can set the full path in `.cursor/mcp.json`:
   ```json
   "command": "/path/to/Ai-Agents/.venv/bin/python",
   "args": ["run_server.py"]
   ```

### Usage in Cursor

The server is configured in `.cursor/mcp.json`. After setup, Cursor will load the `github-issues` tools automatically. You can ask the AI to:
- "List open issues from PyTorch"
- "Get issue #12345 from pytorch/pytorch"
- "Show me bug issues with the module: autograd label"

### Tools

| Tool | Description |
|------|-------------|
| `list_issues` | List issues from a repository. Params: owner, repo, state, labels, sort, per_page, page, include_pull_requests |
| `get_issue` | Get full details of a single issue by number |

### Running Standalone

To run the server directly (e.g., for testing with MCP Inspector):

```bash
uv run --with mcp run_server.py
```

Or with pip:

```bash
python run_server.py
```

Note: When run standalone, the server uses stdio transport. Use [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to test.
