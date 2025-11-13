import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

# Configure boto3 with retry settings
boto_config = Config(
    retries={
        "max_attempts": 10,
        "mode": "adaptive",  # Uses adaptive retry mode which backs off on throttling
    }
)

# Initialize AWS Bedrock client
# Region can be set via AWS_REGION or AWS_DEFAULT_REGION environment variable
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")),
    config=boto_config,
)

# MCP client session, tools, and resources
mcp_session: ClientSession | None = None
mcp_tools: list[dict[str, Any]] = []
mcp_resources: list[dict[str, Any]] = []
mcp_read = None
mcp_write = None

# MCP Server Configuration - Can be customized via environment variables
# Example: export MCP_SERVER_COMMAND="node"
#          export MCP_SERVER_ARGS="path/to/server.js,--option,value"
MCP_SERVER_COMMAND = os.environ.get("MCP_SERVER_COMMAND", "python")
MCP_SERVER_ARGS = os.environ.get("MCP_SERVER_ARGS", "-m,mcp_server.server").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage MCP connection lifecycle"""
    global mcp_session, mcp_tools, mcp_resources, mcp_read, mcp_write

    # Startup: Initialize MCP connection
    print(f"Starting MCP server: {MCP_SERVER_COMMAND} {' '.join(MCP_SERVER_ARGS)}")

    server_params = StdioServerParameters(
        command=MCP_SERVER_COMMAND,
        args=MCP_SERVER_ARGS,
    )

    stdio = stdio_client(server_params)
    mcp_read, mcp_write = await stdio.__aenter__()

    session = ClientSession(mcp_read, mcp_write)
    await session.__aenter__()

    # Wait for initialization
    await session.initialize()
    mcp_session = session

    # List available tools
    tools_result = await session.list_tools()
    mcp_tools = [
        {"name": tool.name, "description": tool.description, "input_schema": tool.inputSchema}
        for tool in tools_result.tools
    ]
    print(f"Connected to MCP server. Available tools: {[t['name'] for t in mcp_tools]}")

    # List available resources
    resources_result = await session.list_resources()
    mcp_resources = [
        {
            "uri": resource.uri,
            "name": resource.name,
            "description": resource.description,
            "mimeType": resource.mimeType,
        }
        for resource in resources_result.resources
    ]
    print(f"Connected to MCP server. Available resources: {[r['uri'] for r in mcp_resources]}")

    yield

    # Shutdown
    await session.__aexit__(None, None, None)
    await stdio.__aexit__(None, None, None)


app = FastAPI(lifespan=lifespan)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def handle_claude_with_tools(
    model_id: str, body: dict, messages: list, client_ip: str | None = None
) -> str:
    """Handle Claude's tool use loop with throttling protection

    Args:
        model_id: The Bedrock model ID to use
        body: The request body for the model
        messages: The conversation messages
        client_ip: Optional client IP address to pass to tools that need it
    """
    max_iterations = 5

    for iteration in range(max_iterations):
        # Add small delay between iterations to avoid throttling
        if iteration > 0:
            await asyncio.sleep(0.2)  # 200ms delay between tool iterations

        # Call Claude with retry handling
        try:
            response = bedrock_runtime.invoke_model(modelId=model_id, body=json.dumps(body))
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ThrottlingException":
                # Wait and retry once more
                await asyncio.sleep(2)
                response = bedrock_runtime.invoke_model(modelId=model_id, body=json.dumps(body))
            else:
                raise

        response_body = json.loads(response["body"].read())

        # Check stop reason
        stop_reason = response_body.get("stop_reason")

        if stop_reason == "tool_use":
            # Claude wants to use a tool
            content_blocks = response_body.get("content", [])

            # Build assistant message with tool use (but only if there's actual content)
            if content_blocks:
                assistant_message = {"role": "assistant", "content": content_blocks}
                messages.append(assistant_message)

            # Execute tool calls and collect results
            tool_results = []
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    tool_name = block.get("name")
                    tool_input = block.get("input", {})
                    tool_use_id = block.get("id")

                    # Inject client IP for get_current_time tool if available
                    if tool_name == "get_current_time" and client_ip:
                        # Only add IP if not already provided by the user
                        if "ip_address" not in tool_input or not tool_input.get("ip_address"):
                            tool_input["ip_address"] = client_ip

                    # Handle resource reading vs tool calling
                    try:
                        if tool_name == "read_resource":
                            # Read an MCP resource
                            uri = tool_input.get("uri", "")
                            result = await mcp_session.read_resource(uri)
                            content = (
                                str(result.contents[0].text) if result.contents else "No content"
                            )
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": content,
                                }
                            )
                        else:
                            # Call a regular MCP tool
                            result = await mcp_session.call_tool(tool_name, arguments=tool_input)
                            tool_results.append(
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": str(result.content[0].text)
                                    if result.content
                                    else "No result",
                                }
                            )
                    except Exception as e:
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": f"Error: {str(e)}",
                                "is_error": True,
                            }
                        )

            # Add tool results as user message (only if we have results)
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Update body for next iteration
            body["messages"] = messages

        elif stop_reason == "end_turn":
            # Claude is done, extract final response
            content_blocks = response_body.get("content", [])
            text_parts = [
                block.get("text", "") for block in content_blocks if block.get("type") == "text"
            ]
            return "\n".join(text_parts)
        else:
            # Unexpected stop reason
            content_blocks = response_body.get("content", [])
            text_parts = [
                block.get("text", "") for block in content_blocks if block.get("type") == "text"
            ]
            return "\n".join(text_parts) if text_parts else f"Stopped with reason: {stop_reason}"

    return "Maximum iterations reached while processing tool calls."


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    # Default to Claude 3.5 Sonnet v1 - verified to work with MCP tools
    model: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    max_tokens: int = 4096
    temperature: float = 1.0
    stream: bool = False


class ChatResponse(BaseModel):
    response: str
    model: str


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the chat interface"""
    with open("static/index.html") as f:
        return f.read()


