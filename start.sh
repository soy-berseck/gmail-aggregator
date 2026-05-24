#!/bin/bash

cd "$(dirname "$0")"

echo "========================================"
echo "🚀 Gmail Aggregator - Iniciando..."
echo "========================================"

export FLASK_APP=app.py
export FLASK_ENV=development
export OAUTHLIB_INSECURE_TRANSPORT=1

python3 -m flask run --host=0.0.0.0 --port=5000 --debug

echo ""
echo "========================================"
echo "📍 Abre: http://localhost:5000"
echo "========================================"
