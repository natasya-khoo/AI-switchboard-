"""
Component matching using fuzzy logic
"""
from typing import List, Dict, Tuple, Optional
from fuzzywuzzy import fuzz, process
from database import Database
from config import estimator_config

class ComponentMatcher:
    """Match detected components to database"""
    
    def __init__(self, db: Database):
        self.db = db
        self.auto_threshold = estimator_config.AUTO_MATCH_THRESHOLD
        self.review_threshold = estimator_config.REVIEW_THRESHOLD
    
    def match_component(self, detected: Dict) -> Tuple[Optional[int], float, str]:
        """
        Match a detected component to component library
        
        Args:
            detected: Dictionary containing detected component info
            
        Returns:
            Tuple of (component_id, match_score, match_type)
            match_type: 'auto', 'review', 'new'
        """
        itemname = detected.get('itemname', '')
        itclass = detected.get('itclass', 'OTHER')
        manufacturer = detected.get('manufacturer', '')
        model_number = detected.get('model_number', '')
        
        # Search database
        candidates = self.db.get_all_components(itclass)
        
        if not candidates:
            return None, 0, 'new'
        
        # Build search strings
        detected_str = f"{itemname} {manufacturer} {model_number}".strip()
        
        candidate_dict = {}
        for candidate in candidates:
            candidate_str = f"{candidate['itemname']} {candidate['manufacturer']} {candidate['model_number']}".strip()
            candidate_dict[candidate_str] = candidate
        
        # Fuzzy match
        best_match = process.extractOne(
            detected_str,
            candidate_dict.keys(),
            scorer=fuzz.token_sort_ratio
        )
        
        if not best_match:
            return None, 0, 'new'
        
        match_str, match_score = best_match
        matched_component = candidate_dict[match_str]
        
        # Determine match type
        if match_score >= self.auto_threshold:
            match_type = 'auto'
        elif match_score >= self.review_threshold:
            match_type = 'review'
        else:
            match_type = 'new'
        
        return matched_component['component_id'], match_score, match_type
    
    def get_match_suggestions(self, detected: Dict, limit: int = 5) -> List[Dict]:
        """
        Get top N match suggestions for a detected component
        
        Args:
            detected: Dictionary containing detected component info
            limit: Number of suggestions to return
            
        Returns:
            List of component dictionaries with match scores
        """
        itemname = detected.get('itemname', '')
        itclass = detected.get('itclass', 'OTHER')
        manufacturer = detected.get('manufacturer', '')
        model_number = detected.get('model_number', '')
        
        candidates = self.db.get_all_components(itclass)
        
        if not candidates:
            return []
        
        detected_str = f"{itemname} {manufacturer} {model_number}".strip()
        
        candidate_dict = {}
        for candidate in candidates:
            candidate_str = f"{candidate['itemname']} {candidate['manufacturer']} {candidate['model_number']}".strip()
            candidate_dict[candidate_str] = candidate
        
        # Get top matches
        matches = process.extract(
            detected_str,
            candidate_dict.keys(),
            scorer=fuzz.token_sort_ratio,
            limit=limit
        )
        
        results = []
        for match_str, score in matches:
            component = candidate_dict[match_str].copy()
            component['match_score'] = score
            results.append(component)
        
        return results
    
    def match_by_manufacturer_model(self, manufacturer: str, model_number: str) -> Optional[Dict]:
        """
        Try to find exact match by manufacturer and model number
        
        Args:
            manufacturer: Manufacturer name
            model_number: Model/part number
            
        Returns:
            Matched component dictionary or None
        """
        if not manufacturer or not model_number:
            return None
        
        # Search for exact match
        components = self.db.search_components(
            f"{manufacturer} {model_number}",
            limit=10
        )
        
        for component in components:
            if (component['manufacturer'].lower() == manufacturer.lower() and
                component['model_number'].lower() == model_number.lower()):
                return component
        
        return None
    
    def batch_match(self, detected_components: List[Dict]) -> List[Dict]:
        """
        Match multiple components at once
        
        Args:
            detected_components: List of detected component dictionaries
            
        Returns:
            List of match results
        """
        results = []
        
        for detected in detected_components:
            component_id, match_score, match_type = self.match_component(detected)
            
            result = {
                'detected': detected,
                'matched_component_id': component_id,
                'match_score': match_score,
                'match_type': match_type,
                'suggestions': []
            }
            
            # Get suggestions for review/new items
            if match_type in ['review', 'new']:
                result['suggestions'] = self.get_match_suggestions(detected, limit=3)
            
            results.append(result)
        
        return results
    
    def get_match_statistics(self, results: List[Dict]) -> Dict:
        """
        Calculate statistics from batch match results
        
        Args:
            results: List of match results from batch_match
            
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total': len(results),
            'auto_matched': 0,
            'needs_review': 0,
            'new_items': 0,
            'avg_confidence': 0
        }
        
        total_score = 0
        
        for result in results:
            match_type = result['match_type']
            match_score = result['match_score']
            
            if match_type == 'auto':
                stats['auto_matched'] += 1
            elif match_type == 'review':
                stats['needs_review'] += 1
            else:
                stats['new_items'] += 1
            
            total_score += match_score
        
        if len(results) > 0:
            stats['avg_confidence'] = total_score / len(results)
        
        return stats
