# MCP Web Testing Interface

A FastAPI web application that provides a chat interface for testing **any MCP-compatible server** with AWS Bedrock Claude models.

## Features

- 🤖 **Universal MCP Client** - Works with any MCP server via stdio
- 🔧 **Configurable** - Switch between MCP servers using environment variables
- 🧪 **Testing Interface** - Interactive chat UI for testing tools
- ⚡ **Throttling Protection** - Built-in retry logic and rate limiting
- 🎯 **Verified Claude Models** - Only includes working Claude models

## Quick Start

### 1. Install Dependencies

```bash
cd web_app
pip install fastapi uvicorn boto3 httpx mcp
```

### 2. Configure AWS Credentials

```bash
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_REGION="us-east-1"  # or us-west-2, etc.
```

### 3. Run with Default Weather Server

```bash
python app.py
```

Visit http://localhost:8000 and start chatting!

## Using Custom MCP Servers

The web app can connect to **any MCP server**, not just the weather server!

### Configuration

Set these environment variables before starting the app:

```bash
# The command to run your MCP server
export MCP_SERVER_COMMAND="python"

# Comma-separated arguments (no spaces after commas)
export MCP_SERVER_ARGS="-m,mcp_server.server"

# Start the app
python app.py
```

### Examples

#### Use the Weather Server (Default)
```bash
export MCP_SERVER_COMMAND="python"
export MCP_SERVER_ARGS="-m,mcp_server.server"
python app.py
```

#### Use Filesystem MCP Server
```bash
export MCP_SERVER_COMMAND="npx"
export MCP_SERVER_ARGS="-y,@modelcontextprotocol/server-filesystem,/tmp"
python app.py
```

#### Use Your Custom Python Server
```bash
export MCP_SERVER_COMMAND="python"
export MCP_SERVER_ARGS="-m,my_company.mcp_server,--verbose"
python app.py
```

#### Use Your Custom Node.js Server
```bash
export MCP_SERVER_COMMAND="node"
export MCP_SERVER_ARGS="dist/server.js,--config,config.json"
python app.py
```

#### Use an Executable
```bash
export MCP_SERVER_COMMAND="/usr/local/bin/my-mcp-server"
export MCP_SERVER_ARGS="--port,3000,--log-level,debug"
python app.py
```

## Environment Variables Reference

| Variable                | Description                                   | Default                        | Required |
| ----------------------- | --------------------------------------------- | ------------------------------ | -------- |
| `MCP_SERVER_COMMAND`    | Command to run MCP server                     | `python`                       | No       |
| `MCP_SERVER_ARGS`       | Comma-separated server args                   | `-m,mcp_server.server` | No       |
| `AWS_ACCESS_KEY_ID`     | AWS access key                                | -                              | Yes      |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key                                | -                              | Yes      |
| `AWS_SESSION_TOKEN`     | AWS session token (if using temp credentials) | -                              | No       |
| `AWS_REGION`            | AWS region                                    | `us-east-1`                    | No       |
| `AWS_DEFAULT_REGION`    | Fallback AWS region                           | -                              | No       |

## How It Works

```
┌─────────────────┐
│   Web Browser   │
│  (localhost:8000)│
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│   FastAPI App   │
│   (app.py)      │
└────┬───────┬────┘
     │       │
     │       └──────→ ┌──────────────────┐
     │                │  AWS Bedrock     │
     │                │  Claude Models   │
     │                └──────────────────┘
     ↓
┌─────────────────┐
│   MCP Server    │  ← Configurable via env vars
│   (stdio)       │
└─────────────────┘
```

1. **Web Browser** sends user messages to FastAPI
2. **FastAPI** sends messages to Claude via AWS Bedrock
3. **Claude** decides to use tools and requests tool calls
4. **FastAPI** executes tools via the **MCP Server**
5. **MCP Server** performs actions and returns results
6. **FastAPI** sends results back to Claude
7. **Claude** formulates final response
8. **Web Browser** displays the response

## Available Claude Models

The web app includes only **verified working models**:

