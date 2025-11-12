# AWS Bedrock Setup Guide

Follow these steps to set up AWS Bedrock for your chat application.

## Prerequisites
- An AWS Account
- AWS CLI installed and configured (optional but recommended)
- Valid payment method added to your AWS account

## Step 1: Access AWS Console

1. Go to https://console.aws.amazon.com/
2. Sign in with your AWS account credentials
3. Make sure you're in a region that supports AWS Bedrock (recommended regions):
   - **US East (N. Virginia)** - `us-east-1`
   - **US West (Oregon)** - `us-west-2`
   - **Europe (Frankfurt)** - `eu-central-1`
   - **Asia Pacific (Tokyo)** - `ap-northeast-1`

## Step 2: Navigate to AWS Bedrock

1. In the AWS Console search bar at the top, type "Bedrock"
2. Click on **Amazon Bedrock** from the results
3. You'll be taken to the Bedrock console

## Step 3: Verify Model Access

**🎯 IMPORTANT: You MUST use Claude models to use MCP weather tools!**

Only Anthropic Claude models support the tool calling needed for MCP integration. This means you need to fill out the use case form.

### Required Steps for MCP Tool Support:

1. In the Bedrock console, click **Model access** (left sidebar)
2. Click **Modify model access** or **Request model access**
3. Select **Anthropic** models, specifically:
   - ✅ **Claude 3.5 Sonnet** (Recommended - best performance)
   - ✅ **Claude 3.5 Haiku** (Faster, cheaper alternative)
   - ✅ **Claude 3 Opus** (Most capable but slowest)

4. You'll be prompted to fill out a **Use Case form**
5. Fill it out honestly (e.g., "Weather information assistant using MCP tools")
6. Submit and wait ~15 minutes for approval
7. Once approved, you'll see "Access granted" status

**Current default model in app**: `anthropic.claude-3-5-sonnet-20241022-v2:0`

### ⚠️ IMPORTANT: Anthropic Claude Models Require Use Case Form

**Claude models (Anthropic) require filling out a use case form** before you can use them:
- When you try to use Claude models, you'll get an error asking you to fill out the form
- The form is available in the Bedrock console under Model access
- After submitting, it may take 15 minutes to be approved

### Alternative Models (Without Use Case Form - For Testing Only):

**⚠️ These models do NOT support MCP tools** but can be used for basic chat testing:

#### Amazon Nova Models (Recommended to Start - November 2024+)
- ✅ **Nova Micro** (`us.amazon.nova-micro-v1:0`) - Fastest, most cost-effective
- ✅ **Nova Lite** (`us.amazon.nova-lite-v1:0`) - Balanced performance
- ✅ **Nova Pro** (`us.amazon.nova-pro-v1:0`) - Most capable Nova model

#### Amazon Titan Models (Legacy)
- ✅ **Titan Text Premier** - Best Titan model, no form required
- ✅ **Titan Text Express** - Fast and capable
- ✅ **Titan Text Lite** - Lightweight option

**Note**: Nova and Titan models do NOT support tool use (MCP integration), but work great for general chat.

#### Meta Llama Models (No form required)
- ✅ **Llama 3.2 90B Instruct**
- ✅ **Llama 3.2 11B Instruct**
- ✅ **Llama 3.2 3B Instruct**
- ✅ **Llama 3.2 1B Instruct**

**Note**: Llama models do NOT support tool use (MCP integration) in this implementation.

If you don't see access granted for certain models, you can request access by clicking **Modify model access** and selecting the models you need.

## Step 4: Set Up IAM Credentials

### Option A: Using AWS CLI (Recommended for Development)

1. Install AWS CLI if you haven't:
   ```bash
   # macOS
   brew install awscli

   # Or download from https://aws.amazon.com/cli/
   ```

2. Configure AWS CLI:
   ```bash
   aws configure
   ```

3. Enter your credentials when prompted:
   - **AWS Access Key ID**: [Your access key]
   - **AWS Secret Access Key**: [Your secret key]
   - **Default region name**: `us-east-1` (or your preferred region like us-west-2, eu-central-1)
   - **Default output format**: `json`

### Option B: Create IAM User with Bedrock Access

