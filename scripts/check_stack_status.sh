#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           CDK Stack Status & Dependencies                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

STACK_NAME="GenerativeAiStack"
REGION="${AWS_DEFAULT_REGION:-eu-west-1}"

echo "Stack: $STACK_NAME"
echo "Region: $REGION"
echo ""

# Check if stack exists
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. STACK STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null)

if [ -z "$STACK_STATUS" ]; then
    echo "❌ Stack not found: $STACK_NAME"
    exit 1
fi

echo "Status: $STACK_STATUS"

# Get stack creation/update time
LAST_UPDATED=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].LastUpdatedTime' \
    --output text 2>/dev/null)

if [ "$LAST_UPDATED" != "None" ]; then
    echo "Last Updated: $LAST_UPDATED"
else
    CREATED=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].CreationTime' \
        --output text)
    echo "Created: $CREATED"
fi

echo ""

# Get stack outputs
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. STACK OUTPUTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[].[OutputKey,OutputValue]' \
    --output table

echo ""

# Get all resources
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. STACK RESOURCES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

aws cloudformation describe-stack-resources \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'StackResources[].[LogicalResourceId,ResourceType,ResourceStatus]' \
    --output table

echo ""

# Get resource details with dependencies
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. RESOURCE DEPENDENCIES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get template to analyze dependencies
TEMPLATE=$(aws cloudformation get-template \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'TemplateBody' \
    --output text)

echo ""
echo "Key Resource Dependencies:"
echo ""

# OpenSearch Collection dependencies
echo "📊 OpenSearch Serverless Collection:"
echo "   Depends on:"
echo "   ├── KBEncryptionPolicy (encryption)"
echo "   ├── KBNetworkPolicy (network access)"
echo "   └── KBDataAccessPolicy (data access)"
echo ""

# Knowledge Base dependencies
echo "📚 Bedrock Knowledge Base:"
echo "   Depends on:"
echo "   ├── BedrockKBRole (IAM role)"
echo "   ├── KBCollection (OpenSearch collection)"
echo "   ├── KnowledgeBaseDataBucket (S3 bucket)"
echo "   └── Vector index (manual creation required)"
echo ""

# Data Source dependencies
echo "📁 Knowledge Base Data Source:"
echo "   Depends on:"
echo "   ├── InsurancePolicyKB (Knowledge Base)"
echo "   └── KnowledgeBaseDataBucket (S3 bucket)"
echo ""

# Lambda dependencies
echo "⚡ Lambda Function:"
echo "   Depends on:"
echo "   ├── InputDocumentBucket (S3 trigger)"
echo "   ├── OutputSummaryBucket (write access)"
echo "   ├── FeedbackBucket (read/write access)"
echo "   ├── KnowledgeBaseDataBucket (read access)"
echo "   └── InsurancePolicyKB (Knowledge Base ID)"
echo ""

# Check specific resource statuses
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. CRITICAL RESOURCES STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get Knowledge Base ID
KB_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' \
    --output text 2>/dev/null)

if [ -n "$KB_ID" ]; then
    echo "✅ Knowledge Base: $KB_ID"
    
    # Check KB status
    KB_STATUS=$(aws bedrock-agent get-knowledge-base \
        --knowledge-base-id "$KB_ID" \
        --region "$REGION" \
        --query 'knowledgeBase.status' \
        --output text 2>/dev/null)
    echo "   Status: $KB_STATUS"
else
    echo "❌ Knowledge Base: Not found"
fi

echo ""

# Get OpenSearch Collection
COLLECTION_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`OpenSearchCollectionArn`].OutputValue' \
    --output text 2>/dev/null)

if [ -n "$COLLECTION_ARN" ]; then
    COLLECTION_ID=$(echo "$COLLECTION_ARN" | awk -F'/' '{print $NF}')
    echo "✅ OpenSearch Collection: $COLLECTION_ID"
    
    # Check collection status
    COLLECTION_STATUS=$(aws opensearchserverless batch-get-collection \
        --ids "$COLLECTION_ID" \
        --region "$REGION" \
        --query 'collectionDetails[0].status' \
        --output text 2>/dev/null)
    echo "   Status: $COLLECTION_STATUS"
else
    echo "❌ OpenSearch Collection: Not found"
fi

echo ""

# Get Lambda Function
LAMBDA_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' \
    --output text 2>/dev/null)

if [ -n "$LAMBDA_NAME" ]; then
    echo "✅ Lambda Function: $LAMBDA_NAME"
    
    # Check Lambda status
    LAMBDA_STATE=$(aws lambda get-function \
        --function-name "$LAMBDA_NAME" \
        --region "$REGION" \
        --query 'Configuration.State' \
        --output text 2>/dev/null)
    echo "   State: $LAMBDA_STATE"
else
    echo "❌ Lambda Function: Not found"
fi

echo ""

# Check S3 buckets
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. S3 BUCKETS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for bucket_key in "InputBucketName" "OutputBucketName" "FeedbackBucketName" "KBDataBucketName"; do
    BUCKET=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query "Stacks[0].Outputs[?OutputKey==\`$bucket_key\`].OutputValue" \
        --output text 2>/dev/null)
    
    if [ -n "$BUCKET" ]; then
        OBJECT_COUNT=$(aws s3 ls "s3://$BUCKET" --recursive 2>/dev/null | wc -l)
        echo "✅ $bucket_key: $BUCKET ($OBJECT_COUNT objects)"
    fi
done

echo ""

# Check for any failed resources
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. FAILED RESOURCES (if any)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

FAILED=$(aws cloudformation describe-stack-resources \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'StackResources[?contains(ResourceStatus, `FAILED`)].[LogicalResourceId,ResourceStatus,ResourceStatusReason]' \
    --output table 2>/dev/null)

if [ -z "$FAILED" ] || [ "$FAILED" == "None" ]; then
    echo "✅ No failed resources"
else
    echo "$FAILED"
fi

echo ""

# Check stack events (last 10)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8. RECENT STACK EVENTS (Last 10)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

aws cloudformation describe-stack-events \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --max-items 10 \
    --query 'StackEvents[].[Timestamp,LogicalResourceId,ResourceStatus,ResourceStatusReason]' \
    --output table

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Status Check Complete                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