- **Claude 3.5 Sonnet** (`anthropic.claude-3-5-sonnet-20240620-v1:0`) - Default, best balance
- **Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`) - Good alternative
- **Claude 3 Haiku** (`anthropic.claude-3-haiku-20240307-v1:0`) - Fastest, most cost-effective

See [TESTING_RESULTS.md](../TESTING_RESULTS.md) for full model testing details.

## Throttling Protection

The app includes three layers of throttling protection:

1. **Boto3 Adaptive Retry** - Up to 10 retries with exponential backoff
2. **Inter-iteration Delays** - 200ms delay between tool calls
3. **Manual Retry Logic** - Catches ThrottlingException and retries once

This prevents `ThrottlingException` errors when Claude makes multiple rapid tool calls.

## Testing Your Custom Server

1. **Set environment variables** for your server
2. **Start the app:** `python app.py`
3. **Check startup logs** - Should show: `Starting MCP server: <your-command> <args>`
4. **Check tool discovery** - Should show: `Connected to MCP server. Available tools: [...]`
5. **Open browser** to http://localhost:8000
6. **Ask Claude** what tools are available
7. **Test your tools** by asking Claude to use them

## Troubleshooting

### MCP Server Not Starting

**Error:** `Can't find module 'your_mcp_server.server'`

**Solution:** Ensure your MCP server is installed:
```bash
pip install -e /path/to/your-mcp-server
```

### No Tools Discovered

**Error:** `Connected to MCP server. Available tools: []`

**Solution:** Verify your MCP server has registered tools with `@mcp.tool()` decorators.

### AWS Throttling Errors

**Error:** `ThrottlingException: Rate exceeded`

**Solution:** The app has built-in throttling protection. If you still see errors:
1. Check your AWS Bedrock quotas in the AWS Console
2. Reduce request rate by spacing out queries
3. Increase the delay in `app.py` (currently 200ms)

### AWS Credentials Expired

**Error:** `ExpiredTokenException` or `SSOTokenLoadError`

**Solution:** Refresh your AWS credentials:
```bash
export AWS_ACCESS_KEY_ID="new-key"
export AWS_SECRET_ACCESS_KEY="new-secret"
export AWS_SESSION_TOKEN="new-token"  # if using temporary credentials
```

### Wrong MCP Server Running

**Check which server is configured:**
```bash
echo $MCP_SERVER_COMMAND
echo $MCP_SERVER_ARGS
```

**Reset to default:**
```bash
unset MCP_SERVER_COMMAND
unset MCP_SERVER_ARGS
python app.py  # Will use weather server
```

## Architecture

The web app follows a clean architecture pattern:

```python
# Boto3 client with adaptive retry
boto_config = Config(retries={'max_attempts': 10, 'mode': 'adaptive'})
bedrock_runtime = boto3.client('bedrock-runtime', config=boto_config)

# MCP server configured via env vars
MCP_SERVER_COMMAND = os.environ.get("MCP_SERVER_COMMAND", "python")
MCP_SERVER_ARGS = os.environ.get("MCP_SERVER_ARGS", "-m,mcp_server.server").split(",")

# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start MCP server
    # Connect via stdio
    # Discover tools
    yield
    # Cleanup
```

## Development

### Run in Development Mode

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Enable Debug Logging

Add to `app.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test with Different Models

Change the model in the web UI dropdown or modify the default in `app.py`:
```python
class ChatRequest(BaseModel):
    model: str = "anthropic.claude-3-haiku-20240307-v1:0"  # Use fastest model
```

## Security Notes

⚠️ **This is a testing interface, not production-ready:**

- Binds to `0.0.0.0` (all interfaces) - Change to `127.0.0.1` for production
- No authentication or authorization
- No rate limiting (relies on AWS throttling)
- CORS enabled for all origins
- No input validation beyond basic types

For production use, add:
- Authentication (OAuth, API keys, etc.)
- Rate limiting per user/IP
- Input sanitization and validation
- HTTPS/TLS
- Proper error handling and logging
- Request timeouts

## Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io)
- [AWS Bedrock Claude Models](https://docs.aws.amazon.com/bedrock/latest/userguide/models-anthropic-claude.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Creating Custom MCP Servers](../CONTRIBUTING.md#creating-your-own-mcp-server)

## License

MIT - See [LICENSE](../LICENSE) for details
