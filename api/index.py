import sys
import os
from pathlib import Path

# Add parent directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from app import create_app

app = create_app()
