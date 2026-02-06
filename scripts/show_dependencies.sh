#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           CDK Resource Dependency Diagram                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

cat << 'EOF'

DEPLOYMENT ORDER & DEPENDENCIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 1: IAM & S3 (No dependencies)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐             │
│  │  BedrockKBRole   │    │   S3 Buckets     │             │
│  │  (IAM Role)      │    │  - Input         │             │
│  │                  │    │  - Output        │             │
│  └──────────────────┘    │  - Feedback      │             │
│                          │  - KB Data       │             │
│                          └──────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼

Phase 2: OpenSearch Policies (Depends on BedrockKBRole)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐             │
│  │ KBEncryptionPolicy│   │ KBNetworkPolicy  │             │
│  │ (Encryption)     │    │ (Public Access)  │             │
│  └──────────────────┘    └──────────────────┘             │
│                                                             │
│  ┌──────────────────────────────────────────┐             │
│  │     KBDataAccessPolicy                   │             │
│  │     (Includes BedrockKBRole ARN)         │             │
│  │     Depends on: BedrockKBRole            │             │
│  └──────────────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼

Phase 3: OpenSearch Collection (Depends on all policies)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌──────────────────────────────────────────┐             │
│  │     KBCollection                         │             │
│  │     (OpenSearch Serverless)              │             │
│  │                                          │             │
│  │     Depends on:                          │             │
│  │     - KBEncryptionPolicy                 │             │
│  │     - KBNetworkPolicy                    │             │
│  │     - KBDataAccessPolicy                 │             │
│  │                                          │             │
│  │     Status: Takes 5-10 minutes           │             │
│  └──────────────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼

Phase 4: MANUAL STEP - Vector Index Creation
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ⚠️  MANUAL STEP REQUIRED                                  │
│                                                             │
│  Run: python3 scripts/create_opensearch_index.py          │
│                                                             │
│  Creates:                                                   │
│  - Index: insurance-policy-index                           │
│  - Dimensions: 1024 (Titan v2)                             │
│  - Algorithm: HNSW with FAISS                              │
│                                                             │
│  Must wait for collection to be ACTIVE first!              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼

Phase 5: Knowledge Base (Depends on Collection + Index)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌──────────────────────────────────────────┐             │
│  │     InsurancePolicyKB                    │             │
│  │     (Bedrock Knowledge Base)             │             │
│  │                                          │             │
│  │     Depends on:                          │             │
│  │     - BedrockKBRole                      │             │
│  │     - KBCollection (must be ACTIVE)      │             │
│  │     - Vector Index (manual creation)     │             │
│  │     - KnowledgeBaseDataBucket            │             │
│  │                                          │             │
│  │     Configuration:                       │             │
│  │     - Model: amazon.titan-embed-text-v2:0│             │
│  │     - Dimensions: 1024                   │             │
│  │     - Index: insurance-policy-index      │             │
│  └──────────────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼

Phase 6: Data Source (Depends on Knowledge Base)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌──────────────────────────────────────────┐             │
│  │     KBDataSource                         │             │
│  │     (S3 Data Source)                     │             │
│  │                                          │             │
│  │     Depends on:                          │             │
│  │     - InsurancePolicyKB                  │             │
│  │     - KnowledgeBaseDataBucket            │             │
│  │                                          │             │
│  │     Configuration:                       │             │
│  │     - Source: S3                         │             │
│  │     - Prefix: policies/                  │             │
│  │     - Chunking: Fixed size (300 tokens)  │             │
│  └──────────────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼

Phase 7: Lambda Function (Depends on all buckets + KB)
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ┌──────────────────────────────────────────┐             │
│  │     DocumentProcessorLambda              │             │
│  │     (Lambda Function)                    │             │
│  │                                          │             │
│  │     Depends on:                          │             │
│  │     - InputDocumentBucket (trigger)      │             │
│  │     - OutputSummaryBucket (write)        │             │
│  │     - FeedbackBucket (read/write)        │             │
│  │     - KnowledgeBaseDataBucket (read)     │             │
│  │     - InsurancePolicyKB (KB ID)          │             │
│  │                                          │             │
│  │     Permissions:                         │             │
│  │     - S3 read/write                      │             │
│  │     - Bedrock InvokeModel                │             │
│  │     - Bedrock Retrieve                   │             │
│  │     - Bedrock RetrieveAndGenerate        │             │
│  └──────────────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘


