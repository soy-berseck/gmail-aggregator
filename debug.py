#!/usr/bin/env python3
import os
import sys

project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)
sys.path.insert(0, project_dir)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

print("=" * 60)
print("🔍 DEBUG: Intentando cargar la app...")
print("=" * 60)

try:
    print("\n1️⃣  Cargando módulos...")
    from app import create_app
    print("   ✅ app.py cargado")

    print("\n2️⃣  Creando la app Flask...")
    app = create_app()
    print("   ✅ App creada")

    print("\n3️⃣  Analizando rutas...")
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(f"   - {rule.rule} ({', '.join(rule.methods - {'HEAD', 'OPTIONS'})})")

    print(f"   ✅ {len(routes)} rutas registradas:")
    for route in sorted(routes):
        print(route)

    print("\n4️⃣  Probando la ruta raíz /...")
    with app.test_client() as client:
        response = client.get('/')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Ruta / responde correctamente")
            # Mostrar primeras 200 caracteres de la respuesta
            print(f"   Respuesta (primeros 200 chars): {response.data.decode()[:200]}")
        else:
            print(f"   ❌ Error: {response.status_code}")

    print("\n" + "=" * 60)
    print("✅ Todo parece estar bien!")
    print("=" * 60)
    print("\nAhora intenta abrir http://localhost:5000 en tu navegador")
    print("Y ejecuta: python3 run.py\n")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()
