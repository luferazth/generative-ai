import json
import boto3
import urllib3
import time
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import http.client

# CloudFormation response helper
def send_response(event, context, response_status, response_data, physical_resource_id=None, reason=None):
    response_url = event['ResponseURL']
    
    response_body = {
        'Status': response_status,
        'Reason': reason or f'See CloudWatch Log Stream: {context.log_stream_name}',
        'PhysicalResourceId': physical_resource_id or context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        'Data': response_data
    }
    
    json_response_body = json.dumps(response_body)
    
    headers = {
        'content-type': '',
        'content-length': str(len(json_response_body))
    }
    
    http = urllib3.PoolManager()
    try:
        http.request('PUT', response_url, body=json_response_body, headers=headers)
    except Exception as e:
        print(f"Failed to send response: {e}")

def make_signed_request(host, method, path, region, payload=None):
    """Make a signed request to OpenSearch Serverless"""
    session = boto3.Session()
    credentials = session.get_credentials()
    
    url = f'https://{host}{path}'
    headers = {
        'Content-Type': 'application/json',
        'Host': host
    }
    
    if payload:
        body = json.dumps(payload).encode('utf-8')
    else:
        body = b''
    
    request = AWSRequest(method=method, url=url, data=body, headers=headers)
    SigV4Auth(credentials, 'aoss', region).add_auth(request)
    
    # Make the request
    conn = http.client.HTTPSConnection(host, timeout=60)
    try:
        conn.request(method, path, body=body, headers=dict(request.headers))
        response = conn.getresponse()
        response_data = response.read().decode('utf-8')
        return response.status, response_data
    finally:
        conn.close()

def wait_for_collection(host, region, max_attempts=20):
    """Wait for collection to be ready"""
    for attempt in range(max_attempts):
        try:
            print(f"Attempt {attempt + 1}/{max_attempts}: Checking collection status...")
            status, response = make_signed_request(host, 'GET', '/_cluster/health', region)
            if status == 200:
                print(f"Collection is ready! Response: {response}")
                return True
            print(f"Collection not ready yet. Status: {status}, Response: {response}")
        except Exception as e:
            print(f"Error checking collection: {e}")
        
        if attempt < max_attempts - 1:
            wait_time = min(30 * (attempt + 1), 120)  # Exponential backoff, max 2 min
            print(f"Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
    
    return False

def handler(event, context):
    print(f"Event: {json.dumps(event)}")
    
    try:
        request_type = event['RequestType']
        collection_endpoint = event['ResourceProperties']['CollectionEndpoint']
        index_name = event['ResourceProperties']['IndexName']
        region = event['ResourceProperties']['Region']
        
        # Remove https:// prefix and trailing slash
        host = collection_endpoint.replace('https://', '').replace('/', '')
        
        print(f"Collection host: {host}")
        print(f"Index name: {index_name}")
        print(f"Region: {region}")
        
        if request_type == 'Delete':
            # Don't delete the index on stack deletion
            print("Delete request - skipping index deletion")
            send_response(event, context, 'SUCCESS', {})
            return
        
        # Wait for collection to be fully active
        print("Waiting for collection to be active...")
        if not wait_for_collection(host, region):
            error_msg = "Collection did not become ready in time"
            print(error_msg)
            send_response(event, context, 'FAILED', {'Error': error_msg}, reason=error_msg)
            return
        
        # Check if index exists
        print(f"Checking if index {index_name} exists...")
        try:
            status, response_data = make_signed_request(host, 'HEAD', f'/{index_name}', region)
            if status == 200:
                print(f"Index {index_name} already exists")
                send_response(event, context, 'SUCCESS', {'IndexName': index_name})
                return
            print(f"Index does not exist. Status: {status}")
        except Exception as e:
            print(f"Error checking index existence: {e}")
            # Continue to create the index
        
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
                        "dimension": 1536,
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
        
        print(f"Creating index {index_name}...")
        print(f"Index body: {json.dumps(index_body, indent=2)}")
        
        status, response_data = make_signed_request(host, 'PUT', f'/{index_name}', region, index_body)
        
        print(f"Create index response - Status: {status}, Response: {response_data}")
        
        if status in [200, 201]:
            print(f"✓ Index created successfully!")
            send_response(event, context, 'SUCCESS', {'IndexName': index_name})
        else:
            error_msg = f"Failed to create index. Status: {status}, Response: {response_data}"
            print(f"✗ {error_msg}")
            send_response(event, context, 'FAILED', {'Error': error_msg}, reason=error_msg)
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        send_response(event, context, 'FAILED', {'Error': error_msg}, reason=error_msg)


