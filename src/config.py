"""
Configuration settings for Swiggy Analysis application
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    # File paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    AUTH_DIR = os.path.join(BASE_DIR, 'auth')
    CREDENTIALS_FILE = os.path.join(AUTH_DIR, 'credentials.json')
    TOKEN_FILE = os.path.join(AUTH_DIR, 'token.json')
    
    # Gmail search parameters
    SWIGGY_SENDER = 'noreply@swiggy.in'
    DELIVERY_SUBJECT_KEYWORDS = ["successfully delivered", "order delivered"]
    
    # Date range for analysis (None means all emails)
    START_DATE = os.getenv('START_DATE', '2016/01/01')  # Format: 'YYYY/MM/DD'
    END_DATE = os.getenv('END_DATE', '2025/12/31')      # Format: 'YYYY/MM/DD'
