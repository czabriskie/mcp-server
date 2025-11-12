#!/usr/bin/env python3
"""Test script to find the correct Claude model identifier."""

import json
import os
import boto3
from botocore.exceptions import ClientError

# Common Claude model IDs to try (in order of likelihood)
MODELS_TO_TRY = [
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
]

def test_model(bedrock_runtime, model_id):
    """Test if a model ID works."""
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello! Just testing."
                }
            ]
        })

        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=body
        )

        # If we get here, the model works!
        return True, "Success"

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        return False, f"{error_code}: {error_msg}"
    except Exception as e:
        return False, str(e)


def main():
    # Get region from environment or default to us-east-1
    region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))

    print("=" * 80)
    print("TESTING CLAUDE MODEL IDENTIFIERS")
    print("=" * 80)
    print()

    try:
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=region
        )
        print(f"✅ Connected to AWS Bedrock in {region}")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to AWS Bedrock: {e}")
        print()
        print("Make sure you've exported your AWS credentials:")
        print("  export AWS_ACCESS_KEY_ID='your-key'")
        print("  export AWS_SECRET_ACCESS_KEY='your-secret'")
        print("  export AWS_REGION='us-east-1'  # or your preferred region")
        return

    print("Testing model identifiers...\n")

    working_models = []

    for model_id in MODELS_TO_TRY:
        print(f"Testing: {model_id}")
        success, message = test_model(bedrock_runtime, model_id)

        if success:
            print(f"  ✅ WORKS!")
            working_models.append(model_id)
        else:
            print(f"  ❌ {message}")
        print()

    print("=" * 80)
    print("RESULTS")
    print("=" * 80)

    if working_models:
        print(f"\n✅ Found {len(working_models)} working model(s):\n")
        for model in working_models:
            print(f"  • {model}")

        print("\n📝 Update web_app/app.py with this model:")
        print(f'\n  model: str = "{working_models[0]}"')
        print()
    else:
        print("\n❌ No working models found!")
        print()
        print("This usually means:")
        print("  1. You haven't requested access to Claude models in Bedrock console")
        print("  2. Your use case form hasn't been approved yet")
        print(f"  3. Claude models aren't available in {region} (try us-east-1 or us-west-2)")
        print()
        print("To request access:")
        print("  1. Go to https://console.aws.amazon.com/bedrock/")
        print("  2. Click 'Model access' in left sidebar")
        print("  3. Click 'Modify model access'")
        print("  4. Select Anthropic Claude models")
        print("  5. Fill out the use case form")
        print("  6. Wait ~15 minutes for approval")
        print()


if __name__ == "__main__":
    main()
