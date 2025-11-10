#!/usr/bin/env python3
"""Quick script to check which Bedrock models you have access to."""

import boto3
from botocore.exceptions import ClientError

def check_bedrock_models():
    """List all available Bedrock models in your account."""
    try:
        bedrock = boto3.client(
            service_name="bedrock",
            region_name="us-west-2"
        )

        response = bedrock.list_foundation_models()

        print("=" * 80)
        print("AVAILABLE BEDROCK MODELS IN us-west-2")
        print("=" * 80)

        # Group by provider
        providers = {}
        for model in response.get('modelSummaries', []):
            provider = model.get('providerName', 'Unknown')
            if provider not in providers:
                providers[provider] = []
            providers[provider].append(model)

        # Print Claude models first (needed for MCP)
        if 'Anthropic' in providers:
            print("\n🎯 ANTHROPIC (Required for MCP Tools):")
            print("-" * 80)
            for model in providers['Anthropic']:
                model_id = model.get('modelId', 'Unknown')
                model_name = model.get('modelName', 'Unknown')
                status = model.get('modelLifecycle', {}).get('status', 'Unknown')

                # Check if this is Claude 3.5
                if 'claude-3-5' in model_id.lower() or 'claude-3.5' in model_name.lower():
                    print(f"  ✅ {model_name}")
                    print(f"     ID: {model_id}")
                    print(f"     Status: {status}")
                    print()
        else:
            print("\n❌ NO ANTHROPIC MODELS AVAILABLE")
            print("   You need to request access to Claude models in the Bedrock console!")
            print("   Go to: https://console.aws.amazon.com/bedrock/")
            print()

        # Print other providers
        for provider, models in sorted(providers.items()):
            if provider == 'Anthropic':
                continue  # Already printed

            print(f"\n{provider}:")
            print("-" * 80)
            for model in models[:3]:  # Limit to 3 per provider
                model_id = model.get('modelId', 'Unknown')
                model_name = model.get('modelName', 'Unknown')
                status = model.get('modelLifecycle', {}).get('status', 'Unknown')
                print(f"  • {model_name}")
                print(f"    ID: {model_id}")
                print(f"    Status: {status}")

            if len(models) > 3:
                print(f"  ... and {len(models) - 3} more")
            print()

        print("=" * 80)
        print("\n✨ To use MCP weather tools, use one of the Claude models above!")
        print("   Current default: anthropic.claude-3-5-sonnet-20241022-v2:0")
        print()

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDeniedException':
            print("❌ ACCESS DENIED")
            print("   Your AWS credentials don't have permission to list Bedrock models.")
            print("   Make sure your IAM user/role has 'bedrock:ListFoundationModels' permission.")
        else:
            print(f"❌ ERROR: {e}")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")

if __name__ == "__main__":
    check_bedrock_models()
