#!/bin/bash

# Get stack outputs
KB_ID=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region eu-west-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' \
    --output text)

DATA_SOURCE_ID=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region eu-west-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`DataSourceId`].OutputValue' \
    --output text)

echo "Knowledge Base ID: $KB_ID"
echo "Data Source ID: $DATA_SOURCE_ID"
echo ""
echo "Fetching latest ingestion job..."
echo ""

# Get the latest ingestion job
aws bedrock-agent list-ingestion-jobs \
    --knowledge-base-id "$KB_ID" \
    --data-source-id "$DATA_SOURCE_ID" \
    --region eu-west-1 \
    --max-results 1 \
    --query 'ingestionJobSummaries[0]' \
    --output json

echo ""
echo "To get detailed status of a specific job, use:"
echo "  aws bedrock-agent get-ingestion-job \\"
echo "    --knowledge-base-id $KB_ID \\"
echo "    --data-source-id $DATA_SOURCE_ID \\"
echo "    --ingestion-job-id <JOB_ID> \\"
echo "    --region eu-west-1"
