# Insurance Claim Processing with AWS Bedrock Knowledge Base

Automated insurance claim processing using AWS Bedrock foundation models with RAG (Retrieval-Augmented Generation).

---

## 🚀 Quick Start

```bash
# 1. Configure AWS credentials
aws configure

# 2. Deploy infrastructure
./scripts/fix_and_deploy.sh

# 3. Start web application
./scripts/run_flask_app.sh

# 4. Open browser
open http://localhost:5000
```

**Total time: ~15 minutes**

---

## 📋 Prerequisites

### Required Software
- **AWS CLI** v2.x - [Install Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Python** 3.11+ - [Download](https://www.python.org/downloads/)
- **Node.js** 18+ - [Download](https://nodejs.org/)
- **AWS CDK** - Install: `npm install -g aws-cdk`

### AWS Account Requirements
- Active AWS account with billing enabled
- IAM user or role with permissions:
  - CloudFormation (full access)
  - S3 (create/delete buckets)
  - IAM (create/delete roles and policies)
  - Lambda (create/delete functions)
  - Bedrock (model access and Knowledge Base)
  - OpenSearch Serverless (create/delete collections)

### AWS Bedrock Model Access
**Model access is now enabled by default!** As per [AWS Bedrock Model Access Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html), foundation models are automatically available in your AWS account without requiring manual access requests.

The models used in this project are:
- ✅ Claude 3 Sonnet (`anthropic.claude-3-sonnet-20240229-v1:0`)
- ✅ Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`)
- ✅ Titan Embed Text v2 (`amazon.titan-embed-text-v2:0`)
- ✅ GPT-OSS models
- ✅ Mistral models

**Verify available models** (optional):
```bash
aws bedrock list-foundation-models --region eu-west-1 \
  --query 'modelSummaries[?modelLifecycle.status==`ACTIVE`].[modelId,modelName]' \
  --output table
```

### Environment Variables

Create `.env` file (optional, for local development):
```bash
AWS_DEFAULT_REGION=eu-west-1
AWS_PROFILE=default  # or your profile name
```

**Security Note**: Never commit `.env` file to git (already in `.gitignore`)

---

## 🔒 Security Considerations

### Data Privacy
- **PII Filtering**: Automatic detection and masking of sensitive information
- **Local Processing**: Flask app runs locally, data stays on your machine
- **S3 Encryption**: All buckets use AWS managed encryption
- **OpenSearch**: Encrypted at rest with AWS owned keys

### AWS Credentials
- **Never commit** AWS credentials to git
- Use IAM roles when possible (EC2, Lambda)
- For local development, use `aws configure` or AWS SSO
- Rotate credentials regularly

### Network Security
- OpenSearch collection: Public access (for POC only)
- **Production**: Use VPC and private endpoints
- Lambda: Runs in AWS managed VPC

### Cost Management
- **POC Cost**: ~$5-10 per day
- Set up billing alerts in AWS Console
- Delete resources after testing: `cdk destroy`

**See [SECURITY.md](SECURITY.md) for complete security guidelines**

---

## Features

- **RAG-Enabled Policy Analysis** - Retrieves relevant policy information from Knowledge Base
- **Multi-Model Comparison** - Compare Claude, GPT-OSS, and Mistral models side-by-side
- **Content Filtering** - Automatic PII detection and masking
- **Claim Type Detection** - Auto-detects auto, medical, or property claims
- **Completeness Validation** - Checks if all required fields are present
- **Web Interface** - Easy-to-use interface for testing

---

## Architecture

### High-Level Overview
```
┌─────────────────────────────────────────────────────────────┐
│                        User                                 │
│                    (Flask Web App)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   AWS Infrastructure                        │
│                                                             │
│  ┌──────────────┐    ┌─────────────────────────────┐      │
│  │  S3 Buckets  │    │  Bedrock Knowledge Base     │      │
│  │  - Input     │    │  - Policy Documents         │      │
│  │  - Output    │    │  - RAG Retrieval            │      │
│  │  - Feedback  │    │  - Titan Embed v2 (1024d)   │      │
│  │  - KB Data   │    └──────────┬──────────────────┘      │
│  └──────┬───────┘               │                          │
│         │                       │                          │
│         ▼                       ▼                          │
│  ┌──────────────┐    ┌─────────────────────────────┐      │
│  │   Lambda     │    │  OpenSearch Serverless      │      │
│  │  Function    │    │  - Vector Index (1024d)     │      │
│  │  - Process   │    │  - HNSW Algorithm           │      │
│  │  - Summarize │    │  - insurance-policy-index   │      │
│  └──────┬───────┘    └─────────────────────────────┘      │
│         │                                                  │
│         ▼                                                  │
│  ┌─────────────────────────────────────────────────┐      │
│  │         Bedrock Foundation Models               │      │
│  │  - Claude 3 Sonnet & Haiku                      │      │
│  │  - GPT-OSS 120B & 20B                           │      │
│  │  - Mistral Large & Mixtral 8x7B                 │      │
│  └─────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### CDK Resources (14 Total)

#### Phase 1: IAM & S3 (Independent)
- **BedrockKBRole** - IAM role for Knowledge Base
- **InputDocumentBucket** - Upload claim documents
- **OutputSummaryBucket** - Store processed summaries
- **FeedbackBucket** - Store user feedback
- **KnowledgeBaseDataBucket** - Store policy documents

#### Phase 2: OpenSearch Policies (Depends on IAM)
- **KBEncryptionPolicy** - Encryption at rest
- **KBNetworkPolicy** - Public access (POC only)
- **KBDataAccessPolicy** - IAM permissions

#### Phase 3: OpenSearch Collection (Depends on Policies)
- **KBCollection** - Vector search collection
  - Type: VECTORSEARCH
  - Provisioning: 5-10 minutes
  - Status: CREATING → ACTIVE

#### Phase 4: Vector Index (MANUAL STEP)
- **insurance-policy-index** - Created via Python script
  - Dimensions: 1024 (Titan v2)
  - Algorithm: HNSW with FAISS
  - Must wait for collection to be ACTIVE

#### Phase 5: Knowledge Base (Depends on Index)
- **InsurancePolicyKB** - Bedrock Knowledge Base
  - Model: amazon.titan-embed-text-v2:0
  - Storage: OpenSearch Serverless
  - Index: insurance-policy-index

#### Phase 6: Data Source (Depends on KB)
- **KBDataSource** - S3 data source
  - Prefix: policies/
  - Chunking: Fixed size (300 tokens, 20% overlap)

#### Phase 7: Lambda (Depends on All)
- **DocumentProcessorLambda** - Process documents
  - Runtime: Python 3.11
  - Timeout: 300s
  - Memory: 512 MB
  - Trigger: S3 event (InputDocumentBucket)

### Dependency Chain
```
Level 1: IAM + S3 (independent)
   ↓
Level 2: OpenSearch Policies (depends on IAM)
   ↓
Level 3: OpenSearch Collection (depends on policies)
   ↓
Level 4: Vector Index (MANUAL - depends on collection)
   ↓
Level 5: Knowledge Base (depends on index)
   ↓
Level 6: Data Source (depends on KB)
   ↓
Level 7: Lambda (depends on all)
```

### Critical Dependencies Explained

**1. Circular Dependency Prevention**
- Problem: Role → Collection → DataAccessPolicy → Role ❌
- Solution: Use wildcard ARN in IAM policy
  ```python
  resources=[f"arn:aws:aoss:{region}:{account}:collection/*"]
  ```

**2. OpenSearch Collection Timing**
- Takes 5-10 minutes to provision
- Cannot create index until status = ACTIVE
- This is why manual step is required

**3. Vector Dimension Matching**
- Index dimensions MUST match embedding model
- Titan v1: 1536 dimensions
- Titan v2: 1024 dimensions ← We use this
- Mismatch causes ingestion failure

**4. Knowledge Base Prerequisites**
Requires ALL of:
- ✓ IAM Role with permissions
- ✓ OpenSearch Collection (ACTIVE)
- ✓ Vector Index (manually created)
- ✓ S3 Bucket with data
- ✓ Embedding model access

---

## Installation

```bash
# 1. Clone repository (if applicable)
git clone <repository-url>
cd generative-ai

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install CDK (if not already installed)
npm install -g aws-cdk

# 4. Configure AWS credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (eu-west-1), Output format (json)

# 5. Bootstrap CDK (first time only)
cdk bootstrap aws://ACCOUNT-ID/eu-west-1

# 6. Deploy infrastructure
./scripts/fix_and_deploy.sh
```

---

## Usage

### Check Deployment Status
```bash
# View all resources and their status
./scripts/check_stack_status.sh

# Check Knowledge Base ingestion
./scripts/check_ingestion.sh
```

### Start Flask Application
```bash
./scripts/run_flask_app.sh
```

### Test API Endpoints
```bash
./scripts/test_flask_app.sh
```

### Check Knowledge Base Status
```bash
./scripts/check_ingestion.sh
```

### Upload Sample Claim
```bash
curl -X POST http://localhost:5000/analyze-claim \
  -F "file=@sample_claims/claim_auto_accident.txt" \
  -F "apply_filtering=true"
```

---

## Scripts Reference

All scripts are in the `scripts/` folder:

| Script | Purpose |
|--------|---------|
| `fix_and_deploy.sh` | **PRIMARY** - Deploy everything automatically |
| `run_flask_app.sh` | Start Flask web application |
| `test_flask_app.sh` | Test API endpoints |
| `check_ingestion.sh` | Check Knowledge Base ingestion status |
| `setup_knowledge_base.sh` | Upload docs and start ingestion |
| `deploy_3_steps.sh` | Alternative manual deployment |
| `create_opensearch_index.py` | Create OpenSearch vector index |
| `delete_and_recreate_index.py` | Fix dimension mismatch |

---

## Issues Encountered & Solutions

### Issue 1: Model Access - Now Enabled by Default

**Update**: As per [AWS documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html), foundation model access is now **enabled by default** in AWS Bedrock. No manual access requests are required!

**Models Available** (automatically accessible):
- ✅ Claude 3 Sonnet (`anthropic.claude-3-sonnet-20240229-v1:0`)
- ✅ Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`)
- ✅ GPT-OSS 120B (`openai.gpt-oss-120b-1:0`)
- ✅ GPT-OSS 20B (`openai.gpt-oss-20b-1:0`)
- ✅ Mistral Large (`mistral.mistral-large-2402-v1:0`)
- ✅ Mixtral 8x7B (`mistral.mixtral-8x7b-instruct-v0:1`)
- ✅ Titan Embed Text v2 (`amazon.titan-embed-text-v2:0`)

**Verify Available Models**:
```bash
aws bedrock list-foundation-models --region eu-west-1 \
  --query 'modelSummaries[?modelLifecycle.status==`ACTIVE`].[modelId,modelName]' \
  --output table
```

---

### Issue 2: Storage Configuration - S3_VECTORS vs OpenSearch

**Problem**: Initial implementation used `S3_VECTORS` storage type with `IndexArn` and `IndexName` parameters, which is invalid.

**Root Cause**: `S3_VECTORS` doesn't support custom index configuration. For production use with custom vector indices, OpenSearch Serverless is required.

**Solution**: Migrated to OpenSearch Serverless with:
- Encryption policy for data at rest
- Network policy for access control
- Data access policy for IAM permissions
- Vector collection with HNSW algorithm

**Code Change**:
```python
# ❌ WRONG
storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
    type="S3_VECTORS",
    s3_vectors_configuration={"IndexArn": "...", "IndexName": "..."}  # Not supported!
)

# ✅ CORRECT
storage_configuration=bedrock.CfnKnowledgeBase.StorageConfigurationProperty(
    type="OPENSEARCH_SERVERLESS",
    opensearch_serverless_configuration=bedrock.CfnKnowledgeBase.OpenSearchServerlessConfigurationProperty(
        collection_arn=aoss_collection.attr_arn,
        vector_index_name="insurance-policy-index",
        field_mapping=bedrock.CfnKnowledgeBase.OpenSearchServerlessFieldMappingProperty(
            vector_field="vector",
            text_field="text",
            metadata_field="metadata"
        )
    )
)
```

---

### Issue 3: Circular Dependency - KB Role, Collection, and Data Access Policy

**Problem**: CDK deployment failed with circular dependency error between BedrockKBRole, KBCollection, and KBDataAccessPolicy.

**Root Cause**: KB role's IAM policy referenced specific collection ARN, creating circular reference chain.

**Solution**: Use wildcard pattern for collection ARN in IAM policy:

```python
# ❌ WRONG - Creates circular dependency
kb_role.add_to_policy(
    iam.PolicyStatement(
        actions=["aoss:APIAccessAll"],
        resources=[aoss_collection.attr_arn]  # Circular reference!
    )
)

# ✅ CORRECT - Use wildcard pattern
kb_role.add_to_policy(
    iam.PolicyStatement(
        actions=["aoss:APIAccessAll"],
        resources=[f"arn:aws:aoss:{self.region}:{self.account}:collection/*"]
    )
)
```

---

### Issue 4: Vector Dimension Mismatch - Titan v1 vs Titan v2

**Problem**: Knowledge Base ingestion failed with error:
```
Query vector has invalid dimension: 1024. Dimension should be: 1536
```

**Root Cause**: OpenSearch index was created with 1536 dimensions (Titan v1) but the embedding model used was Titan v2 (1024 dimensions).

**Embedding Model Dimensions**:
- Titan Embed Text v1: **1536 dimensions**
- Titan Embed Text v2: **1024 dimensions**
- Cohere Embed Multilingual v3: **1024 dimensions**

**Solution**: 
1. Delete existing OpenSearch index
2. Recreate index with 1024 dimensions
3. Update CDK stack to use correct embedding model
4. Delete and recreate Knowledge Base

**Fix Script**: `scripts/delete_and_recreate_index.py`

**Code Changes**:
```python
# OpenSearch index mapping
"vector": {
    "type": "knn_vector",
    "dimension": 1024,  # Changed from 1536 to 1024
    "method": {
        "name": "hnsw",
        "engine": "faiss",
        "parameters": {"ef_construction": 512, "m": 16},
        "space_type": "l2"
    }
}

# CDK stack - embedding model
embedding_model_arn=f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0"
```

---

### Issue 5: OpenSearch Index Creation Timing

**Problem**: Attempted to automate index creation with CDK Custom Resource, but:
- OpenSearch Serverless collections take 5-10 minutes to provision
- Custom Resource Provider has 15-minute total timeout
- Timing is unpredictable, causing deployment failures

**Attempted Solutions** (All Abandoned):
1. AWS Generative AI CDK Constructs library - Required Docker
2. Custom Resource Lambda with inline code - Timing issues
3. Custom Resource Lambda with retry logic - Still timed out

**Final Solution**: Manual 3-step deployment
1. Deploy infrastructure (collection, IAM, S3)
2. Wait for collection to be active (~8-10 minutes)
3. Run Python script to create index
4. Deploy Knowledge Base

**Why This Works**: Separates concerns, no timeout constraints, predictable and reliable, no Docker requirement.

---

### Issue 6: Knowledge Base Requires Vector Database

**Critical Understanding**: Bedrock Knowledge Base is NOT a standalone service. It requires:

1. **Vector Database** (one of):
   - OpenSearch Serverless (recommended)
   - Amazon OpenSearch Service
   - Pinecone
   - Redis Enterprise Cloud
   - Amazon Aurora PostgreSQL with pgvector

2. **Embedding Model** (must match vector dimensions):
   - Amazon Titan Embed Text v1 (1536 dimensions)
   - Amazon Titan Embed Text v2 (1024 dimensions)
   - Cohere Embed Multilingual v3 (1024 dimensions)

3. **Vector Index** (must be created manually):
   - Index name must match Knowledge Base configuration
   - Field mapping must match (vector, text, metadata)
   - Dimensions must match embedding model

**Common Mistake**: Assuming Knowledge Base handles vector storage automatically.

**Reality**: You must create vector database, create vector index with correct dimensions, configure Knowledge Base to use that index, and ensure embedding model matches index dimensions.

---

## Project Structure

```
.
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── cdk.json                          # CDK configuration
├── app.py                            # CDK app entry point
├── flask_app.py                      # Flask web application
│
├── scripts/                          # All scripts and utilities
│   ├── fix_and_deploy.sh            # PRIMARY deployment script
│   ├── run_flask_app.sh             # Start Flask app
│   ├── test_flask_app.sh            # Test endpoints
│   ├── check_ingestion.sh           # Check KB status
│   ├── setup_knowledge_base.sh      # Upload docs & ingest
│   ├── deploy_3_steps.sh            # Alternative deployment
│   ├── create_opensearch_index.py   # Create vector index
│   ├── delete_and_recreate_index.py # Fix dimensions
│   ├── compare_models_cli.py        # CLI model comparison
│   ├── evaluate_models.py           # Model evaluation
│   ├── setup_knowledge_base.py      # KB setup utility
│   └── setup_knowledge_base_manual.py # Manual KB setup
│
├── generative_ai/                    # CDK stack
│   └── generative_ai_stack.py       # Infrastructure definition
│
├── lambda/                           # Lambda functions
│   ├── lambda_handler.py            # Main handler
│   ├── document_processor.py        # Processing logic
│   ├── bedrock_kb_rag.py           # RAG implementation
│   ├── compare_models.py           # Model comparison
│   ├── content_filter.py           # PII filtering
│   └── prompt_manager.py           # Prompt templates
│
├── templates/                        # Flask templates
│   └── index.html                   # Web interface
│
├── knowledge_base_docs/             # Policy documents
│   ├── auto_accident_policy.txt
│   ├── medical_claims_policy.txt
│   └── property_damage_policy.txt
│
├── sample_claims/                   # Test claims
│   ├── claim_auto_accident.txt
│   ├── claim_medical.txt
│   └── claim_property_damage.txt
│
└── tests/                           # Unit tests
    └── unit/
        └── test_generative_ai_stack.py
```

---

## Configuration

### Region
```bash
export AWS_DEFAULT_REGION=eu-west-1
```

### Embedding Model
```python
# generative_ai/generative_ai_stack.py
embedding_model_arn=f"arn:aws:bedrock:{self.region}::foundation-model/amazon.titan-embed-text-v2:0"
```

### Vector Dimensions
```python
# scripts/create_opensearch_index.py
"dimension": 1024  # Must match embedding model
```

---

## Testing

### Web Interface Features
1. **Document Upload** - Drag & drop claim documents
2. **Model Comparison** - Compare Claude, GPT-OSS, Mistral side-by-side
3. **RAG Analysis** - Policy-aware claim processing with content filtering
4. **Feedback System** - Rate and comment on results

### Sample Claims
Test with provided sample claims:
- `sample_claims/claim_auto_accident.txt`
- `sample_claims/claim_medical.txt`
- `sample_claims/claim_property_damage.txt`

---

## Troubleshooting

### Model not available
Check available models:
```bash
aws bedrock list-foundation-models --region eu-west-1
```

### Dimension mismatch
Run fix script:
```bash
./scripts/delete_and_recreate_index.py
```

### Ingestion failed
Check status:
```bash
./scripts/check_ingestion.sh
```

### Flask app won't start
Install dependencies:
```bash
pip3 install flask werkzeug boto3 opensearch-py requests-aws4auth
```

### Port 5000 in use
Kill process:
```bash
lsof -ti:5000 | xargs kill -9
```

---

## Cleanup

Delete all resources after testing:

```bash
cdk destroy
```

This removes: OpenSearch collection, S3 buckets, Lambda function, Knowledge Base, IAM roles, and all other resources.

**Cost**: Pay-as-you-go, minimal for POC (~$5-10 for 1 day)

---

## Key Learnings

1. **Model Access Management** - Always check model availability before implementation
2. **Knowledge Base Architecture** - Requires external vector database with matching dimensions
3. **CDK Best Practices** - Avoid circular dependencies with wildcard ARNs
4. **OpenSearch Serverless** - Collections take 5-10 minutes to provision
5. **Embedding Models** - Different models have different dimensions (Titan v1: 1536, Titan v2: 1024)

---

## License

This project is for educational and POC purposes.

---

## 📁 Project Structure

```
.
├── README.md                    # This file
├── SECURITY.md                  # Security guidelines
├── .env.example                 # Environment template
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
├── cdk.json                     # CDK configuration
├── app.py                       # CDK entry point
├── flask_app.py                 # Flask web application
│
├── scripts/                     # All deployment & utility scripts
│   ├── fix_and_deploy.sh       # PRIMARY: Full deployment
│   ├── run_flask_app.sh        # Start Flask application
│   ├── test_flask_app.sh       # Test API endpoints
│   ├── check_stack_status.sh   # Check CDK stack status
│   ├── check_ingestion.sh      # Check KB ingestion
│   ├── show_dependencies.sh    # Show resource dependencies
│   ├── setup_knowledge_base.sh # Upload docs & start ingestion
│   ├── deploy_3_steps.sh       # Alternative manual deployment
│   ├── create_opensearch_index.py        # Create vector index
│   ├── delete_and_recreate_index.py      # Fix dimension mismatch
│   ├── compare_models_cli.py             # CLI model comparison
│   ├── evaluate_models.py                # Model evaluation
│   ├── setup_knowledge_base.py           # KB setup utility
│   └── setup_knowledge_base_manual.py    # Manual KB setup
│
├── generative_ai/               # CDK infrastructure
│   └── generative_ai_stack.py  # Stack definition (14 resources)
│
├── lambda/                      # Lambda function code
│   ├── lambda_handler.py       # Main handler
│   ├── document_processor.py   # Processing logic
│   ├── bedrock_kb_rag.py      # RAG implementation
│   ├── compare_models.py      # Model comparison
│   ├── content_filter.py      # PII filtering
│   └── prompt_manager.py      # Prompt templates
│
├── templates/                   # Flask web templates
│   └── index.html              # Web interface
│
├── knowledge_base_docs/         # Policy documents (gitignored)
│   ├── auto_accident_policy.txt
│   ├── medical_claims_policy.txt
│   └── property_damage_policy.txt
│
├── sample_claims/               # Test claims (gitignored)
│   ├── claim_auto_accident.txt
│   ├── claim_medical.txt
│   └── claim_property_damage.txt
│
└── tests/                       # Unit tests
    └── unit/
        └── test_generative_ai_stack.py
```

---

## 🛠️ Scripts Reference

All scripts are in the `scripts/` folder:

### Deployment Scripts
- **fix_and_deploy.sh** - Complete automated deployment (recommended)
- **deploy_3_steps.sh** - Alternative manual 3-step deployment
- **setup_knowledge_base.sh** - Upload documents and start ingestion

### Application Scripts
- **run_flask_app.sh** - Start Flask web application
- **test_flask_app.sh** - Test API endpoints

### Monitoring Scripts
- **check_stack_status.sh** - Check CDK stack and all resources
- **check_ingestion.sh** - Check Knowledge Base ingestion status
- **show_dependencies.sh** - Show resource dependency diagram

### Utility Scripts
- **create_opensearch_index.py** - Create OpenSearch vector index
- **delete_and_recreate_index.py** - Fix dimension mismatch issues
- **compare_models_cli.py** - CLI tool for model comparison
- **evaluate_models.py** - Evaluate model performance
- **setup_knowledge_base.py** - Programmatic KB setup
- **setup_knowledge_base_manual.py** - Manual KB setup

