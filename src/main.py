import uvicorn
from .api.main import app
from .utils.helpers import setup_logging, validate_environment

def main():
    setup_logging()
    validate_environment()
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    main()