1. Go to **IAM** in the AWS Console
2. Click **Users** → **Add users**
3. Enter a username (e.g., "bedrock-app-user")
4. Select **Access key - Programmatic access**
5. Click **Next: Permissions**
6. Choose **Attach existing policies directly**
7. Search for and select: **AmazonBedrockFullAccess**
8. Click **Next** through the remaining steps
9. Click **Create user**
10. **IMPORTANT**: Save your Access Key ID and Secret Access Key in a secure location
    - You won't be able to see the secret key again!

11. Configure your credentials:
   - **Option 1**: Use AWS CLI `aws configure`
   - **Option 2**: Set environment variables:
     ```bash
     export AWS_ACCESS_KEY_ID="your-access-key"
     export AWS_SECRET_ACCESS_KEY="your-secret-key"
     export AWS_REGION="us-east-1"  # or us-west-2, eu-central-1, etc.
     ```
   - **Option 3**: Create `~/.aws/credentials` file:
     ```ini
     [default]
     aws_access_key_id = your-access-key
     aws_secret_access_key = your-secret-key
     region = us-east-1
     ```

## Step 5: Verify Setup (Optional)

You can verify your AWS credentials are working:

```bash
# Check your AWS identity
aws sts get-caller-identity

# This will show your AWS account ID and user ARN
```

Note: The AWS CLI may not have the `bedrock` commands available depending on your CLI version. This is normal - the Python `boto3` library (which the app uses) has full Bedrock support.

## Step 6: Install Python Dependencies

In your project directory:

```bash
# Install all dependencies
pip install -e .

# Or install individually
pip install fastapi uvicorn boto3 httpx
```

## Step 7: Configure AWS Region

The application reads the AWS region from environment variables with the following priority:
1. `AWS_REGION` environment variable
2. `AWS_DEFAULT_REGION` environment variable
3. Falls back to `us-east-1` if neither is set

Set your preferred region:

```bash
export AWS_REGION='us-east-1'  # or us-west-2, eu-central-1, ap-northeast-1, etc.
```

**Note:** Model availability varies by region. `us-east-1` typically has the most comprehensive Claude model selection.

## Step 8: Run the Application

```bash
# Start the web server
python app.py

# Or use uvicorn directly
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Then open your browser to: http://localhost:8000

## Troubleshooting

### "AccessDeniedException" Error
- Make sure you've requested and received access to the model
- Verify your IAM user has the `AmazonBedrockFullAccess` policy
- Check that you're using the correct region

### "ValidationException: The provided model identifier is invalid"
- Verify the model ID is correct in the dropdown
- Check that the model is available in your selected region
- Some models may only be available in specific regions

### "ResourceNotFoundException"
- The model might not be available in your current region
- Try switching regions: `export AWS_REGION='us-east-1'` or `export AWS_REGION='us-west-2'`
- Check available models in your region: `python examples/check_models.py`

### "ThrottlingException"
- You're making too many requests
- Bedrock has rate limits based on your account tier
- Wait a moment and try again

### Authentication Issues
- Verify AWS credentials are properly configured
- Run `aws sts get-caller-identity` to check your credentials
- Make sure environment variables or ~/.aws/credentials are set correctly

## Cost Considerations

AWS Bedrock charges based on:
- **Input tokens**: Text you send to the model
- **Output tokens**: Text the model generates

Approximate pricing (as of November 2024):
- **Claude 3.5 Sonnet**: ~$3 per million input tokens, ~$15 per million output tokens
- **Claude 3 Haiku**: ~$0.25 per million input tokens, ~$1.25 per million output tokens
- **Llama models**: Generally cheaper, varies by size

💡 **Tip**: Start with Claude 3 Haiku for testing - it's fast and cost-effective!

## Security Best Practices

1. ✅ Never commit AWS credentials to version control
2. ✅ Use IAM roles when running in production (EC2, ECS, Lambda)
3. ✅ Rotate access keys regularly
4. ✅ Use least-privilege IAM policies
5. ✅ Enable CloudTrail logging for audit trails
6. ✅ Set up billing alerts in AWS Billing console

## Next Steps

- Explore different models to find the best fit for your use case
- Implement streaming responses for better UX
- Add conversation history persistence
- Integrate your MCP weather server tools
- Set up proper error handling and logging

## Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Bedrock API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/)
- [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)
