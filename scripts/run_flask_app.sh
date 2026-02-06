#!/bin/bash
set -e

echo "=========================================="
echo "Starting Flask Application"
echo "=========================================="
echo ""

# Set region
export AWS_DEFAULT_REGION=eu-west-1

echo "Fetching stack outputs..."
echo "------------------------------------------"

# Get stack outputs
INPUT_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region eu-west-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`InputBucketName`].OutputValue' \
    --output text)

OUTPUT_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region eu-west-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`OutputBucketName`].OutputValue' \
    --output text)

FEEDBACK_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region eu-west-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`FeedbackBucketName`].OutputValue' \
    --output text)

KNOWLEDGE_BASE_ID=$(aws cloudformation describe-stacks \
    --stack-name GenerativeAiStack \
    --region eu-west-1 \
    --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' \
    --output text)

echo "✓ Configuration loaded:"
echo "  Input Bucket: $INPUT_BUCKET"
echo "  Output Bucket: $OUTPUT_BUCKET"
echo "  Feedback Bucket: $FEEDBACK_BUCKET"
echo "  Knowledge Base ID: $KNOWLEDGE_BASE_ID"
echo ""

# Export environment variables
export INPUT_BUCKET
export OUTPUT_BUCKET
export FEEDBACK_BUCKET
export KNOWLEDGE_BASE_ID

echo "Installing Python dependencies..."
echo "------------------------------------------"
pip3 install -q flask werkzeug boto3 opensearch-py requests-aws4auth

echo ""
echo "=========================================="
echo "Starting Flask server on http://localhost:5000"
echo "=========================================="
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run Flask app
python3 flask_app.py
