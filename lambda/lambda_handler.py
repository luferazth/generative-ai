import json
import os
import boto3
from datetime import datetime
from prompt_manager import PromptTemplateManager
from document_processor import DocumentProcessor

# Initialize clients
s3 = boto3.client('s3')
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Initialize managers
prompt_manager = PromptTemplateManager()
doc_processor = DocumentProcessor(bedrock_runtime, prompt_manager)

def handler(event, context):
    """
    Lambda handler triggered by S3 upload event.
    Processes document and saves summary to output bucket.
    """
    try:
        # Get bucket and key from S3 event
        record = event['Records'][0]
        input_bucket = record['s3']['bucket']['name']
        input_key = record['s3']['object']['key']
        
        print(f"Processing document: s3://{input_bucket}/{input_key}")
        
        # Get document from S3
        response = s3.get_object(Bucket=input_bucket, Key=input_key)
        document_text = response['Body'].read().decode('utf-8')
        
        # Get model ID from environment
        model_id = os.environ.get('DEFAULT_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
        
        # Process document
        result = doc_processor.process_document(document_text, model_id)
        
        # Prepare output
        output_data = {
            "input_file": input_key,
            "processed_at": datetime.utcnow().isoformat(),
            "model_used": model_id,
            "extracted_info": result.get("extracted_info"),
            "summary": result.get("summary")
        }
        
        # Save to output bucket
        output_bucket = os.environ['OUTPUT_BUCKET']
        output_key = f"summaries/{input_key.split('/')[-1]}.json"
        
        s3.put_object(
            Bucket=output_bucket,
            Key=output_key,
            Body=json.dumps(output_data, indent=2),
            ContentType='application/json'
        )
        
        print(f"Summary saved to: s3://{output_bucket}/{output_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Document processed successfully',
                'output_location': f"s3://{output_bucket}/{output_key}"
            })
        }
        
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
