# Examples

Example scripts for working with the MCP Server.

## Running the Examples

All examples require AWS credentials to be set:

```bash
export AWS_ACCESS_KEY_ID='your-key'
export AWS_SECRET_ACCESS_KEY='your-secret'
export AWS_REGION='us-east-1'
```

## Scripts

### `check_models.py`
List all available AWS Bedrock models in your account.

```bash
python examples/check_models.py
```

Shows which Claude models are available for MCP tool support.

### `test_bedrock_model.py`
Test specific Claude model identifiers to verify they work.

```bash
python examples/test_bedrock_model.py
```

Tests common Claude model IDs and reports which ones are accessible.

### `test_claude_models_mcp.py`
Test MCP tool integration with Claude models.

```bash
python examples/test_claude_models_mcp.py
```

Verifies that Claude models can use MCP tools correctly.

## Supported AWS Regions

- `us-east-1` - US East (N. Virginia) - Recommended
- `us-west-2` - US West (Oregon)
- `eu-central-1` - Europe (Frankfurt)
- `ap-northeast-1` - Asia Pacific (Tokyo)

**Note:** Claude model availability varies by region. `us-east-1` typically has the most models.
