import json
import time
from document_processor import DocumentProcessor

class ModelComparator:
    def __init__(self, bedrock_client, prompt_manager):
        self.bedrock = bedrock_client
        self.prompt_manager = prompt_manager
        self.processor = DocumentProcessor(bedrock_client, prompt_manager)
    
    def compare_models(self, document_text, models=None):
        """
        Compare multiple Bedrock models on the same document
        """
        if models is None:
            models = [
                'anthropic.claude-3-sonnet-20240229-v1:0',
                'openai.gpt-oss-120b-1:0',
                'anthropic.claude-3-haiku-20240307-v1:0'
            ]
        
        results = {}
        
        for model in models:
            print(f"Processing with model: {model}")
            start_time = time.time()
            
            try:
                # Process with current model
                result = self.processor.process_document(document_text, model)
                elapsed_time = time.time() - start_time
                
                results[model] = {
                    "success": True,
                    "time_seconds": round(elapsed_time, 2),
                    "extracted_info": result["extracted_info"],
                    "summary": result["summary"],
                    "summary_length": len(result["summary"])
                }
            except Exception as e:
                results[model] = {
                    "success": False,
                    "error": str(e),
                    "time_seconds": round(time.time() - start_time, 2)
                }
        
        return results
    
    def generate_comparison_report(self, comparison_results):
        """
        Generate a readable comparison report
        """
        report = "Model Comparison Report\n"
        report += "=" * 50 + "\n\n"
        
        for model, result in comparison_results.items():
            report += f"Model: {model}\n"
            report += f"Status: {'Success' if result['success'] else 'Failed'}\n"
            report += f"Processing Time: {result['time_seconds']}s\n"
            
            if result['success']:
                report += f"Summary Length: {result['summary_length']} chars\n"
                report += f"Summary: {result['summary'][:200]}...\n"
            else:
                report += f"Error: {result['error']}\n"
            
            report += "\n" + "-" * 50 + "\n\n"
        
        return report
