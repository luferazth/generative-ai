class PromptTemplateManager:
    def __init__(self):
        self.templates = {
            "extract_info": """Extract the following information from this document:
- Claimant Name
- Policy Number
- Incident Date
- Claim Amount
- Incident Description

Document:
{document_text}

Return the information in JSON format.""",
            
            "generate_summary": """Based on this extracted information:
{extracted_info}

Generate a concise summary of the claim in 2-3 sentences.""",

            "compare_summary": """Compare these two summaries and identify key differences:

Summary 1 (Model: {model1}):
{summary1}

Summary 2 (Model: {model2}):
{summary2}

Provide a brief comparison."""
        }
    
    def get_prompt(self, template_name, **kwargs):
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Template {template_name} not found")
        
        return template.format(**kwargs)
    
    def add_template(self, name, template):
        """Add a new prompt template"""
        self.templates[name] = template
    
    def list_templates(self):
        """List all available templates"""
        return list(self.templates.keys())
