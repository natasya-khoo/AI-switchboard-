"""
Helper utility functions
"""
from datetime import datetime
import hashlib
import os

def generate_project_code(prefix="P"):
    """Generate unique project code"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"{prefix}{timestamp}"

def validate_project_code(code):
    """Validate project code format"""
    if not code:
        return False, "Project code is required"
    
    if len(code) < 3:
        return False, "Project code must be at least 3 characters"
    
    if len(code) > 20:
        return False, "Project code must be less than 20 characters"
    
    # Check for invalid characters
    if not code.replace('-', '').replace('_', '').isalnum():
        return False, "Project code can only contain letters, numbers, hyphens and underscores"
    
    return True, ""

def calculate_labor_hours(components, labor_rates):
    """Calculate total labor hours based on component types"""
    total_hours = 0
    
    for component in components:
        comp_class = component.get('itclass', 'OTHER')
        qty = component.get('qty', 1)
        rate = labor_rates.get(comp_class, 0.5)  # Default 30 min
        
        total_hours += qty * rate
    
    # Add base time for panel assembly
    total_hours += 4
    
    return total_hours

def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:,.2f}"

def format_percentage(value):
    """Format value as percentage"""
    return f"{value:.1f}%"

def sanitize_filename(filename):
    """Sanitize filename for safe file operations"""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    return filename

def hash_file(filepath):
    """Generate hash of file for integrity checking"""
    hash_md5 = hashlib.md5()
    
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    
    return hash_md5.hexdigest()

def ensure_directory(directory):
    """Ensure directory exists, create if not"""
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    return directory

def truncate_text(text, max_length=100):
    """Truncate text to max length with ellipsis"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

class ProgressTracker:
    """Track progress of long-running operations"""
    
    def __init__(self, total_items):
        self.total = total_items
        self.current = 0
        self.start_time = datetime.now()
    
    def update(self, increment=1):
        """Update progress"""
        self.current += increment
    
    def get_percentage(self):
        """Get progress percentage"""
        if self.total == 0:
            return 0
        return (self.current / self.total) * 100
    
    def get_eta(self):
        """Estimate time remaining"""
        if self.current == 0:
            return None
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.current / elapsed
        remaining_items = self.total - self.current
        
        if rate == 0:
            return None
        
        eta_seconds = remaining_items / rate
        return int(eta_seconds)
    
    def is_complete(self):
        """Check if complete"""
        return self.current >= self.total