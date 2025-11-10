import json
from typing import Optional, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import boto3
from botocore.exceptions import ClientError
import asyncio
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Initialize AWS Bedrock client
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-west-2"
)

# MCP client session and tools
mcp_session: Optional[ClientSession] = None
mcp_tools: list[dict[str, Any]] = []
mcp_read = None
mcp_write = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage MCP connection lifecycle"""
    global mcp_session, mcp_tools, mcp_read, mcp_write

    # Startup: Initialize MCP connection
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_weather_server.server"],
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
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        }
        for tool in tools_result.tools
    ]
    print(f"Connected to MCP server. Available tools: {[t['name'] for t in mcp_tools]}")

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


async def handle_claude_with_tools(model_id: str, body: dict, messages: list) -> str:
    """Handle Claude's tool use loop"""
    max_iterations = 5

    for iteration in range(max_iterations):
        # Call Claude
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )

        response_body = json.loads(response["body"].read())

        # Check stop reason
        stop_reason = response_body.get("stop_reason")

        if stop_reason == "tool_use":
            # Claude wants to use a tool
            content_blocks = response_body.get("content", [])

            # Build assistant message with tool use
            assistant_message = {"role": "assistant", "content": content_blocks}
            messages.append(assistant_message)

            # Execute tool calls and collect results
            tool_results = []
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    tool_name = block.get("name")
                    tool_input = block.get("input", {})
                    tool_use_id = block.get("id")

                    # Call the MCP tool
                    try:
                        result = await mcp_session.call_tool(tool_name, arguments=tool_input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": str(result.content[0].text) if result.content else "No result"
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })

            # Add tool results as user message
            messages.append({"role": "user", "content": tool_results})

            # Update body for next iteration
            body["messages"] = messages

        elif stop_reason == "end_turn":
            # Claude is done, extract final response
            content_blocks = response_body.get("content", [])
            text_parts = [block.get("text", "") for block in content_blocks if block.get("type") == "text"]
            return "\n".join(text_parts)
        else:
            # Unexpected stop reason
            content_blocks = response_body.get("content", [])
            text_parts = [block.get("text", "") for block in content_blocks if block.get("type") == "text"]
            return "\n".join(text_parts) if text_parts else f"Stopped with reason: {stop_reason}"

    return "Maximum iterations reached while processing tool calls."

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    # Claude 3.5 Sonnet v2 - supports MCP tools
    # If this doesn't work, try: "anthropic.claude-3-5-sonnet-20240620-v1:0"
    model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    max_tokens: int = 4096
    temperature: float = 1.0
    stream: bool = False

class ChatResponse(BaseModel):
    response: str
    model: str

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the chat interface"""
    with open("static/index.html", "r") as f:
        return f.read()

@app.get("/models")
async def list_models():
    """List available Bedrock models"""
    try:
        bedrock = boto3.client(
            service_name="bedrock",
            region_name="us-west-2"
        )
        response = bedrock.list_foundation_models()

        # Filter for active models that support on-demand
        models = []
        for model in response.get('modelSummaries', []):
            if model.get('modelLifecycle', {}).get('status') == 'ACTIVE':
                models.append({
                    'id': model['modelId'],
                    'name': model['modelName'],
                    'provider': model['providerName']
                })

        return {"models": models}
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    """Handle chat requests to AWS Bedrock with MCP tool support"""
    try:
        # Convert messages to Claude format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # Prepare the request body based on model family
        if "anthropic.claude" in request.model:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "messages": messages,
            }

            # Add MCP tools to Claude request
            if mcp_tools:
                body["tools"] = mcp_tools

            # Tool use loop for Claude
            response_text = await handle_claude_with_tools(request.model, body, messages)
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
                }
            }
        else:
            # Default to Claude format
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "messages": messages
            }

        if request.stream:
            return StreamingResponse(
                stream_bedrock_response(request.model, body),
                media_type="text/event-stream"
            )
        else:
            # Invoke the model
            response = bedrock_runtime.invoke_model(
                modelId=request.model,
                body=json.dumps(body)
            )

            # Parse response
            response_body = json.loads(response['body'].read())

            # Extract text based on model family
            if "anthropic.claude" in request.model:
                response_text = response_body['content'][0]['text']
            elif "meta.llama" in request.model:
                response_text = response_body['generation']
            elif "amazon.titan" in request.model:
                response_text = response_body['results'][0]['outputText']
            else:
                response_text = str(response_body)

            return ChatResponse(response=response_text, model=request.model)

    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"AWS Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

async def stream_bedrock_response(model_id: str, body: dict):
    """Stream responses from Bedrock"""
    try:
        response = bedrock_runtime.invoke_model_with_response_stream(
            modelId=model_id,
            body=json.dumps(body)
        )

        for event in response['body']:
            chunk = event.get('chunk')
            if chunk:
                chunk_data = json.loads(chunk['bytes'])

                # Extract text based on model
                if "anthropic.claude" in model_id:
                    if chunk_data.get('type') == 'content_block_delta':
                        text = chunk_data.get('delta', {}).get('text', '')
                        if text:
                            yield f"data: {json.dumps({'text': text})}\n\n"
                    elif chunk_data.get('type') == 'message_stop':
                        yield f"data: {json.dumps({'done': True})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

# Mount static files (will create this next)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
