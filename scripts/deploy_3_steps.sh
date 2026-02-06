#!/bin/bash

# 3-Step Deployment Script
# Reliable manual approach - no Docker, no timing issues

set -e

REGION="eu-west-1"

echo "=========================================="
echo "Insurance Claims System - 3-Step Deploy"
echo "=========================================="
echo ""
echo "This script will guide you through the 3-step deployment:"
echo "  Step 1: Deploy infrastructure (8-10 min)"
echo "  Step 2: Create OpenSearch index (10 sec)"
echo "  Step 3: Deploy Knowledge Base (2 min)"
echo ""
echo "Total time: ~12-15 minutes"
echo ""

# Check AWS CLI
if ! aws sts get-caller-identity --region $REGION > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured for region $REGION"
    exit 1
fi

echo "✓ AWS CLI configured"
echo ""

# ============================================================
# STEP 1: Deploy Infrastructure
# ============================================================

echo "=========================================="
echo "STEP 1: Deploy Infrastructure"
echo "=========================================="
echo ""
echo "This will create:"
echo "  - OpenSearch Serverless collection (~5-8 min)"
echo "  - IAM roles"
echo "  - S3 buckets"
echo "  - Security policies"
echo "  - Lambda processor"
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read

echo "Deploying infrastructure..."
cdk deploy --require-approval never

echo ""
echo "✓ Step 1 complete!"
echo ""

# ============================================================
# STEP 2: Create OpenSearch Index
# ============================================================

echo "=========================================="
echo "STEP 2: Create OpenSearch Index"
echo "=========================================="
echo ""
echo "Waiting 30 seconds for collection to be fully active..."
sleep 30

echo ""
echo "Creating index..."
python3 create_opensearch_index.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Index creation failed. The collection might not be ready yet."
    echo ""
    echo "Wait 2-3 minutes and run manually:"
    echo "  python3 create_opensearch_index.py"
    echo ""
    echo "Then continue with Step 3:"
    echo "  1. Uncomment Knowledge Base in generative_ai/generative_ai_stack.py"
    echo "  2. Run: cdk deploy"
    exit 1
fi

echo ""
echo "✓ Step 2 complete!"
echo ""

# ============================================================
# STEP 3: Deploy Knowledge Base
# ============================================================

echo "=========================================="
echo "STEP 3: Deploy Knowledge Base"
echo "=========================================="
echo ""
echo "⚠️  MANUAL STEP REQUIRED:"
echo ""
echo "1. Open: generative_ai/generative_ai_stack.py"
echo "2. Find the comment: '# STEP 3: Uncomment below and redeploy'"
echo "3. Uncomment the Knowledge Base and Data Source code"
echo "4. Save the file"
echo ""
echo "Press Enter when you've uncommented the code..."
read

echo "Deploying Knowledge Base..."
cdk deploy --require-approval never

echo ""
echo "✓ Step 3 complete!"
echo ""

# ============================================================
# DONE
# ============================================================

echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""

# Get outputs
echo "Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region $REGION \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo ""
echo "Next Steps:"
echo ""
echo "1. Set up Knowledge Base:"
echo "   ./setup_knowledge_base.sh"
echo ""
echo "2. Test with sample claim:"
echo "   INPUT_BUCKET=\$(aws cloudformation describe-stacks --stack-name GenerativeAiStack --region $REGION --query 'Stacks[0].Outputs[?OutputKey==\`InputBucketName\`].OutputValue' --output text)"
echo "   aws s3 cp sample_claims/claim_auto_accident.txt s3://\${INPUT_BUCKET}/"
echo ""
echo "3. Check results:"
echo "   OUTPUT_BUCKET=\$(aws cloudformation describe-stacks --stack-name GenerativeAiStack --region $REGION --query 'Stacks[0].Outputs[?OutputKey==\`OutputBucketName\`].OutputValue' --output text)"
echo "   aws s3 ls s3://\${OUTPUT_BUCKET}/"
echo ""
echo "To clean up when done:"
echo "   cdk destroy --region $REGION"
echo ""
echo "=========================================="
