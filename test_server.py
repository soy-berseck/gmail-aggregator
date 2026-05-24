#!/usr/bin/env python3
import os
import sys
import threading
import time
import requests

# Setup
base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)
sys.path.insert(0, base_dir)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from app import create_app

def run_server():
    """Ejecutar el servidor en un thread"""
    app = create_app()
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

def test_server():
    """Probar el servidor"""
    print("\n" + "="*70)
    print("🚀 Iniciando servidor en thread...")
    print("="*70)

    # Iniciar servidor en background
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Esperar a que el servidor inicie
    print("⏳ Esperando que el servidor inicie...")
    time.sleep(3)

    # Probar conexión
    print("\n🔍 Probando conexión a http://127.0.0.1:5000...\n")

    try:
        response = requests.get('http://127.0.0.1:5000/', timeout=5)
        print(f"✅ Status: {response.status_code}")
        print(f"✅ Content length: {len(response.text)} caracteres")
        print(f"✅ Primeros 300 chars:\n{response.text[:300]}\n")

        print("="*70)
        print("✅ SERVIDOR FUNCIONANDO CORRECTAMENTE")
        print("="*70)
        print("\n📍 Abre en tu navegador: http://localhost:5000\n")

        # Mantener el servidor corriendo
        print("Presiona Ctrl+C para detener\n")
        while True:
            time.sleep(1)

    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar al servidor")
        print("El servidor puede no estar corriendo correctamente")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_server()
