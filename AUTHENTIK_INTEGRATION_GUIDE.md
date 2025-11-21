# Guía de Integración de Authentik OAuth2/OIDC

Esta guía proporciona una plantilla completa para integrar autenticación Authentik OAuth2/OIDC en aplicaciones web. Puede adaptarse a diferentes frameworks y lenguajes.

## 📋 Tabla de Contenidos

- [¿Qué es Authentik?](#qué-es-authentik)
- [Requisitos Previos](#requisitos-previos)
- [Arquitectura de la Integración](#arquitectura-de-la-integración)
- [Implementación Paso a Paso](#implementación-paso-a-paso)
  - [1. Módulo de Autenticación](#1-módulo-de-autenticación)
  - [2. Configuración Web Automática](#2-configuración-web-automática)
  - [3. Rutas y Callbacks](#3-rutas-y-callbacks)
  - [4. Protección de Rutas](#4-protección-de-rutas)
- [Variables de Entorno](#variables-de-entorno)
- [Despliegue en Producción](#despliegue-en-producción)
- [Troubleshooting](#troubleshooting)
- [Consideraciones de Seguridad](#consideraciones-de-seguridad)

---

## ¿Qué es Authentik?

[Authentik](https://goauthentik.io/) es una plataforma de gestión de identidad y acceso (IAM) de código abierto que proporciona:

- **Single Sign-On (SSO)** con OAuth2/OIDC
- **Gestión centralizada** de usuarios y grupos
- **Autenticación multi-factor (MFA)**
- **Políticas de acceso** personalizables
- **Integración sencilla** con aplicaciones web

### Ventajas de usar Authentik

✅ Autenticación centralizada para múltiples aplicaciones
✅ Control granular de acceso por usuarios y grupos
✅ Seguridad mejorada con MFA y políticas
✅ Fácil gestión de credenciales
✅ Soporte para múltiples protocolos (OAuth2, SAML, LDAP)
✅ Auto-hospedable y gratuito

---

## Requisitos Previos

### En el Servidor de Authentik

1. **Instancia Authentik funcionando** (ej: `https://auth.example.com`)
2. **Cuenta de administrador** con acceso a la API
3. **Token de API** con permisos:
   - `authentik Core: Providers` (view, write)
   - `authentik Core: Applications` (view, write)
   - `authentik Flows: Flows` (view)

### En tu Aplicación

1. **Framework web** (Flask, Django, Express.js, etc.)
2. **Librería OAuth2/OIDC** para tu lenguaje:
   - Python: `authlib`
   - Node.js: `passport-oauth2` o `openid-client`
   - PHP: `league/oauth2-client`
   - Go: `golang.org/x/oauth2`
3. **URL pública** o dominio (para callback OAuth2)

---

## Arquitectura de la Integración

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Usuario   │────────▶│   Tu App     │────────▶│  Authentik  │
│  (Browser)  │         │  (Flask/etc) │         │   Server    │
└─────────────┘         └──────────────┘         └─────────────┘
       │                       │                        │
       │  1. Acceso sin auth   │                        │
       │──────────────────────▶│                        │
       │                       │                        │
       │  2. Redirect a login  │                        │
       │◀──────────────────────│                        │
       │                       │                        │
       │  3. Login Authentik   │                        │
       │─────────────────────────────────────────────▶ │
       │                       │                        │
       │  4. Callback con code │                        │
       │◀──────────────────────────────────────────────│
       │                       │                        │
       │  5. Intercambio token │                        │
       │──────────────────────▶│───────────────────────▶│
       │                       │◀───────────────────────│
       │                       │   (access token)       │
       │  6. Acceso permitido  │                        │
       │◀──────────────────────│                        │
       └───────────────────────┘                        │
```

### Flujo OAuth2:

1. **Usuario intenta acceder** a una ruta protegida
2. **Aplicación redirige** a Authentik para login
3. **Usuario se autentica** en Authentik
4. **Authentik redirige** con código de autorización
5. **Aplicación intercambia** código por token de acceso
6. **Aplicación valida** token y crea sesión
7. **Usuario accede** a la aplicación

---

## Implementación Paso a Paso

### 1. Módulo de Autenticación

Crea un módulo que maneje la lógica de OAuth2. Este es un ejemplo en Python/Flask:

#### `auth.py` - Módulo Principal

```python
#!/usr/bin/env python3
"""
Authentication module for Authentik OAuth2/OIDC
Adaptable to other OAuth2 providers
"""

import os
from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from authlib.integrations.flask_client import OAuth
from datetime import datetime, timedelta


class AuthentikAuth:
    """Authentik OAuth2/OIDC authentication handler"""

    def __init__(self, app):
        self.app = app

        # Enable/disable authentication via environment variable
        self.enabled = os.environ.get('ENABLE_AUTH', 'false').lower() == 'true'

        if not self.enabled:
            print("⚠️  Authentication is DISABLED")
            return

        # Load configuration from environment
        self.base_url = os.environ.get('AUTHENTIK_BASE_URL', '')
        self.client_id = os.environ.get('AUTHENTIK_CLIENT_ID', '')
        self.client_secret = os.environ.get('AUTHENTIK_CLIENT_SECRET', '')
        self.redirect_uri = os.environ.get('AUTHENTIK_REDIRECT_URI', '')
        self.slug = os.environ.get('AUTHENTIK_SLUG', '')  # Application slug for OIDC endpoint

        # Optional: restrict access by groups
        self.allowed_groups = os.environ.get('AUTHENTIK_ALLOWED_GROUPS', '').split(',')
        self.allowed_groups = [g.strip() for g in self.allowed_groups if g.strip()]

        # Validate required configuration
        if not all([self.base_url, self.client_id, self.client_secret, self.slug]):
            raise ValueError("Missing required Authentik configuration")

        # Initialize OAuth
        self.oauth = OAuth(app)

        # Register Authentik as OAuth provider
        # IMPORTANT: Use manual endpoint configuration to avoid JWKS validation issues
        # (Some Authentik configs use HS256 with empty JWKS)
        self.authentik = self.oauth.register(
            name='authentik',
            client_id=self.client_id,
            client_secret=self.client_secret,
            authorize_url=f'{self.base_url}/application/o/authorize/',
            access_token_url=f'{self.base_url}/application/o/token/',
            userinfo_endpoint=f'{self.base_url}/application/o/userinfo/',
            client_kwargs={
                'scope': 'openid email profile',
                'code_challenge_method': 'S256',  # Enable PKCE for better security
            }
        )

        # Session configuration
        session_hours = int(os.environ.get('SESSION_LIFETIME_HOURS', '24'))
        app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=session_hours)

        print(f"✅ Authentication ENABLED - {self.base_url}")
        if self.allowed_groups:
            print(f"   Restricted to groups: {', '.join(self.allowed_groups)}")

    def login_required(self, f):
        """Decorator to protect routes requiring authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # If auth is disabled, allow access
            if not self.enabled:
                return f(*args, **kwargs)

            # Check if user is logged in
            if 'user' not in session:
                # Save the original URL to redirect after login
                session['next'] = request.url
                return redirect(url_for('login'))

            # Check group restrictions (if configured)
            if self.allowed_groups:
                user_groups = session.get('user', {}).get('groups', [])
                if not any(group in self.allowed_groups for group in user_groups):
                    return jsonify({
                        'error': 'Access denied',
                        'message': 'You do not have permission to access this resource'
                    }), 403

            return f(*args, **kwargs)
        return decorated_function

    def get_user_info(self):
        """Get current user information from session"""
        return session.get('user', None)

    def is_authenticated(self):
        """Check if user is currently authenticated"""
        return 'user' in session and self.enabled
```

#### Integración en tu aplicación Flask

```python
from flask import Flask
from auth import AuthentikAuth

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production')

# Initialize authentication
auth = AuthentikAuth(app)

# Example: Protected route
@app.route('/')
@auth.login_required
def index():
    user = auth.get_user_info()
    return f"Hello {user['name']}!"

# Example: Public route
@app.route('/public')
def public():
    return "This page is accessible to everyone"
```

---

### 2. Configuración Web Automática

Permite a los usuarios configurar Authentik desde un wizard web, ideal para plataformas cloud donde no tienen acceso SSH.

#### `web_setup.py` - Auto-configuración vía Web

```python
#!/usr/bin/env python3
"""
Web-based Authentik auto-configuration
Creates OAuth2 provider and application via Authentik API
"""

import requests
import secrets
import os


class WebAuthentikSetup:
    """Handles web-based Authentik configuration"""

    def __init__(self, authentik_url, api_token, app_url, app_name="My Application"):
        self.base_url = authentik_url.rstrip('/')
        self.api_token = api_token
        self.app_url = app_url.rstrip('/')
        self.app_name = app_name
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }

    def api_request(self, method, endpoint, data=None):
        """Make API request to Authentik"""
        url = f"{self.base_url}/api/v3/{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.text
            return {'error': f'{e.response.status_code} {e.response.reason}', 'detail': error_detail}
        except Exception as e:
            return {'error': str(e)}

    def test_connection(self):
        """Test API connection and token validity"""
        result = self.api_request('GET', 'root/config/')
        if 'error' not in result:
            return {'success': True, 'version': result.get('version', 'unknown')}
        return {'success': False, 'error': result['error']}

    def get_default_flow(self, flow_type):
        """Get default flow by designation"""
        flows = self.api_request('GET', f'flows/instances/?designation={flow_type}')
        if flows and 'results' in flows and len(flows['results']) > 0:
            return flows['results'][0]['pk']
        return None

    def provider_exists(self):
        """Check if provider already exists"""
        providers = self.api_request('GET', f'providers/oauth2/?name={self.app_name}')
        if providers and 'results' in providers and len(providers['results']) > 0:
            return providers['results'][0]
        return None

    def application_exists(self):
        """Check if application already exists"""
        apps = self.api_request('GET', f'core/applications/?name={self.app_name}')
        if apps and 'results' in apps and len(apps['results']) > 0:
            return apps['results'][0]
        return None

    def create_oauth_provider(self):
        """Create OAuth2 provider in Authentik"""
        # Check if already exists
        existing = self.provider_exists()
        if existing:
            return {
                'success': True,
                'client_id': existing['client_id'],
                'client_secret': existing['client_secret'],
                'provider_id': existing['pk'],
                'message': 'Provider already exists'
            }

        # Get required flows
        auth_flow = self.get_default_flow('authentication')
        invalidation_flow = self.get_default_flow('invalidation')

        if not auth_flow:
            return {'success': False, 'error': 'No authentication flow found'}

        if not invalidation_flow:
            invalidation_flow = auth_flow  # Fallback

        # Create provider with Authentik 2024.8+ compatible format
        provider_data = {
            'name': self.app_name,
            'authorization_flow': auth_flow,
            'invalidation_flow': invalidation_flow,
            'client_type': 'confidential',
            'redirect_uris': [
                {
                    'matching_mode': 'strict',
                    'url': f"{self.app_url}/callback"
                }
            ],
            'sub_mode': 'hashed_user_id',
            'include_claims_in_id_token': True,
        }

        provider = self.api_request('POST', 'providers/oauth2/', provider_data)

        if provider and 'error' not in provider:
            return {
                'success': True,
                'client_id': provider['client_id'],
                'client_secret': provider['client_secret'],
                'provider_id': provider['pk'],
                'message': 'Provider created successfully'
            }

        return {
            'success': False,
            'error': f"Provider creation failed: {provider.get('error', 'Unknown error')}",
            'detail': provider.get('detail', '')
        }

    def create_application(self, provider_id, slug=None):
        """Create application in Authentik"""
        # Check if already exists
        existing = self.application_exists()
        if existing:
            return {
                'success': True,
                'slug': existing['slug'],
                'message': 'Application already exists'
            }

        # Generate slug if not provided
        if not slug:
            slug = self.app_name.lower().replace(' ', '-').replace('_', '-')

        app_data = {
            'name': self.app_name,
            'slug': slug,
            'provider': provider_id,
            'meta_launch_url': self.app_url,
            'policy_engine_mode': 'any',
        }

        app = self.api_request('POST', 'core/applications/', app_data)

        if app and 'error' not in app:
            return {
                'success': True,
                'slug': app['slug'],
                'message': 'Application created successfully'
            }

        return {
            'success': False,
            'error': f"Application creation failed: {app.get('error', 'Unknown error')}"
        }

    def configure(self):
        """Run full configuration process"""
        # Test connection
        connection = self.test_connection()
        if not connection['success']:
            return {
                'success': False,
                'step': 'connection',
                'error': f"Failed to connect: {connection['error']}"
            }

        # Create provider
        provider_result = self.create_oauth_provider()
        if not provider_result['success']:
            return {
                'success': False,
                'step': 'provider',
                'error': provider_result['error'],
                'detail': provider_result.get('detail', '')
            }

        # Create application
        app_result = self.create_application(provider_result['provider_id'])
        if not app_result['success']:
            return {
                'success': False,
                'step': 'application',
                'error': app_result['error']
            }

        # Generate SECRET_KEY if not exists
        secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

        # Return configuration
        return {
            'success': True,
            'config': {
                'ENABLE_AUTH': 'true',
                'AUTHENTIK_BASE_URL': self.base_url,
                'AUTHENTIK_CLIENT_ID': provider_result['client_id'],
                'AUTHENTIK_CLIENT_SECRET': provider_result['client_secret'],
                'AUTHENTIK_REDIRECT_URI': f"{self.app_url}/callback",
                'SECRET_KEY': secret_key
            },
            'provider': provider_result['message'],
            'application': app_result['message']
        }

    def save_env_file(self, config):
        """Save configuration to .env file"""
        try:
            with open('.env', 'w') as f:
                f.write("# Auto-generated by Authentik Setup Wizard\n")
                f.write(f"# Generated at: {datetime.now().isoformat()}\n\n")
                for key, value in config.items():
                    f.write(f"{key}={value}\n")
            return True
        except Exception as e:
            return False
```

#### Rutas Flask para el Wizard

```python
from flask import render_template, request, jsonify
from web_setup import WebAuthentikSetup

@app.route('/setup')
def setup_page():
    """Show setup wizard page"""
    # Check if already configured
    already_configured = auth.enabled
    return render_template('setup.html',
                         already_configured=already_configured)

@app.route('/setup/configure', methods=['POST'])
def setup_configure():
    """Handle setup wizard form submission"""
    try:
        data = request.json

        # Create setup instance
        setup = WebAuthentikSetup(
            authentik_url=data['authentik_url'],
            api_token=data['api_token'],
            app_url=data['app_url'],
            app_name=data.get('app_name', 'My Application')
        )

        # Run configuration
        result = setup.configure()

        if result['success']:
            # Save to .env file
            setup.save_env_file(result['config'])

            return jsonify({
                'success': True,
                'message': 'Configuration completed successfully',
                'config': result['config']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'detail': result.get('detail', '')
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
```

---

### 3. Rutas y Callbacks

Implementa las rutas OAuth2 necesarias:

```python
from flask import session, redirect, url_for

@app.route('/login')
def login():
    """Initiate OAuth2 login flow"""
    if not auth.enabled:
        return redirect(url_for('index'))

    redirect_uri = url_for('callback', _external=True)
    return auth.authentik.authorize_redirect(redirect_uri)


@app.route('/callback')
def callback():
    """OAuth2 callback endpoint"""
    if not auth.enabled:
        return redirect(url_for('index'))

    try:
        # Exchange code for token (without parsing id_token)
        # Use fetch_token() to avoid JWKS validation issues with HS256
        token = auth.authentik.fetch_token(
            auth.authentik.access_token_url,
            grant_type='authorization_code',
            authorization_response=request.url,
            redirect_uri=url_for('callback', _external=True)
        )

        # Get user info from userinfo endpoint
        user_info = auth.authentik.userinfo(token=token)

        # Store in session
        session['user'] = {
            'sub': user_info.get('sub'),
            'email': user_info.get('email', ''),
            'name': user_info.get('name', user_info.get('preferred_username', 'User')),
            'groups': user_info.get('groups', [])
        }
        session.permanent = True

        # Redirect to original URL or home
        next_url = session.pop('next', url_for('index'))
        return redirect(next_url)

    except Exception as e:
        return f"Authentication failed: {str(e)}", 400


@app.route('/logout')
def logout():
    """Logout user and clear session"""
    session.clear()

    if auth.enabled:
        # Redirect to Authentik logout
        logout_url = f"{auth.base_url}/application/o/{auth.client_id}/end-session/"
        return redirect(logout_url)

    return redirect(url_for('index'))


@app.route('/user/info')
@auth.login_required
def user_info():
    """Get current user information (API endpoint)"""
    return jsonify(auth.get_user_info())
```

---

### 4. Protección de Rutas

Usa el decorador `@auth.login_required` para proteger rutas:

```python
# Ruta protegida - requiere autenticación
@app.route('/dashboard')
@auth.login_required
def dashboard():
    user = auth.get_user_info()
    return render_template('dashboard.html', user=user)


# Ruta pública - no requiere autenticación
@app.route('/about')
def about():
    return render_template('about.html')


# Ruta con verificación manual
@app.route('/api/data')
def api_data():
    if auth.enabled and not auth.is_authenticated():
        return jsonify({'error': 'Authentication required'}), 401

    return jsonify({'data': 'sensitive information'})
```

---

## Variables de Entorno

### Archivo `.env.example`

Crea una plantilla de configuración:

```bash
# =============================================================================
# AUTHENTICATION CONFIGURATION
# =============================================================================

# Enable/disable authentication
# Set to 'true' to enable, 'false' to disable
ENABLE_AUTH=false

# =============================================================================
# AUTHENTIK OAUTH2/OIDC CONFIGURATION
# =============================================================================

# Authentik Server URL
# Example: https://auth.example.com
AUTHENTIK_BASE_URL=https://authentik.example.com

# OAuth2 Client Credentials
# Get these after creating an OAuth2 provider in Authentik
AUTHENTIK_CLIENT_ID=your-client-id-here
AUTHENTIK_CLIENT_SECRET=your-client-secret-here

# Application Slug
# The URL-friendly name of your application in Authentik
# Example: my-app, msg-converter, etc.
# Find in Authentik: Applications → your app → Slug field
AUTHENTIK_SLUG=your-app-slug-here

# Callback URL
# Must match the redirect URI configured in Authentik
# For development: http://localhost:5000/callback
# For production: https://your-domain.com/callback
AUTHENTIK_REDIRECT_URI=http://localhost:5000/callback

# =============================================================================
# AUTHENTIK API TOKEN (for auto-configuration)
# =============================================================================

# API Token for automatic setup via web wizard
# Create in Authentik: Directory → Tokens
# Required scopes: view, write (for Providers and Applications)
AUTHENTIK_API_TOKEN=your-api-token-here

# =============================================================================
# OPTIONAL CONFIGURATION
# =============================================================================

# Allowed Groups (comma-separated)
# Leave empty to allow all authenticated users
# Example: admin,developers,editors
AUTHENTIK_ALLOWED_GROUPS=

# Session Lifetime (in hours)
# Default: 24 hours
SESSION_LIFETIME_HOURS=24

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

# Flask Secret Key
# IMPORTANT: Generate a random string for production!
# Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=change-this-to-a-random-string-in-production
```

---

## Despliegue en Producción

### Render.com

1. **Configura las variables de entorno** en Dashboard → Environment:
   ```
   ENABLE_AUTH=true
   AUTHENTIK_BASE_URL=https://auth.example.com
   AUTHENTIK_CLIENT_ID=your-client-id
   AUTHENTIK_CLIENT_SECRET=your-client-secret
   AUTHENTIK_SLUG=your-app-slug
   AUTHENTIK_REDIRECT_URI=https://your-app.onrender.com/callback
   SECRET_KEY=<generated-secret-key>
   ```

2. **Opcional**: Configura `AUTHENTIK_API_TOKEN` si quieres usar el wizard web

3. **Guarda** - Render redespleará automáticamente

### Railway.app

Similar a Render, agrega las variables en Settings → Variables

### Vercel

En Project Settings → Environment Variables, agrega todas las variables necesarias.

### Docker

Crea un archivo `.env` y usa docker-compose:

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
    env_file:
      - .env
    environment:
      - ENABLE_AUTH=true
```

### Heroku

```bash
heroku config:set ENABLE_AUTH=true
heroku config:set AUTHENTIK_BASE_URL=https://auth.example.com
heroku config:set AUTHENTIK_CLIENT_ID=your-client-id
heroku config:set AUTHENTIK_CLIENT_SECRET=your-client-secret
heroku config:set AUTHENTIK_SLUG=your-app-slug
heroku config:set AUTHENTIK_REDIRECT_URI=https://your-app.herokuapp.com/callback
heroku config:set SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

---

## Troubleshooting

### Problema: "Authentication is DISABLED" en producción

**Causa**: Variable `ENABLE_AUTH` no está configurada o es `false`

**Solución**:
```bash
# Verifica que esté en true (no "True" ni "TRUE")
ENABLE_AUTH=true
```

### Problema: "404 Not Found" en OIDC configuration endpoint

**Causa**: La URL de OIDC discovery usa el `client_id` en lugar del `slug` de la aplicación

**Error típico**:
```
404 Client Error: Not Found for url: https://auth.example.com/application/o/0EQttwGxHfo2S0uSy7IhtV8qYPWKCkLIG56quYxp/.well-known/openid-configuration
```

**Solución**:
1. La URL correcta debe usar el **slug** de la aplicación, no el `client_id`
2. Encuentra el slug en Authentik: Applications → tu aplicación → campo "Slug"
3. Configura la variable de entorno:
   ```bash
   AUTHENTIK_SLUG=msg-eml-converter  # Usa tu slug real
   ```
4. Verifica que el código use el slug en la URL:
   ```python
   server_metadata_url=f'{base_url}/application/o/{slug}/.well-known/openid-configuration'
   ```
   **NO uses**: `server_metadata_url=f'{base_url}/application/o/{client_id}/.well-known/openid-configuration'`

### Problema: "redirect_uri_mismatch"

**Causa**: El callback URI en Authentik no coincide con el configurado

**Solución**:
1. Ve a Authentik → Applications → tu Provider
2. Verifica que `redirect_uris` contenga exactamente: `https://your-app.com/callback`
3. Asegúrate que `AUTHENTIK_REDIRECT_URI` tenga el mismo valor

### Problema: "Invalid key set format"

**Causa**: Error al parsear el JWKS (JSON Web Key Set) de Authentik durante la validación del ID token

**Error típico**:
```json
{
  "error": "Authentication failed",
  "message": "Invalid key set format"
}
```

**Causas comunes**:
1. **JWKS vacío con algoritmo HS256** (causa más común)
2. Versión antigua de Authlib (< 1.6.0)
3. Problemas con la configuración del OAuth2 provider en Authentik
4. JWKS endpoint devuelve formato inesperado
5. Nonce verification issues

**Diagnóstico rápido**:
```bash
# Verifica si JWKS está vacío:
curl https://your-authentik.com/application/o/your-slug/jwks/
# Si devuelve {} (vacío), tienes el problema #1
```

**Solución**:

1. **Actualizar Authlib** (solución más efectiva):
   ```bash
   pip install --upgrade authlib>=1.6.0 cryptography>=41.0.0
   ```

2. **Verificar requirements.txt**:
   ```txt
   Authlib>=1.6.0
   cryptography>=41.0.0
   ```

3. **Agregar configuración PKCE** en el registro OAuth:
   ```python
   client_kwargs={
       'scope': 'openid email profile',
       'code_challenge_method': 'S256',  # Enable PKCE
   },
   authorize_params={'nonce': None}  # Disable nonce if problematic
   ```

4. **Verificar endpoint JWKS** manualmente:
   ```bash
   curl https://your-authentik.com/application/o/your-slug/.well-known/openid-configuration
   ```

   Debe devolver JSON válido con `jwks_uri` apuntando a:
   ```
   https://your-authentik.com/application/o/your-slug/jwks/
   ```

5. **Verificar JWKS keys**:
   ```bash
   curl https://your-authentik.com/application/o/your-slug/jwks/
   ```

   Debe devolver:
   ```json
   {
     "keys": [
       {
         "kty": "RSA",
         "alg": "RS256",
         "use": "sig",
         "kid": "...",
         "n": "...",
         "e": "AQAB"
       }
     ]
   }
   ```

6. **Si el problema persiste**, verifica la configuración del provider en Authentik:
   - Authentik → Applications → Tu aplicación → Provider
   - Asegúrate que "Signing Key" esté configurada
   - Verifica que "Subject mode" sea `hashed_user_id` o `user_username`

7. **SOLUCIÓN DEFINITIVA para JWKS vacío con HS256**:

   Si tu endpoint JWKS devuelve `{}` (vacío) y usas algoritmo HS256, necesitas dos cambios:

   **a) Configurar manualmente los endpoints** (sin `server_metadata_url`):
   ```python
   # ❌ NO uses esto si JWKS está vacío:
   server_metadata_url=f'{base_url}/application/o/{slug}/.well-known/openid-configuration'

   # ✅ USA esto en su lugar:
   authorize_url=f'{base_url}/application/o/authorize/',
   access_token_url=f'{base_url}/application/o/token/',
   userinfo_endpoint=f'{base_url}/application/o/userinfo/',
   ```

   **b) Usar `fetch_token()` en lugar de `authorize_access_token()`** en el callback:
   ```python
   # ❌ NO uses esto (intenta parsear id_token):
   token = oauth_client.authorize_access_token()

   # ✅ USA esto (solo obtiene access token):
   token = oauth_client.fetch_token(
       oauth_client.access_token_url,
       grant_type='authorization_code',
       authorization_response=request.url,
       redirect_uri=redirect_uri
   )
   ```

   **Por qué**:
   - `server_metadata_url` hace que Authlib descargue configuración OIDC e intente validar el id_token con JWKS
   - `authorize_access_token()` también intenta parsear y validar el id_token automáticamente
   - Con JWKS vacío (HS256), ambos fallan con "Invalid key set format" o "Missing jwks_uri"
   - La configuración manual + `fetch_token()` evita completamente la validación de id_token
   - Solo usa el userinfo endpoint que siempre funciona

### Problema: "Invalid client_id or client_secret"

**Causa**: Credenciales incorrectas o provider mal configurado

**Solución**:
1. Ve a Authentik → Applications → tu aplicación → Provider
2. Copia el Client ID (no el slug)
3. Haz clic en "Show secret" y copia el Client Secret
4. Actualiza las variables de entorno

### Problema: "Access denied - insufficient permissions"

**Causa**: Usuario no pertenece a los grupos permitidos

**Solución**:
- **Opción 1**: Agrega al usuario a los grupos requeridos en Authentik
- **Opción 2**: Elimina la restricción de grupos: `AUTHENTIK_ALLOWED_GROUPS=` (vacío)

### Problema: Error 400 al crear provider con API

**Causa**: Versión Authentik 2024.8+ requiere formato diferente para `redirect_uris`

**Solución**: Usa el formato de objetos:
```python
'redirect_uris': [
    {
        'matching_mode': 'strict',
        'url': 'https://your-app.com/callback'
    }
]
```

En lugar de lista de strings:
```python
'redirect_uris': ['https://your-app.com/callback']  # ❌ No funciona en 2024.8+
```

### Problema: Sesión expira muy rápido

**Causa**: `SESSION_LIFETIME_HOURS` muy corto o no configurado

**Solución**:
```bash
# Aumentar duración de sesión (ej: 7 días)
SESSION_LIFETIME_HOURS=168
```

---

## Consideraciones de Seguridad

### 🔐 Mejores Prácticas

1. **SECRET_KEY**: Usa claves aleatorias largas (mínimo 32 bytes)
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **HTTPS Obligatorio**: Siempre usa HTTPS en producción
   - OAuth2 requiere conexiones seguras
   - Los tokens se transmiten en URLs

3. **Token de API**: Limita los permisos al mínimo necesario
   - Solo `view` y `write` para Providers y Applications
   - Considera crear tokens de un solo uso para setup

4. **Grupos de Acceso**: Usa `AUTHENTIK_ALLOWED_GROUPS` para limitar acceso
   ```bash
   AUTHENTIK_ALLOWED_GROUPS=admin,developers
   ```

5. **Validación de Redirect URIs**: Authentik valida automáticamente
   - Usa `matching_mode: strict` en producción
   - No uses wildcards en producción

6. **Sesiones Seguras**: Configura Flask correctamente
   ```python
   app.config['SESSION_COOKIE_SECURE'] = True  # Solo HTTPS
   app.config['SESSION_COOKIE_HTTPONLY'] = True  # No accesible desde JS
   app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Protección CSRF
   ```

7. **Rate Limiting**: Implementa límites en `/login` y `/callback`

8. **Logging**: Registra intentos de acceso y errores
   ```python
   import logging
   logging.info(f"User {user['email']} logged in from {request.remote_addr}")
   ```

### 🚫 Evitar

- ❌ No expongas `client_secret` en el código fuente
- ❌ No uses HTTP en producción
- ❌ No almacenes tokens en localStorage (usa sesiones server-side)
- ❌ No deshabilites validación de certificados SSL
- ❌ No uses `SECRET_KEY` por defecto en producción

---

## Estructura de Archivos Recomendada

```
my-app/
├── app.py                          # Aplicación principal
├── auth.py                         # Módulo de autenticación
├── web_setup.py                    # Auto-configuración web
├── requirements.txt                # Dependencias Python
├── .env.example                    # Plantilla de configuración
├── .env                            # Configuración real (git-ignored)
├── .gitignore                      # Ignorar .env y secrets
├── templates/
│   ├── base.html                   # Template base
│   ├── index.html                  # Página principal
│   ├── setup.html                  # Wizard de configuración
│   └── dashboard.html              # Dashboard protegido
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── docs/
    └── AUTHENTIK_INTEGRATION_GUIDE.md  # Esta guía
```

---

## Dependencias Python

```txt
# requirements.txt
Flask>=3.0.0
Authlib>=1.6.0
requests>=2.31.0
python-dotenv>=1.0.0
cryptography>=41.0.0
```

**Nota importante**: Asegúrate de usar Authlib 1.6.0 o superior para evitar problemas con el parseo de JWKS.

Instalar:
```bash
pip install -r requirements.txt
```

---

## Ejemplo Completo Mínimo

Aquí hay un ejemplo mínimo funcional:

```python
# app.py - Aplicación completa mínima
import os
from flask import Flask, render_template_string, session, redirect, url_for
from authlib.integrations.flask_client import OAuth
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

# OAuth setup
oauth = OAuth(app)
authentik = oauth.register(
    name='authentik',
    client_id=os.getenv('AUTHENTIK_CLIENT_ID'),
    client_secret=os.getenv('AUTHENTIK_CLIENT_SECRET'),
    authorize_url=f"{os.getenv('AUTHENTIK_BASE_URL')}/application/o/authorize/",
    access_token_url=f"{os.getenv('AUTHENTIK_BASE_URL')}/application/o/token/",
    userinfo_endpoint=f"{os.getenv('AUTHENTIK_BASE_URL')}/application/o/userinfo/",
    client_kwargs={
        'scope': 'openid email profile',
        'code_challenge_method': 'S256'
    }
)

# Decorator
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# Routes
@app.route('/')
@login_required
def index():
    return f"<h1>Hello {session['user']['name']}!</h1><a href='/logout'>Logout</a>"

@app.route('/login')
def login():
    return authentik.authorize_redirect(url_for('callback', _external=True))

@app.route('/callback')
def callback():
    # Use fetch_token to avoid JWKS validation with HS256
    token = authentik.fetch_token(
        authentik.access_token_url,
        grant_type='authorization_code',
        authorization_response=request.url,
        redirect_uri=url_for('callback', _external=True)
    )
    # Get user info from userinfo endpoint
    user = authentik.userinfo(token=token)
    session['user'] = {'name': user.get('name', 'User'), 'email': user.get('email')}
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(f"{os.getenv('AUTHENTIK_BASE_URL')}/application/o/{os.getenv('AUTHENTIK_CLIENT_ID')}/end-session/")

if __name__ == '__main__':
    app.run(debug=True)
```

---

## Referencias y Recursos

- **Documentación Authentik**: https://goauthentik.io/docs/
- **OAuth2 RFC**: https://datatracker.ietf.org/doc/html/rfc6749
- **OIDC Specification**: https://openid.net/specs/openid-connect-core-1_0.html
- **Authlib Docs**: https://docs.authlib.org/
- **Flask Security Best Practices**: https://flask.palletsprojects.com/en/stable/security/

---

## Licencia y Contribuciones

Esta guía es de código abierto y puede ser adaptada libremente para tus proyectos.

Para contribuir o reportar errores, visita el repositorio del proyecto.

---

**¿Preguntas o problemas?** Revisa la sección de [Troubleshooting](#troubleshooting) o consulta la documentación oficial de Authentik.

**Última actualización**: 2025-11-21
**Versión de la guía**: 1.0
**Compatible con**: Authentik 2024.8+
