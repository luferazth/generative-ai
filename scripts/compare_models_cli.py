#!/usr/bin/env python3
"""
CLI tool to compare multiple Bedrock models on the same document
"""
import sys
import json
import boto3
from datetime import datetime

# Add lambda directory to path
sys.path.insert(0, 'lambda')

from compare_models import ModelComparator
from prompt_manager import PromptTemplateManager

def main():
    if len(sys.argv) < 2:
        print("Usage: python compare_models_cli.py <document_file> [model1] [model2] ...")
        print("\nExample:")
        print("  python compare_models_cli.py test_document.txt")
        print("\nAvailable models (on-demand ✅):")
        print("  Anthropic Claude:")
        print("    - anthropic.claude-3-sonnet-20240229-v1:0 (best quality)")
        print("    - anthropic.claude-3-haiku-20240307-v1:0 (faster, cheaper)")
        print("  OpenAI:")
        print("    - openai.gpt-oss-120b-1:0 (120B parameters, excellent quality)")
        print("    - openai.gpt-oss-20b-1:0 (20B parameters, faster)")
        print("  Mistral AI:")
        print("    - mistral.mistral-large-2402-v1:0 (excellent quality)")
        print("    - mistral.mixtral-8x7b-instruct-v0:1 (good balance)")
        sys.exit(1)
    
    document_file = sys.argv[1]
    
    # Default models if none specified
    if len(sys.argv) > 2:
        models = sys.argv[2:]
    else:
        models = [
            'anthropic.claude-3-sonnet-20240229-v1:0',
            'openai.gpt-oss-120b-1:0',
            'anthropic.claude-3-haiku-20240307-v1:0'
        ]
    
    print(f"\n📄 Reading document: {document_file}")
    try:
        with open(document_file, 'r') as f:
            document_text = f.read()
    except FileNotFoundError:
        print(f"❌ Error: File '{document_file}' not found")
        sys.exit(1)
    
    print(f"📊 Comparing {len(models)} models...")
    print(f"Models: {', '.join([m.split('.')[-1].split('-')[0].title() for m in models])}")
    print("\n" + "="*70)
    
    # Initialize clients
    bedrock = boto3.client('bedrock-runtime', region_name='eu-west-1')
    prompt_manager = PromptTemplateManager()
    comparator = ModelComparator(bedrock, prompt_manager)
    
    # Run comparison
    try:
        results = comparator.compare_models(document_text, models)
        
        # Generate and display report
        report = comparator.generate_comparison_report(results)
        print(report)
        
        # Save results to file
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_file = f"model_comparison_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        # Summary table
        print("\n📈 Quick Comparison:")
        print("-" * 70)
        print(f"{'Model':<45} {'Time (s)':<12} {'Length':<10}")
        print("-" * 70)
        
        for model, result in results.items():
            model_name = model.split('.')[-1]
            if result['success']:
                print(f"{model_name:<45} {result['time_seconds']:<12} {result['summary_length']:<10}")
            else:
                print(f"{model_name:<45} {'FAILED':<12} {'-':<10}")
        
        print("-" * 70)
        
        # Winner determination
        successful_results = {k: v for k, v in results.items() if v['success']}
        if successful_results:
            fastest = min(successful_results.items(), key=lambda x: x[1]['time_seconds'])
            print(f"\n🏆 Fastest: {fastest[0].split('.')[-1]} ({fastest[1]['time_seconds']}s)")
        
    except Exception as e:
        print(f"\n❌ Error during comparison: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
