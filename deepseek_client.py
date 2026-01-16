"""
DeepSeek API Client for Component Detection
Fixed for DeepSeek's image format requirements
"""
import os
import base64
import requests
from typing import Dict, List, Optional
import config 
import json

class DeepSeekClient:
    """Client for DeepSeek Vision API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize DeepSeek client"""
        #self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        self.api_key = api_key or config.deepseek_config.API_KEY
        
        if not self.api_key:
            raise ValueError("DeepSeek API key not found. Set DEEPSEEK_API_KEY environment variable.")
        
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek/deepseek-chat" 
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _get_image_mime_type(self, image_path: str) -> str:
        """Get MIME type from file extension"""
        ext = image_path.lower().split('.')[-1]
        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        return mime_types.get(ext, 'image/jpeg')
    
    def detect_components(self, image_path: str, project_code: str) -> Optional[Dict]:
        """
        Detect electrical components from drawing image
        
        Args:
            image_path: Path to the electrical drawing image
            project_code: Project identifier
            
        Returns:
            Dictionary with detected components and drawing info
        """
        
        # Encode image
        base64_image = self._encode_image(image_path)
        mime_type = self._get_image_mime_type(image_path)
        
        # Create the prompt
        system_prompt = """You are an expert electrical engineer specializing in analyzing electrical single-line diagrams and panel drawings. 

Your task is to identify ALL electrical components visible in the drawing and extract their specifications.

For each component, identify:
1. Component type (itemname): MCB, MCCB, Contactor, Relay, Busbar, Terminal, Cable, Transformer, etc.
2. Component class (itclass): Same as itemname for categorization
3. Quantity (qty): How many of this exact component
4. Manufacturer: Brand name if visible (Schneider, ABB, Siemens, etc.)
5. Model number: Specific model/part number if visible
6. Rating: Electrical ratings (e.g., "63A 3P 415V", "100A", "230V")
7. Description: Any additional details visible
8. Confidence: high/medium/low based on clarity

Also identify:
- Drawing type: single_line_diagram, panel_layout, schematic, etc.
- Voltage system: 415V, 230V, etc.
- Total circuit breakers count
- Main switchboard rating if visible

Return ONLY a valid JSON object with this structure:
{
    "drawing_info": {
        "drawing_type": "single_line_diagram",
        "voltage_system": "415V 3-phase",
        "main_breaker_rating": "630A"
    },
    "components": [
        {
            "itemname": "MCB",
            "itclass": "MCB",
            "qty": 4,
            "manufacturer": "Schneider",
            "model_number": "C60N",
            "rating": "63A 3P",
            "itemdesc": "Miniature Circuit Breaker",
            "confidence": "high",
            "location_on_drawing": "Outgoing circuits 1-4"
        }
    ]
}"""

        user_prompt = f"""Analyze this electrical drawing for project {project_code}.

Identify ALL components visible in the drawing. Be thorough and systematic.

Return ONLY the JSON object, no other text."""

        # Build request payload - CORRECTED FORMAT FOR DEEPSEEK
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt
                        },
                        {
                            "type": "image",  # ✅ DeepSeek format (NOT "image_url")
                            "image": f"data:{mime_type};base64,{base64_image}"  # ✅ Direct base64 string
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4000,
            "response_format": {"type": "json_object"}
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            print("Calling DeepSeek API...")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"API Error {response.status_code}: {response.text}")
                return None
            
            result = response.json()
            
            # Extract the JSON response
            content = result['choices'][0]['message']['content']
            
            # Parse the JSON
            try:
                parsed_result = json.loads(content)
                print(f"✅ Detected {len(parsed_result.get('components', []))} components")
                return parsed_result
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
                print(f"Raw response: {content}")
                return None
            
        except requests.exceptions.Timeout:
            print("Request timed out")
            return None
        except Exception as e:
            print(f"Error calling DeepSeek API: {e}")
            return None
    
    def validate_response(self, response: Dict) -> bool:
        """Validate API response structure"""
        required_keys = ['drawing_info', 'components']
        
        if not all(key in response for key in required_keys):
            return False
        
        if not isinstance(response['components'], list):
            return False
        
        # Validate each component has required fields
        for component in response['components']:
            required_component_keys = ['itemname', 'itclass', 'qty']
            if not all(key in component for key in required_component_keys):
                return False
        
        return True


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python deepseek_client.py <image_path>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    try:
        client = DeepSeekClient()
        result = client.detect_components(image_path, "TEST001")
        
        if result:
            print("\n✅ Analysis successful!")
            print(f"\nDrawing Info:")
            print(json.dumps(result['drawing_info'], indent=2))
            print(f"\nComponents Found: {len(result['components'])}")
            
            for i, comp in enumerate(result['components'], 1):
                print(f"\n{i}. {comp['itemname']} - {comp.get('manufacturer', 'Unknown')}")
                print(f"   Qty: {comp['qty']}, Rating: {comp.get('rating', 'N/A')}")
        else:
            print("❌ Analysis failed")
    
    except Exception as e:
        print(f"Error: {e}")