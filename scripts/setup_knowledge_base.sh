#!/bin/bash

# Post-deployment setup script for Knowledge Base

set -e

REGION="eu-west-1"

echo "========================================="
echo "Knowledge Base Setup"
echo "========================================="
echo ""

# Get stack outputs
echo "Fetching stack outputs..."
KB_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`KBDataBucketName`].OutputValue' \
    --output text)

KB_ID=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' \
    --output text)

DS_ID=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`DataSourceId`].OutputValue' \
    --output text)

echo "✓ Stack outputs retrieved"
echo "  KB Bucket: ${KB_BUCKET}"
echo "  Knowledge Base ID: ${KB_ID}"
echo "  Data Source ID: ${DS_ID}"
echo ""

# Upload policy documents
echo "Uploading policy documents to S3..."
if [ -d "knowledge_base_docs" ]; then
    aws s3 cp knowledge_base_docs/ s3://${KB_BUCKET}/policies/ --recursive --region $REGION
    echo "✓ Policy documents uploaded"
else
    echo "⚠ Warning: knowledge_base_docs directory not found"
    echo "  Please upload your policy documents manually to:"
    echo "  s3://${KB_BUCKET}/policies/"
fi
echo ""

# Start ingestion job
echo "Starting Knowledge Base ingestion job..."
JOB_ID=$(aws bedrock-agent start-ingestion-job \
    --knowledge-base-id ${KB_ID} \
    --data-source-id ${DS_ID} \
    --region $REGION \
    --query 'ingestionJob.ingestionJobId' \
    --output text)

echo "✓ Ingestion job started: ${JOB_ID}"
echo ""

# Monitor ingestion job
echo "Monitoring ingestion job status..."
echo "(This may take 2-5 minutes depending on document size)"
echo ""

while true; do
    STATUS=$(aws bedrock-agent get-ingestion-job \
        --knowledge-base-id ${KB_ID} \
        --data-source-id ${DS_ID} \
        --ingestion-job-id ${JOB_ID} \
        --region $REGION \
        --query 'ingestionJob.status' \
        --output text)
    
    echo "Status: ${STATUS}"
    
    if [ "${STATUS}" == "COMPLETE" ]; then
        echo ""
        echo "✓ Ingestion completed successfully!"
        break
    elif [ "${STATUS}" == "FAILED" ]; then
        echo ""
        echo "✗ Ingestion failed. Check the error details:"
        aws bedrock-agent get-ingestion-job \
            --knowledge-base-id ${KB_ID} \
            --data-source-id ${DS_ID} \
            --ingestion-job-id ${JOB_ID} \
            --region $REGION
        exit 1
    fi
    
    sleep 10
done

echo ""
echo "========================================="
echo "Knowledge Base Setup Complete!"
echo "========================================="
echo ""
echo "Your Knowledge Base is ready to use."
echo ""
echo "To test, upload a claim document:"
INPUT_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`InputBucketName`].OutputValue' \
    --output text)

echo "  aws s3 cp sample_claims/claim_auto_accident.txt s3://${INPUT_BUCKET}/"
echo ""
echo "Check the output bucket for the summary:"
OUTPUT_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`OutputBucketName`].OutputValue' \
    --output text)

echo "  aws s3 ls s3://${OUTPUT_BUCKET}/"
echo ""