@app.get("/models")
async def list_models():
    """List available Bedrock models"""
    try:
        bedrock = boto3.client(
            service_name="bedrock",
            region_name=os.environ.get(
                "AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
            ),
        )
        response = bedrock.list_foundation_models()

        # Filter for active models that support on-demand
        models = []
        for model in response.get("modelSummaries", []):
            if model.get("modelLifecycle", {}).get("status") == "ACTIVE":
                models.append(
                    {
                        "id": model["modelId"],
                        "name": model["modelName"],
                        "provider": model["providerName"],
                    }
                )

        return {"models": models}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/chat")
async def chat(request: ChatRequest, http_request: Request):
    """Handle chat requests to AWS Bedrock with MCP tool support"""
    try:
        # Get client IP address for tools that need it (like get_current_time)
        client_ip = http_request.client.host if http_request.client else None

        # Convert messages to Claude format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # Generate current local time context for time-sensitive answers
        system_prompt = None
        try:
            now = datetime.now().astimezone()
            now_iso = now.isoformat()
            now_str = now.strftime("%A, %B %d, %Y %H:%M:%S %Z%z")

            # Build resource list
            resource_list = (
                "\n".join(
                    [
                        f"  - {r['uri']}: {r.get('description', 'No description')}"
                        for r in mcp_resources
                    ]
                )
                if mcp_resources
                else "  (none available)"
            )

            system_prompt = (
                f"Current local time: {now_str} (ISO: {now_iso}). "
                "Use this timestamp for any time-sensitive answers. "
                "\n\nFor weather requests:"
                "\n1. First call get_current_time to attempt location detection from IP"
                "\n2. If coordinates are provided in the response, use them for get_forecast"
                "\n3. If no coordinates are returned, politely ask the user for their location (city/state or lat/lon)"
                "\n4. Never make up coordinates or assume a location"
                "\n\nAvailable MCP Resources (use read_resource tool to access):"
                f"\n{resource_list}"
            )
        except Exception:
            # If timezone retrieval fails, continue without system prompt
            pass

        # Determine if model is Claude (including inference profiles)
        is_claude = (
            "anthropic.claude" in request.model or "anthropic.claude" in request.model.lower()
        )

        # Prepare the request body based on model family
        if is_claude:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "messages": messages,
            }

            # Add system prompt if available
            if system_prompt:
                body["system"] = system_prompt

            # Add MCP tools to Claude request (including built-in read_resource tool)
            if mcp_tools:
                tools = mcp_tools.copy()
                # Add read_resource tool for accessing MCP resources
                tools.append(
                    {
                        "name": "read_resource",
                        "description": "Read an MCP resource by its URI. Use this to access conversation logs, cached weather data, and other resources.",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "uri": {
                                    "type": "string",
                                    "description": "The URI of the resource to read (e.g., 'conversation://log', 'weather://cache')",
                                }
                            },
                            "required": ["uri"],
                        },
                    }
                )
                body["tools"] = tools

            # Tool use loop for Claude
            response_text = await handle_claude_with_tools(request.model, body, messages, client_ip)
            return ChatResponse(response=response_text, model=request.model)
        elif "meta.llama" in request.model:
            # Llama format
            prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
            body = {
                "prompt": prompt,
                "max_gen_len": request.max_tokens,
                "temperature": request.temperature,
            }
        elif "amazon.titan" in request.model:
            # Titan format
            body = {
                "inputText": messages[-1]["content"],
                "textGenerationConfig": {
                    "maxTokenCount": request.max_tokens,
                    "temperature": request.temperature,
                },
            }
        else:
            # Default to Claude format
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "messages": messages,
            }

        if request.stream:
            return StreamingResponse(
                stream_bedrock_response(request.model, body), media_type="text/event-stream"
            )
        else:
            # Invoke the model
            response = bedrock_runtime.invoke_model(modelId=request.model, body=json.dumps(body))

            # Parse response
            response_body = json.loads(response["body"].read())

            # Extract text based on model family
            if "anthropic.claude" in request.model:
                response_text = response_body["content"][0]["text"]
            elif "meta.llama" in request.model:
                response_text = response_body["generation"]
            elif "amazon.titan" in request.model:
                response_text = response_body["results"][0]["outputText"]
            else:
                response_text = str(response_body)

            return ChatResponse(response=response_text, model=request.model)

    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}") from e


async def stream_bedrock_response(model_id: str, body: dict):
    """Stream responses from Bedrock"""
    try:
        response = bedrock_runtime.invoke_model_with_response_stream(
            modelId=model_id, body=json.dumps(body)
        )

        for event in response["body"]:
            chunk = event.get("chunk")
            if chunk:
                chunk_data = json.loads(chunk["bytes"])

                # Extract text based on model
                if "anthropic.claude" in model_id:
                    if chunk_data.get("type") == "content_block_delta":
                        text = chunk_data.get("delta", {}).get("text", "")
                        if text:
                            yield f"data: {json.dumps({'text': text})}\n\n"
                    elif chunk_data.get("type") == "message_stop":
                        yield f"data: {json.dumps({'done': True})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


# Mount static files (will create this next)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
