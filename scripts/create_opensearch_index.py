#!/usr/bin/env python3
"""
Simple script to create OpenSearch Serverless index for Bedrock Knowledge Base
No Docker required!
"""
import boto3
import json
import sys
import os
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

def create_index():
    """Create the vector index in OpenSearch Serverless"""
    
    # Get region from environment or default to eu-west-1
    region = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-1')
    
    # Get stack outputs
    cfn = boto3.client('cloudformation', region_name=region)
    try:
        response = cfn.describe_stacks(StackName='GenerativeAiStack')
        outputs = {o['OutputKey']: o['OutputValue'] for o in response['Stacks'][0]['Outputs']}
    except Exception as e:
        print(f"Error getting stack outputs: {e}")
        print("Make sure the stack is deployed first: cdk deploy")
        sys.exit(1)
    
    collection_endpoint = outputs.get('OpenSearchCollectionEndpoint')
    if not collection_endpoint:
        print("Error: OpenSearchCollectionEndpoint not found in stack outputs")
        sys.exit(1)
    
    # Remove https:// prefix
    host = collection_endpoint.replace('https://', '').replace('/', '')
    
    print(f"Collection endpoint: {collection_endpoint}")
    print(f"Region: {region}")
    
    # Set up AWS auth
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, 'aoss')
    
    # Create OpenSearch client
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300
    )
    
    index_name = "insurance-policy-index"
    
    # Check if index exists
    try:
        if client.indices.exists(index=index_name):
            print(f"✓ Index '{index_name}' already exists")
            return
    except Exception as e:
        print(f"Checking index existence: {e}")
    
    # Create index with proper mapping for Bedrock
    index_body = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 512
            }
        },
        "mappings": {
            "properties": {
                "vector": {
                    "type": "knn_vector",
                    "dimension": 1024,  # Titan Embed Text v2
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "parameters": {
                            "ef_construction": 512,
                            "m": 16
                        },
                        "space_type": "l2"
                    }
                },
                "text": {
                    "type": "text"
                },
                "metadata": {
                    "type": "text"
                }
            }
        }
    }
    
    print(f"Creating index '{index_name}'...")
    try:
        response = client.indices.create(index=index_name, body=index_body)
        print(f"✓ Index created successfully!")
        print(json.dumps(response, indent=2))
    except Exception as e:
        print(f"✗ Error creating index: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("OpenSearch Serverless Index Creator")
    print("=" * 60)
    print()
    
    try:
        create_index()
        print()
        print("=" * 60)
        print("Success! Now update the stack to create the Knowledge Base:")
        print("  cdk deploy")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
