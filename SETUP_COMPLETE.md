# 🎉 MCP Weather Server - Ready to Use!

## ✅ What's Fixed

The web application now defaults to **Claude 3.5 Sonnet v2** instead of Titan, which enables MCP tool support.

### Previous Issue
- HTML dropdown defaulted to `amazon.titan-text-premier-v1:0` (selected)
- Claude models were disabled in the dropdown
- When you clicked send, it was trying to use Titan format with an invalid model ID

### Solution
- Updated default model to `anthropic.claude-3-5-sonnet-20241022-v2:0`
- Removed "disabled" status from Claude models
- Reordered dropdown to show MCP-enabled models first

## 🚀 Quick Start

### 1. Export AWS Credentials (if not already done)
```bash
export AWS_ACCESS_KEY_ID='your-access-key-id'
export AWS_SECRET_ACCESS_KEY='your-secret-access-key'
export AWS_DEFAULT_REGION='us-west-2'
```

### 2. Start the Web App
```bash
cd web_app
python app.py
```

### 3. Open Browser
Visit: **http://localhost:8000**

### 4. Test MCP Weather Tools
Try these queries in the chat:

```
What are the current weather alerts in California?

Get weather forecast for Seattle (latitude: 47.6062, longitude: -122.3321)

Are there any weather alerts in Texas?

What's the forecast for Miami? (latitude: 25.7617, longitude: -80.1918)
```

## 📊 Available Models

### MCP-Enabled (Can use weather tools)
- ✅ **Claude 3.5 Sonnet v2** - Best performance (default)
- ✅ **Claude 3.5 Sonnet v1** - Slightly older
- ✅ **Claude 3 Haiku** - Fastest, cheapest
- ✅ **Claude 3 Sonnet** - Good balance

### No MCP Support (Basic chat only)
- ⚠️ **Amazon Titan** - No tool calling support
- ⚠️ **Llama 3.2** - No tool calling support

## 🔧 How It Works

1. **User sends message** → Web UI
2. **Message sent to Claude** → AWS Bedrock API with MCP tools defined
3. **Claude decides to use tools** → Calls `get_alerts()` or `get_forecast()`
4. **MCP Server executes** → National Weather Service API
5. **Results returned to Claude** → Claude formats response
6. **User sees formatted answer** → Web UI

## 📁 Project Structure

```
mcp-server/
├── src/mcp_weather_server/     # Modular MCP server
│   ├── api_client.py            # NWS API client
│   ├── tools.py                 # Weather tools logic
│   └── server.py                # MCP server & entry point
├── tests/                       # Comprehensive test suite
│   ├── test_api_client.py
│   └── test_tools.py
├── web_app/                     # Optional testing interface
│   ├── app.py                   # FastAPI + Bedrock integration
│   └── static/index.html        # Chat UI
└── pyproject.toml               # Package config
```

## 🎯 Key Commands

```bash
# Run MCP server standalone
mcp-weather-server

# Run web app
cd web_app && python app.py

# Run tests
pytest

# Test a specific Bedrock model
python test_bedrock_model.py

# Check available Bedrock models
python check_models.py
```

## 💡 Tips

1. **Use Claude models** for MCP tool support - only Anthropic models support tool calling
2. **Haiku is cheaper** - Use Claude 3 Haiku for development/testing to save costs
3. **Web app is optional** - The MCP server can run standalone and connect to Claude Desktop
4. **Check logs** - If errors occur, check `/tmp/bedrock_app.log`

## 🐛 Troubleshooting

### "Invalid model identifier"
- Make sure you're using a Claude model (starts with `anthropic.`)
- Check the dropdown is set to Claude, not Titan

### "Access Denied"
- Export your AWS credentials (see step 1 above)
- Verify you have Bedrock access in AWS console

### "Tool not found"
- Make sure MCP server started successfully (check terminal logs)
- Verify tools are listed: should see `['get_alerts', 'get_forecast']` on startup

### Port 8000 in use
```bash
lsof -ti:8000 | xargs kill -9
```

## 🎊 Success!

Your MCP Weather Server is production-ready and can:
- ✅ Provide real-time weather alerts
- ✅ Get forecasts for any US location
- ✅ Integrate with Claude via MCP protocol
- ✅ Be deployed as a standalone service
- ✅ Connect to multiple applications

Enjoy your weather-powered AI assistant! 🌤️
