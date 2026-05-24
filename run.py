#!/usr/bin/env python3
import os
import sys

project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)
sys.path.insert(0, project_dir)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from app import create_app

if __name__ == "__main__":
    app = create_app()
    print("\n" + "="*60)
    print("🚀 Gmail Aggregator - Servidor en ejecución")
    print("="*60)
    print("📍 Abre tu navegador en: http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=True, port=5000, use_reloader=False)
