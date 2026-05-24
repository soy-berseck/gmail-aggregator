# Gmail Multi-Account Aggregator

Una aplicación Flask que permite conectar múltiples cuentas de Gmail y buscar correos en todas ellas simultáneamente. Perfecto para encontrar facturas, recibos, pagos y otros correos importantes.

## Características

- 🔐 Autenticación OAuth con Google (seguro, sin almacenar contraseñas)
- 📧 Conecta múltiples cuentas de Gmail
- 🔍 Busca en todos los correos a la vez
- 📋 Vista detallada de cada correo
- 🔄 Sincronización automática de correos
- 🛡️ Tokens OAuth cifrados en la base de datos local

## Instalación

### Requisitos previos

- Python 3.8+
- Una cuenta de Google / Google Cloud Project

### Paso 1: Descargar dependencias

```bash
pip install -r requirements.txt
```

### Paso 2: Configurar Google Cloud Console

1. Ve a [console.cloud.google.com](https://console.cloud.google.com)
2. Crea un nuevo proyecto
3. Habilita la API de Gmail:
   - APIs & Services → Library → Busca "Gmail API" → Enable
4. Crea credenciales OAuth:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Web application**
   - Authorized redirect URIs: `http://localhost:5000/oauth2callback`
   - Descarga el JSON y guárdalo como `credentials.json` en la raíz del proyecto
5. Configura el OAuth consent screen:
   - Elige "External"
   - Llena los campos requeridos
   - Agrega scope: `https://www.googleapis.com/auth/gmail.readonly`
   - Agrega tus cuentas de Gmail como "Test users" (mientras esté en Testing)

### Paso 3: Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y rellena:

```
SECRET_KEY=<cualquier string de al menos 32 caracteres>
FERNET_KEY=<ejecuta el script abajo para generar una>
ADMIN_PASSWORD=<tu contraseña elegida>
```

Para generar `FERNET_KEY`:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

### Paso 4: Ejecutar la aplicación

```bash
python app.py
```

Abre [http://localhost:5000](http://localhost:5000) en tu navegador.

## Uso

### Conectar una cuenta de Gmail

1. Haz click en "Conectar Gmail" en la página de inicio
2. Autoriza con tu cuenta de Google
3. La app sincronizará automáticamente tus correos

### Buscar correos

1. Ve al Dashboard (haz click en "Admin")
2. Ingresa tu contraseña de admin
3. Usa la barra de búsqueda para buscar por:
   - Asunto del correo
   - Remitente
   - Fragmento/preview del correo

### Conectar múltiples cuentas

Simplemente repite el paso 1 con diferentes cuentas de Gmail. Cada cuenta se sincroniza independientemente.

### Sincronizar manualmente

En el Dashboard, haz click en "Sincronizar" en la tarjeta de cualquier cuenta para jalar correos nuevos.

## Seguridad

- ✅ Tokens OAuth cifrados con Fernet antes de almacenar
- ✅ Solo scope `gmail.readonly` (sin permisos de escritura)
- ✅ Cuerpos de correos NO se almacenan permanentemente (se obtienen bajo demanda)
- ✅ `credentials.json` y `.env` están en `.gitignore`

## Estructura de archivos

```
login correos/
├── app.py                    # Punto de entrada
├── config.py                 # Configuración
├── models.py                 # Modelos SQLAlchemy
├── db.py                     # Inicialización de BD
├── crypto.py                 # Cifrado/descifrado de tokens
├── auth/routes.py            # Rutas OAuth
├── gmail/client.py           # Cliente de Gmail API
├── gmail/sync.py             # Sincronización de correos
├── admin/routes.py           # Rutas del admin
└── templates/                # Plantillas HTML
```

## Troubleshooting

### Error: "FERNET_KEY environment variable not set"

Asegúrate de haber configurado `.env` correctamente con `FERNET_KEY`.

### Error: "OAuth error: invalid_request"

Verifica que:
- `credentials.json` existe en la raíz
- El redirect URI en Google Cloud Console es exactamente `http://localhost:5000/oauth2callback`

### Error: "Error 403: access_denied"

Agregaste tu Gmail como "Test user" en el OAuth consent screen del Google Cloud Console.

### Los correos no aparecen después de conectar

La sincronización puede tomar unos segundos. Verifica que los correos coincidan con la búsqueda predeterminada (facturas, recibos, pagos de los últimos 6 meses). Haz click en "Sincronizar" en el Dashboard para jalar nuevos correos.

## Limitaciones actuales

- Solo lectura de correos (scope `gmail.readonly`)
- Base de datos local SQLite (no escalable a millones de correos)
- Sin historial de búsquedas
- Sin filtros avanzados

## Mejoras futuras

- Filtros avanzados por fecha, remitente, etc.
- Etiquetado de correos importantes
- Exportar resultados a CSV
- Desplegar a la nube (AWS, Heroku, etc.)
- Base de datos PostgreSQL para mayor escala

## Licencia

MIT

## Contacto

Juan Camilo Pineda - jcpineda@equitel.com.co
