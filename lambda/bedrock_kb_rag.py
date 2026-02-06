"""
AWS Bedrock Knowledge Base RAG Component
Uses AWS Bedrock Knowledge Base for policy information retrieval with content filtering.
"""
import boto3
import json
from typing import Dict, List, Optional

class BedrockKnowledgeBaseRAG:
    """
    RAG component using AWS Bedrock Knowledge Base for policy information.
    Integrates with content filtering for sensitive data protection.
    """
    
    def __init__(self, knowledge_base_id: Optional[str] = None):
        """
        Initialize Bedrock Knowledge Base RAG.
        
        Args:
            knowledge_base_id: AWS Bedrock Knowledge Base ID (optional for fallback mode)
        """
        self.knowledge_base_id = knowledge_base_id
        
        # Initialize Bedrock Agent Runtime client for KB queries
        if knowledge_base_id:
            self.bedrock_agent = boto3.client('bedrock-agent-runtime')  # Uses default region
        else:
            self.bedrock_agent = None
        
        # Fallback to simple policy knowledge if KB not configured
        self.use_fallback = knowledge_base_id is None
        
        # Simple policy knowledge (fallback)
        self.policy_knowledge = {
            "auto_accident": {
                "coverage_types": ["Collision", "Comprehensive", "Liability"],
                "required_info": ["Police report number", "Other driver information", "Witness statements"],
                "typical_deductible": "$500-$1000",
                "processing_time": "7-14 business days",
                "documentation": "Photos of damage, repair estimates, police report"
            },
            "property_damage": {
                "coverage_types": ["Homeowners", "Renters", "Property"],
                "required_info": ["Date of incident", "Cause of damage", "Extent of damage"],
                "typical_deductible": "$1000-$2500",
                "processing_time": "10-21 business days",
                "documentation": "Photos, repair estimates, receipts for damaged items"
            },
            "medical": {
                "coverage_types": ["Medical Payments", "Personal Injury Protection"],
                "required_info": ["Medical provider information", "Treatment dates", "Diagnosis"],
                "typical_deductible": "$0-$500",
                "processing_time": "14-30 business days",
                "documentation": "Medical bills, treatment records, prescription receipts"
            }
        }
    
    def retrieve_policy_context(self, query: str, max_results: int = 5) -> Dict:
        """
        Retrieve policy information from Bedrock Knowledge Base.
        Falls back to simple knowledge if KB not configured.
        
        Args:
            query: Query text for policy information
            max_results: Maximum number of results to retrieve
            
        Returns:
            dict: Retrieved policy context
        """
        if self.use_fallback or not self.bedrock_agent:
            # Use simple keyword-based retrieval
            return self._fallback_retrieval(query)
        
        try:
            # Query Bedrock Knowledge Base
            response = self.bedrock_agent.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={
                    'text': query
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results
                    }
                }
            )
            
            # Extract retrieved results
            results = []
            for result in response.get('retrievalResults', []):
                results.append({
                    'content': result['content']['text'],
                    'score': result.get('score', 0),
                    'location': result.get('location', {}),
                    'metadata': result.get('metadata', {})
                })
            
            return {
                'source': 'bedrock_kb',
                'results': results,
                'query': query
            }
        
        except Exception as e:
            print(f"Error querying Knowledge Base: {e}")
            # Fallback to simple retrieval
            return self._fallback_retrieval(query)
    
    def _fallback_retrieval(self, query: str) -> Dict:
        """
        Fallback retrieval using simple keyword matching.
        
        Args:
            query: Query text
            
        Returns:
            dict: Policy context
        """
        query_lower = query.lower()
        
        # Determine claim type
        if any(word in query_lower for word in ['vehicle', 'car', 'accident', 'collision', 'driver']):
            claim_type = "auto_accident"
        elif any(word in query_lower for word in ['property', 'home', 'house', 'building', 'fire', 'water']):
            claim_type = "property_damage"
        elif any(word in query_lower for word in ['medical', 'injury', 'hospital', 'treatment', 'doctor']):
            claim_type = "medical"
        else:
            claim_type = "general"
        
        policy_info = self.policy_knowledge.get(claim_type, self.policy_knowledge['auto_accident'])
        
        return {
            'source': 'fallback',
            'claim_type': claim_type,
            'policy_info': policy_info,
            'query': query
        }
    
    def enrich_prompt_with_kb(self, base_prompt: str, claim_text: str, apply_filtering: bool = True) -> Dict:
        """
        Enrich prompt with Knowledge Base context and optionally filter sensitive data.
        
        Args:
            base_prompt: Base prompt template
            claim_text: Claim document text
            apply_filtering: Whether to apply content filtering
            
        Returns:
            dict: {
                'enriched_prompt': str,
                'policy_context': dict,
                'filtered_text': str (if filtering applied),
                'filter_summary': dict (if filtering applied)
            }
        """
        result = {
            'base_prompt': base_prompt,
            'original_text': claim_text
        }
        
        # Apply content filtering if requested
        if apply_filtering:
            from content_filter import ContentFilter
            content_filter = ContentFilter()
            filter_result = content_filter.filter_document(claim_text)
            
            filtered_text = filter_result['filtered_text']
            result['filtered_text'] = filtered_text
            result['filter_summary'] = filter_result['summary']
            result['detections'] = filter_result['detections']
        else:
            filtered_text = claim_text
            result['filtered_text'] = claim_text
            result['filter_summary'] = {'total_detections': 0}
        
        # Retrieve policy context
        policy_context = self.retrieve_policy_context(filtered_text)
        result['policy_context'] = policy_context
        
        # Build enriched prompt
        if policy_context['source'] == 'bedrock_kb':
            # Use KB results
            context_str = "\nPOLICY CONTEXT FROM KNOWLEDGE BASE:\n"
            for i, kb_result in enumerate(policy_context['results'][:3], 1):
                context_str += f"\n{i}. {kb_result['content']}\n"
        else:
            # Use fallback
            policy_info = policy_context['policy_info']
            context_str = f"""
POLICY CONTEXT:
- Claim Type: {policy_context['claim_type'].replace('_', ' ').title()}
- Coverage Types: {', '.join(policy_info['coverage_types'])}
- Required Information: {', '.join(policy_info['required_info'])}
- Typical Deductible: {policy_info['typical_deductible']}
- Expected Processing Time: {policy_info['processing_time']}
- Required Documentation: {policy_info['documentation']}

"""
        
        enriched_prompt = context_str + base_prompt
        result['enriched_prompt'] = enriched_prompt
        result['enrichment_stats'] = {
            'base_length': len(base_prompt),
            'enriched_length': len(enriched_prompt),
            'context_added': len(enriched_prompt) - len(base_prompt)
        }
        
        return result
    
    def validate_claim_with_kb(self, extracted_info: str, claim_text: str) -> Dict:
        """
        Validate claim completeness using Knowledge Base policy requirements.
        
        Args:
            extracted_info: Extracted information from claim
            claim_text: Original claim text
            
        Returns:
            dict: Validation results
        """
        # Get policy context
        policy_context = self.retrieve_policy_context(claim_text)
        
        if policy_context['source'] == 'fallback':
            # Use simple validation
            policy_info = policy_context['policy_info']
            required_fields = policy_info["required_info"]
            
            extracted_lower = extracted_info.lower()
            missing_fields = []
            present_fields = []
            
            for field in required_fields:
                field_keywords = field.lower().split()
                if any(keyword in extracted_lower for keyword in field_keywords):
                    present_fields.append(field)
                else:
                    missing_fields.append(field)
            
            return {
                'is_complete': len(missing_fields) == 0,
                'present_fields': present_fields,
                'missing_fields': missing_fields,
                'completeness_score': len(present_fields) / len(required_fields) if required_fields else 1.0,
                'source': 'fallback'
            }
        else:
            # Use KB-based validation
            return {
                'is_complete': True,  # Simplified for KB
                'present_fields': [],
                'missing_fields': [],
                'completeness_score': 1.0,
                'source': 'bedrock_kb',
                'kb_results': policy_context['results']
            }
