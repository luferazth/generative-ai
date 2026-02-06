from flask import Flask, render_template, request, jsonify, send_file
import boto3
import json
import os
import sys
from datetime import datetime
from werkzeug.utils import secure_filename

# Add lambda directory to path for imports
sys.path.insert(0, 'lambda')

from compare_models import ModelComparator
from prompt_manager import PromptTemplateManager
from content_filter import ContentFilter
from bedrock_kb_rag import BedrockKnowledgeBaseRAG

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize AWS clients
s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime')  # Uses default region from AWS config

# Initialize model comparison tools
prompt_manager = PromptTemplateManager()
model_comparator = ModelComparator(bedrock, prompt_manager)
content_filter = ContentFilter()
policy_rag = BedrockKnowledgeBaseRAG(
    knowledge_base_id=os.environ.get('KNOWLEDGE_BASE_ID')  # Optional
)

# Get bucket names from environment or CDK outputs
INPUT_BUCKET = os.environ.get('INPUT_BUCKET', 'your-input-bucket-name')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'your-output-bucket-name')
FEEDBACK_BUCKET = os.environ.get('FEEDBACK_BUCKET', 'your-feedback-bucket-name')

def save_feedback_to_s3(feedback_entry):
    """Save feedback to S3"""
    try:
        feedback_key = f"feedback/{feedback_entry['id']}.json"
        s3.put_object(
            Bucket=FEEDBACK_BUCKET,
            Key=feedback_key,
            Body=json.dumps(feedback_entry, indent=2),
            ContentType='application/json'
        )
        return True
    except Exception as e:
        print(f"Error saving feedback to S3: {e}")
        return False

