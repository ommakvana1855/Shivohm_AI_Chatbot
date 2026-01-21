import sys
from pathlib import Path

# Add project root to Python path FIRST
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now use absolute imports (no dots)
import uvicorn
from api.routes import app

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )