"""
Configuration for AI Estimator
"""
import os
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    """Database connection settings"""
    # Your new AI database
    AI_DB_NAME = "estimator"
    AI_DB_USER = "postgres"
    AI_DB_PASSWORD = "123456"
    AI_DB_HOST = "localhost"
    AI_DB_PORT = 5432
    
    # ERP database (Read-only)
    ERP_DB_NAME = "CS"
    ERP_DB_USER = "postgres"
    ERP_DB_PASSWORD = "123456"
    ERP_DB_HOST = "localhost"
    ERP_DB_PORT = 5432

@dataclass
class DeepSeekConfig:
    """DeepSeek API settings"""
    API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-6ff73d69c94f49448bc1007fb35b9dcc")
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    MODEL = "DeepSeek-V3.2"
    TEMPERATURE = 0.1
    MAX_TOKENS = 6000

@dataclass
class EstimatorConfig:
    """Estimator settings"""
    DEFAULT_LABOR_RATE = 80.00
    DEFAULT_MARKUP_PCT = 15.00
    AUTO_MATCH_THRESHOLD = 85
    REVIEW_THRESHOLD = 70
    
    # Component types
    COMPONENT_CLASSES = [
        'MCB', 'MCCB', 'ACB', 'RCD', 'RCBO',
        'CONTACTOR', 'RELAY', 'TIMER',
        'SWITCH', 'ISOLATOR', 'PUSHBUTTON',
        'BUSBAR', 'TERMINAL',
        'METER', 'AMMETER', 'VOLTMETER',
        'PANEL', 'ENCLOSURE',
        'OTHER'
    ]
    
    # Labor estimation (hours per component)
    LABOR_ESTIMATES = {
        'MCB': 0.25,
        'MCCB': 0.5,
        'ACB': 1.5,
        'CONTACTOR': 1.0,
        'RELAY': 0.5,
        'BUSBAR': 2.0,
        'METER': 0.75,
        'TERMINAL': 0.1,
        'SWITCH': 0.5,
        'PANEL': 4.0,
        'OTHER': 0.5
    }

# Export configs
db_config = DatabaseConfig()
deepseek_config = DeepSeekConfig()
estimator_config = EstimatorConfig()