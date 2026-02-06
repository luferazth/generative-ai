#!/usr/bin/env python3
"""
Manual Knowledge Base setup script.
Creates Bedrock Knowledge Base via AWS SDK after CDK deployment.
"""
import boto3
import json
import time
import sys
import glob
import os

def get_stack_outputs():
    """Get CloudFormation outputs."""
    cfn = boto3.client('cloudformation', region_name='eu-west-1')
    try:
        response = cfn.describe_stacks(StackName='GenerativeAiStack')
        outputs = {}
        for output in response['Stacks'][0]['Outputs']:
            outputs[output['OutputKey']] = output['OutputValue']
        return outputs
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def create_knowledge_base(kb_data_bucket):
    """Create Bedrock Knowledge Base via SDK."""
    print("\n" + "="*70)
    print("Creating Bedrock Knowledge Base")
    print("="*70)
    
    bedrock_agent = boto3.client('bedrock-agent', region_name='eu-west-1')
    iam = boto3.client('iam')
    
    # Create KB role
    print("\n1. Creating IAM role for Knowledge Base...")
    role_name = "BedrockKBRole-Manual"
    
    try:
        role_response = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            }),
            Description="Role for Bedrock Knowledge Base"
        )
        role_arn = role_response['Role']['Arn']
        print(f"✅ Created role: {role_arn}")
        
        # Attach policies
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="BedrockKBPolicy",
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetObject", "s3:ListBucket"],
                        "Resource": [
                            f"arn:aws:s3:::{kb_data_bucket}",
                            f"arn:aws:s3:::{kb_data_bucket}/*"
                        ]
                    },
                    {
                        "Effect": "Allow",
                        "Action": ["bedrock:InvokeModel"],
                        "Resource": "arn:aws:bedrock:eu-west-1::foundation-model/amazon.titan-embed-text-v1"
                    }
                ]
            })
        )
        
        # Wait for role to propagate
        print("Waiting for role to propagate (10s)...")
        time.sleep(10)
        
    except iam.exceptions.EntityAlreadyExistsException:
        role_arn = f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/{role_name}"
        print(f"✅ Role already exists: {role_arn}")
    
    # Create KB
    print("\n2. Creating Bedrock Knowledge Base...")
    print("Note: This will use the console-created OpenSearch collection")
    print("Please create Knowledge Base manually in AWS Console:")
    print(f"  1. Go to: https://console.aws.amazon.com/bedrock")
    print(f"  2. Click 'Knowledge bases' → 'Create knowledge base'")
    print(f"  3. Name: insurance-policy-kb")
    print(f"  4. IAM Role: {role_arn}")
    print(f"  5. Data source: S3")
    print(f"  6. S3 URI: s3://{kb_data_bucket}/policies/")
    print(f"  7. Embeddings: Amazon Titan Embed Text V1")
    print(f"  8. Vector store: Quick create OpenSearch Serverless")
    print(f"  9. Create and sync")
    print(f" 10. Copy Knowledge Base ID")
    print(f" 11. Set: export KNOWLEDGE_BASE_ID=<your-kb-id>")
    
    return None

def upload_policy_documents(kb_data_bucket):
    """Upload policy documents to S3."""
    print("\n" + "="*70)
    print("Uploading Policy Documents")
    print("="*70)
    
    s3 = boto3.client('s3')
    docs = glob.glob('knowledge_base_docs/*.txt')
    
    if not docs:
        print("❌ No policy documents found")
        return False
    
    print(f"\nUploading {len(docs)} documents to s3://{kb_data_bucket}/policies/")
    
    for doc_path in docs:
        filename = os.path.basename(doc_path)
        s3_key = f"policies/{filename}"
        
        try:
            with open(doc_path, 'rb') as f:
                s3.put_object(
                    Bucket=kb_data_bucket,
                    Key=s3_key,
                    Body=f,
                    ContentType='text/plain'
                )
            print(f"  ✅ {filename}")
        except Exception as e:
            print(f"  ❌ {filename}: {e}")
            return False
    
    print(f"\n✅ All documents uploaded!")
    return True

def main():
    print("\n" + "="*70)
    print("KNOWLEDGE BASE SETUP")
    print("="*70)
    
    # Get outputs
    print("\nGetting CloudFormation outputs...")
    outputs = get_stack_outputs()
    
    if not outputs:
        print("❌ Stack not found. Run: cdk deploy")
        sys.exit(1)
    
    kb_bucket = outputs.get('KBDataBucketName')
    print(f"✅ KB Data Bucket: {kb_bucket}")
    
    # Upload documents
    if not upload_policy_documents(kb_bucket):
        sys.exit(1)
    
    # Instructions for manual KB creation
    create_knowledge_base(kb_bucket)
    
    print("\n" + "="*70)
    print("SETUP COMPLETE")
    print("="*70)
    print("\nPolicy documents are uploaded to S3.")
    print("Follow the instructions above to create the Knowledge Base in AWS Console.")
    print("\nAfter creating the KB, set the environment variable:")
    print("  export KNOWLEDGE_BASE_ID=<your-kb-id>")
    print("\nThen test:")
    print("  python flask_app.py")

if __name__ == '__main__':
    main()
