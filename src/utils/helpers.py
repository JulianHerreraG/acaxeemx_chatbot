import logging
from ..config import settings

def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def validate_environment():
    required_vars = [
        'FIREBASE_CREDENTIALS_PATH',
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY'
    ]
    missing = [var for var in required_vars if not getattr(settings, var.lower(), None)]
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")