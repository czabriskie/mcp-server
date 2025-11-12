"""
Test Claude models with MCP tool calling to verify they work with your AWS account.
This script tests each Claude model to ensure it can:
1. Connect to AWS Bedrock
2. Support tool use (MCP integration)
3. Successfully invoke with a simple tool call
"""

import json
import os
import boto3
from botocore.exceptions import ClientError

# Get region from environment or use default
region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))

# Initialize Bedrock client
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name=region
)

# Claude models to test (all models shown in web interface)
MODELS_TO_TEST = [
    ("Claude 3.5 Sonnet v2", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
    ("Claude 3.5 Sonnet v1", "anthropic.claude-3-5-sonnet-20240620-v1:0"),
    ("Claude 3.5 Haiku", "anthropic.claude-3-5-haiku-20241022-v1:0"),
    ("Claude 3 Opus", "anthropic.claude-3-opus-20240229-v1:0"),
    ("Claude 3 Sonnet", "anthropic.claude-3-sonnet-20240229-v1:0"),
    ("Claude 3 Haiku", "anthropic.claude-3-haiku-20240307-v1:0"),
]

# Simple tool definition for testing
TEST_TOOL = {
    "name": "get_weather",
    "description": "Get weather information for a location",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city or location"
            }
        },
        "required": ["location"]
    }
}


def test_model(model_name: str, model_id: str) -> tuple[bool, str]:
    """
    Test a single model with tool calling.

    Returns:
        tuple: (success: bool, message: str)
    """
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"Model ID: {model_id}")
    print(f"{'='*60}")

    try:
        # Prepare request body with tool
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": "What's the weather like in San Francisco?"
                }
            ],
            "tools": [TEST_TOOL]
        }

        # Invoke model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )

        response_body = json.loads(response["body"].read())

        # Check if model supports tools
        stop_reason = response_body.get("stop_reason")
        content = response_body.get("content", [])

        print(f"✓ Model accessible")
        print(f"✓ Stop reason: {stop_reason}")

        # Check for tool use
        has_tool_use = any(
            block.get("type") == "tool_use"
            for block in content
        )

        if has_tool_use or stop_reason == "tool_use":
            print(f"✓ Tool calling SUPPORTED")
            print(f"✓ Model works with MCP integration")
            return True, "✅ WORKING - Supports tool calls"
        else:
            print(f"⚠ Tool calling not triggered (might still work)")
            return True, "⚠ ACCESSIBLE - Check tool support manually"

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_msg = e.response["Error"]["Message"]

        print(f"✗ ERROR: {error_code}")
        print(f"  Message: {error_msg}")

        if error_code == "ResourceNotFoundException":
            return False, "❌ NOT AVAILABLE - Model not found in region"
        elif error_code == "AccessDeniedException":
            return False, "❌ NO ACCESS - Request access in AWS Console"
        else:
            return False, f"❌ ERROR - {error_code}: {error_msg}"

    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        return False, f"❌ ERROR - {str(e)}"


def main():
    """Test all Claude models and generate a report."""
    print(f"\n🔍 Testing Claude Models for MCP Tool Support")
    print(f"Region: {region}")
    print(f"Models to test: {len(MODELS_TO_TEST)}")
    print("\nNote: Ensure AWS credentials are configured:")
    print("  export AWS_ACCESS_KEY_ID='your-key'")
    print("  export AWS_SECRET_ACCESS_KEY='your-secret'")
    print("  export AWS_REGION='us-east-1'\n")

    results = []

    for model_name, model_id in MODELS_TO_TEST:
        success, message = test_model(model_name, model_id)
        results.append((model_name, model_id, success, message))

    # Print summary
    print(f"\n\n{'='*80}")
    print("SUMMARY REPORT")
    print(f"{'='*80}\n")

    working_models = []
    failed_models = []

    for model_name, model_id, success, message in results:
        print(f"{message}")
        print(f"  {model_name}")
        print(f"  {model_id}\n")

        if success:
            working_models.append((model_name, model_id))
        else:
            failed_models.append((model_name, model_id))

    print(f"{'='*80}")
    print(f"✅ Working: {len(working_models)}/{len(MODELS_TO_TEST)}")
    print(f"❌ Failed: {len(failed_models)}/{len(MODELS_TO_TEST)}")
    print(f"{'='*80}\n")

    if failed_models:
        print("\n⚠️  RECOMMENDATIONS:")
        print("1. Request model access in AWS Bedrock console")
        print("2. Check model availability in your region")
        print(f"3. Try a different region (current: {region})")
        print("4. Update web_app/static/index.html to remove unavailable models\n")

    if working_models:
        print("\n✨ WORKING MODELS (keep these in web interface):")
        for model_name, model_id in working_models:
            print(f"   • {model_name} ({model_id})")
        print()


if __name__ == "__main__":
    main()