def load_feedback_from_s3():
    """Load all feedback from S3"""
    try:
        response = s3.list_objects_v2(Bucket=FEEDBACK_BUCKET, Prefix='feedback/')
        feedback_list = []
        
        if 'Contents' in response:
            for obj in response['Contents']:
                try:
                    obj_response = s3.get_object(Bucket=FEEDBACK_BUCKET, Key=obj['Key'])
                    feedback_data = json.loads(obj_response['Body'].read().decode('utf-8'))
                    feedback_list.append(feedback_data)
                except Exception as e:
                    print(f"Error loading feedback {obj['Key']}: {e}")
        
        return feedback_list
    except Exception as e:
        print(f"Error loading feedback from S3: {e}")
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_document():
    """Upload document to S3 input bucket"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        s3_key = f"documents/{timestamp}_{filename}"
        
        # Upload to S3
        s3.upload_fileobj(
            file,
            INPUT_BUCKET,
            s3_key,
            ExtraArgs={'ContentType': file.content_type or 'text/plain'}
        )
        
        return jsonify({
            'message': 'File uploaded successfully',
            'filename': filename,
            's3_key': s3_key,
            'status': 'processing'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/summaries', methods=['GET'])
def list_summaries():
    """List all processed summaries"""
    try:
        response = s3.list_objects_v2(
            Bucket=OUTPUT_BUCKET,
            Prefix='summaries/'
        )
        
        summaries = []
        if 'Contents' in response:
            for obj in response['Contents']:
                summaries.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
        
        return jsonify({'summaries': summaries})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/summary/<path:key>', methods=['GET'])
def get_summary(key):
    """Get a specific summary"""
    try:
        response = s3.get_object(Bucket=OUTPUT_BUCKET, Key=key)
        summary_data = json.loads(response['Body'].read().decode('utf-8'))
        return jsonify(summary_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'input_bucket': INPUT_BUCKET,
        'output_bucket': OUTPUT_BUCKET
    })

@app.route('/compare', methods=['POST'])
def compare_models():
    """Compare multiple models on the same document"""
    try:
        # Get document text from request
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        document_text = data['text']
        models = data.get('models', [
            'anthropic.claude-3-5-sonnet-20241022-v2:0',
            'anthropic.claude-3-5-haiku-20241022-v1:0'
        ])
        
        # Run comparison
        results = model_comparator.compare_models(document_text, models)
        
        # Generate report
        report = model_comparator.generate_comparison_report(results)
        
        return jsonify({
            'results': results,
            'report': report,
            'models_compared': len(models)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/compare-file', methods=['POST'])
def compare_file():
    """Compare multiple models on an uploaded file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Read file content
        document_text = file.read().decode('utf-8')
        
        # Get models from form data
        models_str = request.form.get('models', '')
        if models_str:
            models = [m.strip() for m in models_str.split(',')]
        else:
            models = [
                'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'anthropic.claude-3-5-haiku-20241022-v1:0'
            ]
        
        # Run comparison
        results = model_comparator.compare_models(document_text, models)
        
        # Generate report
        report = model_comparator.generate_comparison_report(results)
        
        return jsonify({
            'results': results,
            'report': report,
            'models_compared': len(models),
            'filename': file.filename
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/available-models', methods=['GET'])
def available_models():
    """List available Bedrock models"""
    models = {
        'claude-3.5': [
            {
                'id': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'name': 'Claude 3.5 Sonnet v2',
                'description': 'Latest Sonnet - best for summarization',
                'cost': 'Medium'
            },
            {
                'id': 'anthropic.claude-3-5-haiku-20241022-v1:0',
                'name': 'Claude 3.5 Haiku',
                'description': 'Fastest - good for simple summaries',
                'cost': 'Low'
            }
        ],
        'claude-3': [
            {
                'id': 'anthropic.claude-3-sonnet-20240229-v1:0',
                'name': 'Claude 3 Sonnet',
                'description': 'Previous generation Sonnet',
                'cost': 'Medium'
            },
            {
                'id': 'anthropic.claude-3-haiku-20240307-v1:0',
                'name': 'Claude 3 Haiku',
                'description': 'Previous generation Haiku',
                'cost': 'Low'
            }
        ]
    }
    return jsonify(models)

@app.route('/filter-content', methods=['POST'])
def filter_content():
    """Filter sensitive information from text"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text = data['text']
        filter_types = data.get('filter_types', None)  # None = all types
        
        # Filter the content
        result = content_filter.filter_document(text, filter_types)
        
        # Generate report
        report = content_filter.get_filter_report(result)
        
        return jsonify({
            'filtered_text': result['filtered_text'],
            'detections': result['detections'],
            'summary': result['summary'],
            'report': report
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/detect-sensitive', methods=['POST'])
def detect_sensitive():
    """Detect sensitive information without filtering"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text = data['text']
        filter_types = data.get('filter_types', None)
        
        # Detect only (don't filter)
        result = content_filter.detect_only(text, filter_types)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze-claim', methods=['POST'])
def analyze_claim():
    """
    Analyze claim with Bedrock Knowledge Base RAG and content filtering.
    Shows policy context, filtering results, and completeness validation.
    """
    try:
        # Get claim text from file or JSON
        if 'file' in request.files:
            file = request.files['file']
            claim_text = file.read().decode('utf-8')
            filename = file.filename
        else:
            data = request.get_json()
            if not data or 'text' not in data:
                return jsonify({'error': 'No text provided'}), 400
            claim_text = data['text']
            filename = data.get('filename', 'unknown')
        
        apply_filtering = request.form.get('apply_filtering', 'true').lower() == 'true' if 'file' in request.files else data.get('apply_filtering', True)
        
        # Get base extraction prompt
        base_prompt = prompt_manager.get_prompt("extract_info", document_text=claim_text)
        
        # Enrich prompt with KB and apply filtering
        enrichment_result = policy_rag.enrich_prompt_with_kb(base_prompt, claim_text, apply_filtering=apply_filtering)
        
        # Process with default model
        from document_processor import DocumentProcessor
        processor = DocumentProcessor(bedrock, prompt_manager)
        
        # Use filtered text if filtering was applied
        process_text = enrichment_result['filtered_text']
        result = processor.process_document(process_text, 'anthropic.claude-3-sonnet-20240229-v1:0')
        
        # Validate completeness
        validation = policy_rag.validate_claim_with_kb(result['extracted_info'], process_text)
        
        # Build response
        response_data = {
            'filename': filename,
            'policy_context': enrichment_result['policy_context'],
            'content_filtering': {
                'applied': apply_filtering,
                'detections': enrichment_result.get('filter_summary', {}).get('total_detections', 0),
                'details': enrichment_result.get('detections', []) if apply_filtering else []
            },
            'extracted_info': result['extracted_info'],
            'summary': result['summary'],
            'validation': validation,
            'prompt_enrichment': enrichment_result['enrichment_stats']
        }
        
        # Add claim type if using fallback
        if enrichment_result['policy_context']['source'] == 'fallback':
            response_data['claim_type'] = enrichment_result['policy_context']['claim_type']
            response_data['policy_info'] = enrichment_result['policy_context']['policy_info']
        
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback - stored in S3"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Create feedback entry
        feedback_entry = {
            'id': datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f'),
            'timestamp': datetime.utcnow().isoformat(),
            'rating': data.get('rating'),  # 1-5 stars
            'feedback_type': data.get('feedback_type'),  # 'positive', 'negative', 'neutral'
            'model_id': data.get('model_id'),
            'document_id': data.get('document_id'),
            'comment': data.get('comment', ''),
            'accuracy_rating': data.get('accuracy_rating'),  # 1-5
            'speed_rating': data.get('speed_rating'),  # 1-5
            'quality_rating': data.get('quality_rating'),  # 1-5
            'user_agent': request.headers.get('User-Agent', '')
        }
        
        # Save to S3
        if save_feedback_to_s3(feedback_entry):
            return jsonify({
                'message': 'Feedback submitted successfully',
                'feedback_id': feedback_entry['id'],
                'storage': 'S3'
            })
        else:
            return jsonify({'error': 'Failed to save feedback'}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/feedback', methods=['GET'])
def get_feedback():
    """Get all feedback from S3"""
    try:
        feedback_list = load_feedback_from_s3()
        
        # Calculate statistics
        total = len(feedback_list)
        if total == 0:
            return jsonify({
                'feedback': [],
                'statistics': {
                    'total': 0,
                    'average_rating': 0,
                    'by_type': {}
                },
                'storage': 'S3'
            })
        
        # Calculate averages
        ratings = [f['rating'] for f in feedback_list if f.get('rating')]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Count by type
        by_type = {}
        for f in feedback_list:
            ftype = f.get('feedback_type', 'unknown')
            by_type[ftype] = by_type.get(ftype, 0) + 1
        
        return jsonify({
            'feedback': feedback_list,
            'statistics': {
                'total': total,
                'average_rating': round(avg_rating, 2),
                'by_type': by_type
            },
            'storage': 'S3',
            'bucket': FEEDBACK_BUCKET
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/feedback/report', methods=['GET'])
def feedback_report():
    """Generate feedback analytics report from S3"""
    try:
        feedback_list = load_feedback_from_s3()
        
        if not feedback_list:
            return jsonify({
                'message': 'No feedback data available',
                'storage': 'S3',
                'bucket': FEEDBACK_BUCKET
            })
        
        # Calculate detailed statistics
        total = len(feedback_list)
        ratings = [f['rating'] for f in feedback_list if f.get('rating')]
        accuracy_ratings = [f['accuracy_rating'] for f in feedback_list if f.get('accuracy_rating')]
        speed_ratings = [f['speed_rating'] for f in feedback_list if f.get('speed_rating')]
        quality_ratings = [f['quality_rating'] for f in feedback_list if f.get('quality_rating')]
        
        report = {
            'total_feedback': total,
            'storage': 'S3',
            'bucket': FEEDBACK_BUCKET,
            'overall': {
                'average_rating': round(sum(ratings) / len(ratings), 2) if ratings else 0,
                'total_ratings': len(ratings)
            },
            'detailed': {
                'accuracy': {
                    'average': round(sum(accuracy_ratings) / len(accuracy_ratings), 2) if accuracy_ratings else 0,
                    'count': len(accuracy_ratings)
                },
                'speed': {
                    'average': round(sum(speed_ratings) / len(speed_ratings), 2) if speed_ratings else 0,
                    'count': len(speed_ratings)
                },
                'quality': {
                    'average': round(sum(quality_ratings) / len(quality_ratings), 2) if quality_ratings else 0,
                    'count': len(quality_ratings)
                }
            },
            'by_type': {},
            'by_model': {},
            'recent_comments': []
        }
        
        # Count by type
        for f in feedback_list:
            ftype = f.get('feedback_type', 'unknown')
            report['by_type'][ftype] = report['by_type'].get(ftype, 0) + 1
            
            # Count by model
            model = f.get('model_id', 'unknown')
            if model not in report['by_model']:
                report['by_model'][model] = {'count': 0, 'ratings': []}
            report['by_model'][model]['count'] += 1
            if f.get('rating'):
                report['by_model'][model]['ratings'].append(f['rating'])
        
        # Calculate average rating per model
        for model in report['by_model']:
            ratings = report['by_model'][model]['ratings']
            report['by_model'][model]['average_rating'] = round(sum(ratings) / len(ratings), 2) if ratings else 0
        
        # Get recent comments
        comments = [f for f in feedback_list if f.get('comment')]
        report['recent_comments'] = sorted(comments, key=lambda x: x['timestamp'], reverse=True)[:10]
        
        return jsonify(report)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
