#!/bin/bash
set -e

echo "=========================================="
echo "Fix Dimension Mismatch and Redeploy"
echo "=========================================="
echo ""

# Set region
export AWS_DEFAULT_REGION=eu-west-1

echo "Step 1: Delete existing Knowledge Base..."
echo "------------------------------------------"
KB_ID="C3C0JSHBYV"
echo "Deleting Knowledge Base: $KB_ID"
aws bedrock-agent delete-knowledge-base \
    --knowledge-base-id "$KB_ID" \
    --region eu-west-1 || echo "KB already deleted or doesn't exist"

echo ""
echo "Waiting 10 seconds for KB deletion to propagate..."
sleep 10

echo ""
echo "Step 2: Delete and recreate OpenSearch index..."
echo "------------------------------------------"
python3 delete_and_recreate_index.py

echo ""
echo "Step 3: Deploy updated CDK stack..."
echo "------------------------------------------"
cdk deploy --require-approval never

echo ""
echo "Step 4: Get new Knowledge Base ID..."
echo "------------------------------------------"
NEW_KB_ID=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region eu-west-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' \
    --output text)

echo "New Knowledge Base ID: $NEW_KB_ID"

echo ""
echo "Step 5: Upload policy documents..."
echo "------------------------------------------"
KB_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region eu-west-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`KBDataBucketName`].OutputValue' \
    --output text)

echo "Uploading to bucket: $KB_BUCKET"
aws s3 cp knowledge_base_docs/ "s3://$KB_BUCKET/policies/" --recursive

echo ""
echo "Step 6: Start ingestion job..."
echo "------------------------------------------"
DATA_SOURCE_ID=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region eu-west-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`DataSourceId`].OutputValue' \
    --output text)

echo "Starting ingestion for Data Source: $DATA_SOURCE_ID"
INGESTION_JOB_ID=$(aws bedrock-agent start-ingestion-job \
    --knowledge-base-id "$NEW_KB_ID" \
    --data-source-id "$DATA_SOURCE_ID" \
    --region eu-west-1 \
    --query 'ingestionJob.ingestionJobId' \
    --output text)

echo "Ingestion Job ID: $INGESTION_JOB_ID"

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Knowledge Base ID: $NEW_KB_ID"
echo "Data Source ID: $DATA_SOURCE_ID"
echo "Ingestion Job ID: $INGESTION_JOB_ID"
echo ""
echo "Monitor ingestion status:"
echo "  aws bedrock-agent get-ingestion-job \\"
echo "    --knowledge-base-id $NEW_KB_ID \\"
echo "    --data-source-id $DATA_SOURCE_ID \\"
echo "    --ingestion-job-id $INGESTION_JOB_ID \\"
echo "    --region eu-west-1"
echo ""
