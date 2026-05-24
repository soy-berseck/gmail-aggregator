#!/usr/bin/env python3
"""
Script simple para iniciar el servidor Flask
"""
import os
import sys
import traceback

# Encontrar el directorio correcto
proyecto_dir = None
for item in os.listdir("/Users/juancamilopineda/Desktop"):
    full_path = os.path.join("/Users/juancamilopineda/Desktop", item)
    if os.path.isdir(full_path) and "login" in item.lower() and "correos" in item.lower():
        if len(os.listdir(full_path)) > 10:
            proyecto_dir = full_path
            break

if not proyecto_dir:
    print("❌ No se encontró el directorio del proyecto")
    sys.exit(1)

print(f"📁 Directorio: {proyecto_dir}")
os.chdir(proyecto_dir)
sys.path.insert(0, proyecto_dir)

# Configurar variables de entorno
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["FLASK_ENV"] = "development"

print("\n" + "="*70)
print("🚀 INICIANDO GMAIL AGGREGATOR")
print("="*70)

try:
    print("\n1️⃣  Importando Flask...")
    from flask import Flask
    print("   ✅ Flask importado")

    print("\n2️⃣  Cargando configuración...")
    from config import Config
    print("   ✅ Config cargada")

    print("\n3️⃣  Inicializando base de datos...")
    from db import init_db
    init_db()
    print("   ✅ Base de datos inicializada")

    print("\n4️⃣  Creando app Flask...")
    from app import create_app
    app = create_app()
    print("   ✅ App creada")

    print("\n5️⃣  Verificando rutas...")
    rutas = list(app.url_map.iter_rules())
    print(f"   ✅ {len(rutas)} rutas registradas")

    print("\n" + "="*70)
    print("✅ TODO LISTO - SERVIDOR INICIANDO")
    print("="*70)
    print("\n📍 Abre en tu navegador: http://localhost:5000")
    print("🔐 Contraseña admin: admin123")
    print("\nPresiona Ctrl+C para detener el servidor\n")
    print("="*70 + "\n")

    # Iniciar servidor
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        use_reloader=False
    )

except Exception as e:
    print("\n" + "❌ "*35)
    print(f"\n❌ ERROR: {e}\n")
    print("Traceback completo:")
    print("-" * 70)
    traceback.print_exc()
    print("-" * 70)
    sys.exit(1)
