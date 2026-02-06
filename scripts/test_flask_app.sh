#!/bin/bash

echo "=========================================="
echo "Testing Flask Application Endpoints"
echo "=========================================="
echo ""

BASE_URL="http://localhost:5000"

echo "1. Testing health endpoint..."
echo "------------------------------------------"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

echo "2. Testing available models endpoint..."
echo "------------------------------------------"
curl -s "$BASE_URL/available-models" | python3 -m json.tool | head -20
echo ""

echo "3. Testing analyze-claim with sample claim..."
echo "------------------------------------------"
SAMPLE_CLAIM="sample_claims/claim_auto_accident.txt"

if [ -f "$SAMPLE_CLAIM" ]; then
    echo "Using sample claim: $SAMPLE_CLAIM"
    curl -s -X POST "$BASE_URL/analyze-claim" \
        -F "file=@$SAMPLE_CLAIM" \
        -F "apply_filtering=true" | python3 -m json.tool | head -50
else
    echo "Sample claim file not found: $SAMPLE_CLAIM"
fi

echo ""
echo "=========================================="
echo "✓ Basic tests complete!"
echo "=========================================="
echo ""
echo "Open your browser to: http://localhost:5000"
echo ""
