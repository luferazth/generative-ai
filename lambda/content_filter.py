"""
Content Filter for Sensitive Information
Detects and masks PII and sensitive data in insurance claims.
"""
import re
from typing import Dict, List, Tuple

class ContentFilter:
    """
    Filters sensitive information from documents before processing.
    Detects and masks PII including SSN, credit cards, emails, phone numbers, etc.
    """
    
    def __init__(self, mask_char='*'):
        self.mask_char = mask_char
        
        # Regex patterns for sensitive data
        self.patterns = {
            'ssn': {
                'pattern': r'\b\d{3}-\d{2}-\d{4}\b',
                'replacement': 'XXX-XX-XXXX',
                'description': 'Social Security Number'
            },
            'credit_card': {
                'pattern': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
                'replacement': 'XXXX-XXXX-XXXX-XXXX',
                'description': 'Credit Card Number'
            },
            'email': {
                'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                'replacement': '[EMAIL_REDACTED]',
                'description': 'Email Address'
            },
            'phone': {
                'pattern': r'\b\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b',
                'replacement': '(XXX) XXX-XXXX',
                'description': 'Phone Number'
            },
            'date_of_birth': {
                'pattern': r'\b(?:DOB|Date of Birth|Birth Date):\s*\d{1,2}/\d{1,2}/\d{4}\b',
                'replacement': 'DOB: XX/XX/XXXX',
                'description': 'Date of Birth'
            },
            'drivers_license': {
                'pattern': r'\b(?:DL|Driver\'?s? License|License)[\s#:]+[A-Z0-9]{5,15}\b',
                'replacement': 'DL: XXXXXXXXX',
                'description': 'Driver\'s License'
            },
            'bank_account': {
                'pattern': r'\b(?:Account|Acct)[\s#:]+\d{8,17}\b',
                'replacement': 'Account: XXXXXXXXXX',
                'description': 'Bank Account Number'
            },
            'vin': {
                'pattern': r'\b[A-HJ-NPR-Z0-9]{17}\b',
                'replacement': 'VIN: XXXXXXXXXXXXX',
                'description': 'Vehicle Identification Number'
            }
        }
    
    def filter_document(self, text: str, filter_types: List[str] = None) -> Dict:
        """
        Filter sensitive information from document text.
        
        Args:
            text (str): Document text to filter
            filter_types (List[str]): Specific filter types to apply (None = all)
            
        Returns:
            dict: {
                'filtered_text': str,
                'detections': List[dict],
                'summary': dict
            }
        """
        if filter_types is None:
            filter_types = list(self.patterns.keys())
        
        filtered_text = text
        detections = []
        
        # Apply each filter
        for filter_type in filter_types:
            if filter_type not in self.patterns:
                continue
            
            pattern_info = self.patterns[filter_type]
            pattern = pattern_info['pattern']
            replacement = pattern_info['replacement']
            
            # Find all matches
            matches = list(re.finditer(pattern, filtered_text, re.IGNORECASE))
            
            for match in matches:
                detections.append({
                    'type': filter_type,
                    'description': pattern_info['description'],
                    'original': match.group(),
                    'replacement': replacement,
                    'position': match.span()
                })
            
            # Replace matches
            filtered_text = re.sub(pattern, replacement, filtered_text, flags=re.IGNORECASE)
        
        # Generate summary
        summary = {
            'total_detections': len(detections),
            'by_type': {}
        }
        
        for detection in detections:
            dtype = detection['type']
            if dtype not in summary['by_type']:
                summary['by_type'][dtype] = 0
            summary['by_type'][dtype] += 1
        
        return {
            'filtered_text': filtered_text,
            'detections': detections,
            'summary': summary,
            'original_length': len(text),
            'filtered_length': len(filtered_text)
        }
    
    def detect_only(self, text: str, filter_types: List[str] = None) -> Dict:
        """
        Detect sensitive information without filtering.
        Useful for auditing and reporting.
        
        Args:
            text (str): Document text to analyze
            filter_types (List[str]): Specific filter types to check
            
        Returns:
            dict: Detection results without filtering
        """
        if filter_types is None:
            filter_types = list(self.patterns.keys())
        
        detections = []
        
        for filter_type in filter_types:
            if filter_type not in self.patterns:
                continue
            
            pattern_info = self.patterns[filter_type]
            pattern = pattern_info['pattern']
            
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            
            for match in matches:
                detections.append({
                    'type': filter_type,
                    'description': pattern_info['description'],
                    'found': match.group(),
                    'position': match.span(),
                    'context': self._get_context(text, match.span())
                })
        
        summary = {
            'total_detections': len(detections),
            'by_type': {},
            'has_sensitive_data': len(detections) > 0
        }
        
        for detection in detections:
            dtype = detection['type']
            if dtype not in summary['by_type']:
                summary['by_type'][dtype] = 0
            summary['by_type'][dtype] += 1
        
        return {
            'detections': detections,
            'summary': summary
        }
    
    def _get_context(self, text: str, span: Tuple[int, int], context_chars: int = 30) -> str:
        """
        Get surrounding context for a detection.
        
        Args:
            text (str): Full text
            span (Tuple[int, int]): Start and end position
            context_chars (int): Characters to include before/after
            
        Returns:
            str: Context string
        """
        start, end = span
        context_start = max(0, start - context_chars)
        context_end = min(len(text), end + context_chars)
        
        context = text[context_start:context_end]
        
        # Add ellipsis if truncated
        if context_start > 0:
            context = '...' + context
        if context_end < len(text):
            context = context + '...'
        
        return context
    
    def add_custom_pattern(self, name: str, pattern: str, replacement: str, description: str):
        """
        Add a custom filtering pattern.
        
        Args:
            name (str): Pattern identifier
            pattern (str): Regex pattern
            replacement (str): Replacement text
            description (str): Pattern description
        """
        self.patterns[name] = {
            'pattern': pattern,
            'replacement': replacement,
            'description': description
        }
    
    def get_filter_report(self, filter_result: Dict) -> str:
        """
        Generate a human-readable report of filtering results.
        
        Args:
            filter_result (dict): Result from filter_document()
            
        Returns:
            str: Formatted report
        """
        summary = filter_result['summary']
        
        report = []
        report.append("Content Filtering Report")
        report.append("=" * 50)
        report.append(f"\nTotal Detections: {summary['total_detections']}")
        
        if summary['total_detections'] > 0:
            report.append("\nDetections by Type:")
            for dtype, count in summary['by_type'].items():
                report.append(f"  - {dtype}: {count}")
            
            report.append(f"\nOriginal Length: {filter_result['original_length']} chars")
            report.append(f"Filtered Length: {filter_result['filtered_length']} chars")
        else:
            report.append("\nNo sensitive information detected.")
        
        return '\n'.join(report)


# Convenience function for quick filtering
def filter_sensitive_data(text: str, filter_types: List[str] = None) -> str:
    """
    Quick function to filter sensitive data from text.
    
    Args:
        text (str): Text to filter
        filter_types (List[str]): Specific types to filter (None = all)
        
    Returns:
        str: Filtered text
    """
    filter = ContentFilter()
    result = filter.filter_document(text, filter_types)
    return result['filtered_text']
