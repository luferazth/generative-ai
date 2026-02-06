#!/usr/bin/env python3
"""
Delete existing OpenSearch index and recreate with correct dimensions
"""
import boto3
import json
import sys
import os
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

def delete_and_recreate_index():
    """Delete the old index and create new one with correct dimensions"""
    
    # Get region from environment or default to eu-west-1
    region = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-1')
    
    # Get stack outputs
    cfn = boto3.client('cloudformation', region_name=region)
    try:
        response = cfn.describe_stacks(StackName='GenerativeAiStack')
        outputs = {o['OutputKey']: o['OutputValue'] for o in response['Stacks'][0]['Outputs']}
    except Exception as e:
        print(f"Error getting stack outputs: {e}")
        sys.exit(1)
    
    collection_endpoint = outputs.get('OpenSearchCollectionEndpoint')
    if not collection_endpoint:
        print("Error: OpenSearchCollectionEndpoint not found")
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
    
    # Delete existing index
    print(f"\nDeleting existing index '{index_name}'...")
    try:
        if client.indices.exists(index=index_name):
            response = client.indices.delete(index=index_name)
            print(f"✓ Index deleted successfully!")
        else:
            print(f"Index '{index_name}' does not exist, skipping deletion")
    except Exception as e:
        print(f"Warning during deletion: {e}")
    
    # Create new index with 1024 dimensions for Titan v2
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
    
    print(f"\nCreating new index with 1024 dimensions...")
    try:
        response = client.indices.create(index=index_name, body=index_body)
        print(f"✓ Index created successfully with 1024 dimensions!")
        print(json.dumps(response, indent=2))
    except Exception as e:
        print(f"✗ Error creating index: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("Delete and Recreate OpenSearch Index")
    print("=" * 60)
    print()
    
    try:
        delete_and_recreate_index()
        print()
        print("=" * 60)
        print("✓ Index recreated with correct dimensions!")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