CRITICAL DEPENDENCIES EXPLAINED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Circular Dependency Prevention:
   ─────────────────────────────
   BedrockKBRole uses WILDCARD ARN for OpenSearch:
   arn:aws:aoss:{region}:{account}:collection/*
   
   This breaks the circular dependency:
   Role → Collection → DataAccessPolicy → Role ❌
   
   Instead:
   Role (wildcard) ✓
   DataAccessPolicy (uses Role ARN) ✓
   Collection (uses DataAccessPolicy) ✓

2. OpenSearch Collection Timing:
   ─────────────────────────────
   Collection takes 5-10 minutes to provision
   Status: CREATING → ACTIVE
   
   Cannot create index until status = ACTIVE
   This is why manual step is required

3. Vector Index Requirements:
   ──────────────────────────
   - Must match embedding model dimensions
   - Titan v1: 1536 dimensions
   - Titan v2: 1024 dimensions ← We use this
   - Cohere v3: 1024 dimensions
   
   Mismatch causes ingestion failure!

4. Knowledge Base Dependencies:
   ────────────────────────────
   Requires ALL of:
   ✓ IAM Role with permissions
   ✓ OpenSearch Collection (ACTIVE)
   ✓ Vector Index (manually created)
   ✓ S3 Bucket for data
   ✓ Embedding model access

5. Data Source Ingestion:
   ──────────────────────
   After deployment:
   1. Upload documents to S3 (policies/ prefix)
   2. Start ingestion job
   3. Wait 2-3 minutes for completion
   4. Verify with: ./scripts/check_ingestion.sh


DEPLOYMENT SEQUENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Deploy Infrastructure
   $ cdk deploy
   
   Creates:
   - IAM roles
   - S3 buckets
   - OpenSearch policies
   - OpenSearch collection (starts provisioning)
   
   Wait: 8-10 minutes for collection to be ACTIVE

Step 2: Create Vector Index
   $ python3 scripts/create_opensearch_index.py
   
   Creates:
   - Index: insurance-policy-index
   - Dimensions: 1024
   - Algorithm: HNSW

Step 3: Deploy Knowledge Base
   (Already deployed in Step 1, but now functional)
   
   Upload documents:
   $ ./scripts/setup_knowledge_base.sh
   
   This:
   - Uploads policy documents to S3
   - Starts ingestion job
   - Waits for completion

Step 4: Verify
   $ ./scripts/check_ingestion.sh
   
   Should show: COMPLETE


RESOURCE RELATIONSHIPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BedrockKBRole
  ├── Permissions to: OpenSearch (wildcard)
  ├── Permissions to: S3 (KnowledgeBaseDataBucket)
  └── Permissions to: Bedrock (Titan v2 model)

KBDataAccessPolicy
  ├── Includes: BedrockKBRole ARN
  └── Includes: Root account (for manual operations)

KBCollection
  ├── Depends on: KBEncryptionPolicy
  ├── Depends on: KBNetworkPolicy
  └── Depends on: KBDataAccessPolicy

InsurancePolicyKB
  ├── Uses: BedrockKBRole
  ├── Uses: KBCollection
  ├── Uses: Vector Index (manual)
  └── Uses: KnowledgeBaseDataBucket

KBDataSource
  ├── Belongs to: InsurancePolicyKB
  └── Reads from: KnowledgeBaseDataBucket

DocumentProcessorLambda
  ├── Triggered by: InputDocumentBucket
  ├── Writes to: OutputSummaryBucket
  ├── Reads/Writes: FeedbackBucket
  ├── Reads from: KnowledgeBaseDataBucket
  └── Queries: InsurancePolicyKB


EOF

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Dependency Diagram Complete                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
