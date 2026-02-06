import json

class DocumentProcessor:
    def __init__(self, bedrock_client, prompt_manager):
        self.bedrock = bedrock_client
        self.prompt_manager = prompt_manager
    
    def process_document(self, document_text, model_id):
        """
        Process document: extract information and generate summary
        """
        # Extract information
        extract_prompt = self.prompt_manager.get_prompt(
            "extract_info",
            document_text=document_text
        )
        
        extracted_info = self._invoke_bedrock(model_id, extract_prompt, temperature=0.0)
        
        # Generate summary
        summary_prompt = self.prompt_manager.get_prompt(
            "generate_summary",
            extracted_info=extracted_info
        )
        
        summary = self._invoke_bedrock(model_id, summary_prompt, temperature=0.7)
        
        return {
            "extracted_info": extracted_info,
            "summary": summary
        }
    
    def _invoke_bedrock(self, model_id, prompt, temperature=0.0, max_tokens=1000):
        """
        Invoke Bedrock model with proper formatting for Claude 3, Mistral, OpenAI GPT-OSS, and Amazon Nova models
        """
        # Check model type and format request accordingly
        if model_id.startswith('amazon.nova'):
            # Format request for Amazon Nova models
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                "inferenceConfig": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature
                }
            }
        elif model_id.startswith('openai.gpt-oss'):
            # Format request for OpenAI GPT-OSS models
            request_body = {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_completion_tokens": max_tokens,
                "temperature": temperature
            }
        else:
            # Format request for Claude 3 and Mistral models (same format)
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature
            }
        
        response = self.bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        
        # Extract text based on model type
        if model_id.startswith('amazon.nova'):
            # Amazon Nova response format
            if 'output' in response_body and 'message' in response_body['output']:
                content = response_body['output']['message'].get('content', [])
                if content and len(content) > 0:
                    return content[0].get('text', '')
        elif model_id.startswith('openai.gpt-oss'):
            # OpenAI GPT-OSS response format
            if 'choices' in response_body and len(response_body['choices']) > 0:
                message = response_body['choices'][0].get('message', {})
                return message.get('content', '')
        else:
            # Claude 3 and Mistral response format (same)
            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0]['text']
        
        return response_body.get('completion', '')
