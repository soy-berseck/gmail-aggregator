#!/usr/bin/env python3
import os
import sys

# Setup
base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)
sys.path.insert(0, base_dir)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Import and run
from app import create_app

app = create_app()

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 Gmail Aggregator - Servidor LOCAL")
    print("="*70)
    print("\n✅ Abre tu navegador en: http://localhost:5000")
    print("🔐 Admin password: admin123\n")
    print("="*70 + "\n")

    app.run(host='127.0.0.1', port=5000, debug=True)
