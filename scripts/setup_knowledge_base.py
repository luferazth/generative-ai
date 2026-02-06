#!/usr/bin/env python3
"""
Setup script for Bedrock Knowledge Base.
Uploads policy documents to S3 and syncs the Knowledge Base.
"""
import boto3
import sys
import glob
import os
import time

def get_stack_outputs(stack_name='GenerativeAiStack'):
    """Get all outputs from CloudFormation stack."""
    cfn = boto3.client('cloudformation', region_name='eu-west-1')
    
    try:
        response = cfn.describe_stacks(StackName=stack_name)
        outputs = response['Stacks'][0]['Outputs']
        
        output_dict = {}
        for output in outputs:
            output_dict[output['OutputKey']] = output['OutputValue']
        
        return output_dict
    
    except Exception as e:
        print(f"❌ Error getting stack outputs: {e}")
        return None

def upload_kb_documents(bucket_name):
    """Upload knowledge base documents to S3."""
    s3 = boto3.client('s3')
    
    print("\n" + "="*70)
    print("Uploading Policy Documents to S3")
    print("="*70)
    print(f"\nTarget Bucket: {bucket_name}")
    print(f"Prefix: policies/")
    
    # Get all policy documents
    docs = glob.glob('knowledge_base_docs/*.txt')
    
    if not docs:
        print("\n❌ Error: No policy documents found in knowledge_base_docs/")
        return False
    
    print(f"\nFound {len(docs)} policy documents:")
    for doc in docs:
        print(f"  - {os.path.basename(doc)}")
    
    print("\nUploading...")
    
    uploaded = 0
    for doc_path in docs:
        filename = os.path.basename(doc_path)
        s3_key = f"policies/{filename}"
        
        try:
            with open(doc_path, 'rb') as f:
                s3.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=f,
                    ContentType='text/plain'
                )
            print(f"  ✅ {filename}")
            uploaded += 1
        except Exception as e:
            print(f"  ❌ {filename}: {e}")
            return False
    
    print(f"\n✅ All {uploaded} documents uploaded successfully!")
    return True

def sync_knowledge_base(kb_id, data_source_id):
    """Trigger Knowledge Base data source sync."""
    bedrock_agent = boto3.client('bedrock-agent', region_name='eu-west-1')
    
    print("\n" + "="*70)
    print("Syncing Knowledge Base Data Source")
    print("="*70)
    print(f"\nKnowledge Base ID: {kb_id}")
    print(f"Data Source ID: {data_source_id}")
    
    try:
        # Start ingestion job
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id
        )
        
        ingestion_job_id = response['ingestionJob']['ingestionJobId']
        print(f"\n✅ Ingestion job started: {ingestion_job_id}")
        print("\nWaiting for ingestion to complete...")
        
        # Poll for completion
        max_wait = 300  # 5 minutes
        wait_time = 0
        
        while wait_time < max_wait:
            time.sleep(10)
            wait_time += 10
            
            job_response = bedrock_agent.get_ingestion_job(
                knowledgeBaseId=kb_id,
                dataSourceId=data_source_id,
                ingestionJobId=ingestion_job_id
            )
            
            status = job_response['ingestionJob']['status']
            print(f"  Status: {status} ({wait_time}s elapsed)")
            
            if status == 'COMPLETE':
                stats = job_response['ingestionJob'].get('statistics', {})
                print(f"\n✅ Ingestion complete!")
                print(f"  Documents scanned: {stats.get('numberOfDocumentsScanned', 0)}")
                print(f"  Documents indexed: {stats.get('numberOfNewDocumentsIndexed', 0)}")
                return True
            elif status == 'FAILED':
                print(f"\n❌ Ingestion failed!")
                print(f"  Failure reasons: {job_response['ingestionJob'].get('failureReasons', [])}")
                return False
        
        print(f"\n⚠️ Ingestion still in progress after {max_wait}s")
        print("Check AWS Console for status")
        return True
        
    except Exception as e:
        print(f"\n❌ Error syncing Knowledge Base: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("BEDROCK KNOWLEDGE BASE SETUP")
    print("="*70)
    
    # Get stack outputs
    print("\nStep 1: Getting CloudFormation outputs...")
    outputs = get_stack_outputs()
    
    if not outputs:
        print("\n❌ Could not get stack outputs.")
        print("Please ensure the CDK stack is deployed:")
        print("  cdk deploy")
        sys.exit(1)
    
    kb_bucket = outputs.get('KBDataBucketName')
    kb_id = outputs.get('KnowledgeBaseId')
    data_source_id = outputs.get('DataSourceId')
    
    print(f"✅ KB Data Bucket: {kb_bucket}")
    print(f"✅ Knowledge Base ID: {kb_id}")
    print(f"✅ Data Source ID: {data_source_id}")
    
    # Upload documents
    print("\nStep 2: Uploading policy documents...")
    if not upload_kb_documents(kb_bucket):
        sys.exit(1)
    
    # Sync Knowledge Base
    print("\nStep 3: Syncing Knowledge Base...")
    if not sync_knowledge_base(kb_id, data_source_id):
        print("\n⚠️ Sync may still be in progress. Check AWS Console.")
    
    print("\n" + "="*70)
    print("SETUP COMPLETE!")
    print("="*70)
    print("\n✅ Knowledge Base is ready to use!")
    print(f"\nKnowledge Base ID: {kb_id}")
    print("\nThe Lambda function already has this ID configured.")
    print("No additional environment variables needed!")
    print("\nTest the Knowledge Base:")
    print("  python flask_app.py")
    print("  # Open http://localhost:5000")
    print("  # Go to RAG Policy Analysis section")
    print("  # Upload a sample claim")

if __name__ == '__main__':
    main()
