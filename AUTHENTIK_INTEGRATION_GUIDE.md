# Guía Completa de Integración de Authentik OAuth2/OIDC

Esta guía proporciona una plantilla completa y probada en producción para integrar autenticación Authentik OAuth2/OIDC en aplicaciones web. Incluye soluciones a todos los problemas comunes encontrados durante implementaciones reales.

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
  - [Problemas de Configuración](#problemas-de-configuración)
  - [Problemas de JWKS/Tokens](#problemas-de-jwkstokens)
  - [Problemas de Sesión](#problemas-de-sesión)
  - [Problemas de PKCE](#problemas-de-pkce)
- [Consideraciones de Seguridad](#consideraciones-de-seguridad)
- [Referencias y Recursos](#referencias-y-recursos)

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
4. **Middleware ProxyFix** si despliegas detrás de un proxy reverso (Render, Heroku, etc.)

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
       │                       │   (access + id_token)  │
       │  6. Acceso permitido  │                        │
       │◀──────────────────────│                        │
       └───────────────────────┘                        │
```

### Flujo OAuth2/OIDC:

1. **Usuario intenta acceder** a una ruta protegida
2. **Aplicación redirige** a Authentik para login
3. **Usuario se autentica** en Authentik (usuario/contraseña, MFA, etc.)
4. **Authentik redirige** con código de autorización
5. **Aplicación intercambia** código por access_token e id_token
6. **Aplicación extrae** información del usuario del id_token
7. **Usuario accede** a la aplicación con sesión activa

---

## Implementación Paso a Paso

### 1. Módulo de Autenticación

Crea un módulo que maneje la lógica de OAuth2/OIDC. Este código está probado en producción y resuelve todos los problemas comunes.

#### `auth.py` - Módulo Principal (Producción-Ready)

```python
#!/usr/bin/env python3
"""
Authentication module for Authentik OAuth2/OIDC
Tested with Authentik 2024.8+ and Flask 3.0+
Includes solutions for common issues: PKCE, JWKS, session size, etc.
"""

import os
import json
import base64
import requests
from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from authlib.integrations.flask_client import OAuth
from datetime import datetime, timedelta


class AuthentikAuth:
    """Authentik OAuth2/OIDC authentication handler"""

    def __init__(self, app):
        self.app = app
        self.enabled = os.environ.get('ENABLE_AUTH', 'false').lower() == 'true'

        if not self.enabled:
            print("⚠️  Authentication is DISABLED")
            return

        # Configuration
        self.base_url = os.environ.get('AUTHENTIK_BASE_URL', '').rstrip('/')
        self.client_id = os.environ.get('AUTHENTIK_CLIENT_ID', '')
        self.client_secret = os.environ.get('AUTHENTIK_CLIENT_SECRET', '')
        self.redirect_uri = os.environ.get('AUTHENTIK_REDIRECT_URI', '')
        self.slug = os.environ.get('AUTHENTIK_SLUG', '')

        # Optional: restrict access by groups
        self.allowed_groups = os.environ.get('AUTHENTIK_ALLOWED_GROUPS', '').split(',')
        self.allowed_groups = [g.strip() for g in self.allowed_groups if g.strip()]

        if not all([self.base_url, self.client_id, self.client_secret, self.redirect_uri, self.slug]):
            raise ValueError(
                "Missing Authentik configuration. Please set: "
                "AUTHENTIK_BASE_URL, AUTHENTIK_CLIENT_ID, AUTHENTIK_CLIENT_SECRET, "
                "AUTHENTIK_REDIRECT_URI, AUTHENTIK_SLUG"
            )

        # Initialize OAuth
        self.oauth = OAuth(app)

        # Register Authentik provider
        # IMPORTANT: Manual endpoint configuration to avoid JWKS validation issues with HS256
        # IMPORTANT: PKCE disabled - manual token exchange doesn't support PKCE verification
        self.authentik = self.oauth.register(
            name='authentik',
            client_id=self.client_id,
            client_secret=self.client_secret,
            # Manual endpoints (not server_metadata_url) to avoid JWKS auto-fetching
            authorize_url=f'{self.base_url}/application/o/authorize/',
            access_token_url=f'{self.base_url}/application/o/token/',
            client_kwargs={
                'scope': 'openid email profile',
                # PKCE disabled - causes "invalid_grant" with manual token exchange
                # If you use oauth.authorize_access_token(), you can enable PKCE:
                # 'code_challenge_method': 'S256',
            }
        )

        print(f"✅ Authentication ENABLED - Authentik URL: {self.base_url}")
        if self.allowed_groups:
            print(f"   🔒 Access restricted to groups: {', '.join(self.allowed_groups)}")

    def login_required(self, f):
        """Decorator to require authentication for a route"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.enabled:
                return f(*args, **kwargs)

            if not self.is_authenticated():
                session['next'] = request.url
                return redirect(url_for('login'))

            # Check session expiration
            if self.is_session_expired():
                session.clear()
                session['next'] = request.url
                return redirect(url_for('login'))

            return f(*args, **kwargs)
        return decorated_function

    def is_authenticated(self):
        """Check if user is authenticated"""
        return 'user' in session and session.get('user') is not None

    def is_session_expired(self):
        """Check if session has expired"""
        if 'expires_at' not in session:
            return True

        expires_at = datetime.fromisoformat(session['expires_at'])
        return datetime.now() >= expires_at

    def check_group_membership(self, user_info):
        """Check if user belongs to allowed groups"""
        if not self.allowed_groups:
            return True  # No group restrictions

        user_groups = user_info.get('groups', [])
        return any(group in self.allowed_groups for group in user_groups)

    def get_current_user(self):
        """Get current user info from session"""
        return session.get('user', None)


def init_auth_routes(app, auth):
    """Initialize authentication routes"""

    @app.route('/login')
    def login():
        """Initiate OAuth2 login flow"""
        if not auth.enabled:
            return redirect(url_for('index'))

        # Use url_for to generate callback URL dynamically
        redirect_uri = url_for('callback', _external=True)
        return auth.authentik.authorize_redirect(redirect_uri)

    @app.route('/callback')
    def callback():
        """OAuth2 callback handler - handles token exchange and user info extraction"""
        if not auth.enabled:
            return redirect(url_for('index'))

        try:
            # Get authorization code
            code = request.args.get('code')
            if not code:
                return jsonify({
                    'error': 'No authorization code',
                    'message': 'Authorization code not found in callback URL'
                }), 400

            # Exchange authorization code for access token using requests directly
            # This avoids Authlib's automatic id_token parsing which fails with empty JWKS (HS256)
            # IMPORTANT: redirect_uri must match exactly what was used in authorize step
            redirect_uri_used = url_for('callback', _external=True)

            token_response = requests.post(
                f'{auth.base_url}/application/o/token/',
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': redirect_uri_used,
                    'client_id': auth.client_id,
                    'client_secret': auth.client_secret,
                    # Note: scope is optional in token exchange, already set in authorize
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            if token_response.status_code != 200:
                error_detail = token_response.json() if token_response.text else {}
                return jsonify({
                    'error': 'Token exchange failed',
                    'message': f'Failed to exchange authorization code: {error_detail.get("error_description", "Unknown error")}',
                    'redirect_uri_used': redirect_uri_used,
                    'status_code': token_response.status_code
                }), token_response.status_code

            token = token_response.json()

            # Get user info - try id_token first (OIDC), fallback to userinfo endpoint
            # This solves the "insufficient_scope" problem
            user_info = None

            if 'id_token' in token:
                # Parse id_token to get user info (OIDC standard)
                # ID tokens are JWT but we can decode without verification since we got it
                # directly from the token endpoint over HTTPS with client authentication
                try:
                    # JWT format: header.payload.signature
                    id_token_parts = token['id_token'].split('.')
                    if len(id_token_parts) >= 2:
                        # Decode payload (add padding if needed)
                        payload = id_token_parts[1]
                        payload += '=' * (4 - len(payload) % 4)  # Add padding
                        user_info = json.loads(base64.urlsafe_b64decode(payload))
                        print(f"✅ Successfully decoded id_token for user: {user_info.get('email', 'unknown')}")
                except Exception as e:
                    print(f"⚠️  Warning: Failed to decode id_token: {e}")
                    user_info = None

            # Fallback to userinfo endpoint if id_token parsing failed
            if not user_info:
                print("ℹ️  Falling back to userinfo endpoint")
                userinfo_url = f'{auth.base_url}/application/o/userinfo/'
                userinfo_response = requests.get(
                    userinfo_url,
                    headers={'Authorization': f'Bearer {token["access_token"]}'}
                )

                if userinfo_response.status_code != 200:
                    return jsonify({
                        'error': 'Failed to get user info',
                        'message': f'Both id_token parsing and userinfo endpoint failed',
                        'userinfo_status': userinfo_response.status_code,
                        'userinfo_error': userinfo_response.text
                    }), userinfo_response.status_code

                user_info = userinfo_response.json()

            # Check group membership if configured
            if auth.allowed_groups and not auth.check_group_membership(user_info):
                return jsonify({
                    'error': 'Access denied',
                    'message': 'You are not authorized to access this application. Please contact your administrator.'
                }), 403

            # Calculate session expiration
            session_lifetime = int(os.environ.get('SESSION_LIFETIME_HOURS', '24'))
            expires_at = datetime.now() + timedelta(hours=session_lifetime)

            # Store user info in session (minimal data to avoid cookie size limit of 4KB)
            # CRITICAL: Do NOT store tokens in session - they're too large and cause
            # "cookie too large" warning which makes browsers silently ignore the cookie
            session['user'] = {
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'preferred_username': user_info.get('preferred_username'),
                'groups': user_info.get('groups', [])
            }
            session['expires_at'] = expires_at.isoformat()
            session['authenticated'] = True

            # Redirect to original URL or home
            next_url = session.pop('next', None)
            return redirect(next_url or url_for('index'))

        except Exception as e:
            print(f"❌ Authentication error: {str(e)}")
            return jsonify({
                'error': 'Authentication failed',
                'message': str(e)
            }), 400

    @app.route('/logout')
    def logout():
        """Logout user and redirect to Authentik logout"""
        session.clear()

        if auth.enabled:
            # Redirect to Authentik logout endpoint
            logout_url = f"{auth.base_url}/application/o/{auth.slug}/end-session/"
            return redirect(logout_url)

        return redirect(url_for('index'))

    @app.route('/auth/status')
    def auth_status():
        """Check authentication status (API endpoint)"""
        if not auth.enabled:
            return jsonify({'authenticated': False, 'auth_enabled': False})

        return jsonify({
            'authenticated': auth.is_authenticated(),
            'auth_enabled': True,
            'user': auth.get_current_user() if auth.is_authenticated() else None
        })
```

#### Integración en tu aplicación Flask

```python
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from auth import AuthentikAuth, init_auth_routes
import os

app = Flask(__name__)

# CRITICAL: Fix for running behind proxy (Render, Heroku, Nginx, etc.)
# This ensures Flask correctly detects HTTPS protocol and generates proper URLs
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production')

# Initialize authentication
try:
    auth = AuthentikAuth(app)
    init_auth_routes(app, auth)
except Exception as e:
    print(f"Warning: Authentication initialization failed: {e}")
    print("Running without authentication")
    # Create a dummy auth object
    class DummyAuth:
        enabled = False
        def login_required(self, f):
            return f
    auth = DummyAuth()

# Example: Protected route
@app.route('/')
def index():
    if auth.enabled and not auth.is_authenticated():
        # Show welcome page with login button
        return render_template('welcome.html')

    user = auth.get_current_user() if auth.enabled else None
    return render_template('index.html', user=user)

# Example: Always protected route
@app.route('/dashboard')
@auth.login_required
def dashboard():
    user = auth.get_current_user()
    return render_template('dashboard.html', user=user)
```

---

### 2. Configuración Web Automática

Esta sección explica cómo programar una aplicación para que con un botón se autoconfigure toda la configuración de Authentik usando su API REST.

#### ¿Cómo funciona la autoconfiguración?

La autoconfiguración automatiza todos los pasos manuales de configurar Authentik:

1. **Conexión a la API** de Authentik usando un token de administrador
2. **Creación del Provider OAuth2** con todos los parámetros necesarios
3. **Creación de la Application** vinculada al provider
4. **Guardado automático** de credenciales (client_id, client_secret) en el archivo `.env`

**Ventajas**:
- ✅ Sin configuración manual en Authentik
- ✅ Sin copiar/pegar client_id y client_secret
- ✅ Configuración en 1 clic
- ✅ Menos errores de configuración
- ✅ Ideal para despliegues rápidos

#### Requisitos previos

1. **Token de API de Authentik** con permisos:
   - `authentik Core: Providers` (view, write)
   - `authentik Core: Applications` (view, write)
   - `authentik Flows: Flows` (view)

2. **Cómo crear el token**:
   - Inicia sesión en Authentik como administrador
   - Ve a **Directory → Tokens**
   - Clic en **Create**
   - Configura:
     - **Identifier**: `msg-converter-setup`
     - **User**: Tu usuario administrador
     - **Scopes**: Selecciona todos los permisos mencionados arriba
   - Guarda y **copia el token** (solo se muestra una vez)

#### Arquitectura de la autoconfiguración

```
┌──────────────┐         ┌──────────────┐         ┌─────────────┐
│   Usuario    │────────▶│  Setup Web   │────────▶│  Authentik  │
│  (Browser)   │         │  (Flask)     │         │   API       │
└──────────────┘         └──────────────┘         └─────────────┘
       │                        │                        │
       │  1. Accede /setup      │                        │
       │───────────────────────▶│                        │
       │                        │                        │
       │  2. Formulario         │                        │
       │◀───────────────────────│                        │
       │                        │                        │
       │  3. Submit config      │                        │
       │───────────────────────▶│                        │
       │                        │                        │
       │                        │  4. POST /api/v3/      │
       │                        │    providers/oauth2/   │
       │                        │───────────────────────▶│
       │                        │◀───────────────────────│
       │                        │  (client_id, secret)   │
       │                        │                        │
       │                        │  5. POST /api/v3/      │
       │                        │    core/applications/  │
       │                        │───────────────────────▶│
       │                        │◀───────────────────────│
       │                        │                        │
       │                        │  6. Save to .env       │
       │                        │  (AUTHENTIK_CLIENT_ID, │
       │                        │   AUTHENTIK_CLIENT_    │
       │                        │   SECRET)              │
       │                        │                        │
       │  7. Success + Restart  │                        │
       │◀───────────────────────│                        │
       └────────────────────────┘                        │
```

#### Implementación: Módulo de autoconfiguración

Crea un archivo `web_setup.py`:

```python
#!/usr/bin/env python3
"""
Web-based setup wizard for Authentik configuration
Automates OAuth2 provider and application creation via API
"""

import os
import requests
from dotenv import set_key


class WebAuthentikSetup:
    """Web-based Authentik setup handler"""

    def __init__(self, base_url, api_token, app_url):
        """
        Initialize setup handler

        Args:
            base_url: Authentik server URL (eg: https://auth.example.com)
            api_token: API token with provider/app creation permissions
            app_url: Your application URL (eg: https://msg-converter.com)
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.app_url = app_url.rstrip('/')
        self.app_name = "MSG to EML Converter"
        self.app_slug = "msg-eml-converter"

    def api_request(self, method, endpoint, data=None):
        """
        Make API request to Authentik

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint (eg: 'core/applications/')
            data: Request body for POST requests

        Returns:
            dict: Response JSON or error dict with 'error' key
        """
        url = f"{self.base_url}/api/v3/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=10)
            else:
                return {'error': f'Unsupported method: {method}'}

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            return {'error': 'Request timeout. Check Authentik URL and network.'}
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    # Extract detailed error messages
                    if isinstance(error_detail, dict):
                        if 'detail' in error_detail:
                            error_msg = error_detail['detail']
                        elif 'error' in error_detail:
                            error_msg = error_detail['error']
                        else:
                            # Collect all field errors
                            error_parts = []
                            for field, errors in error_detail.items():
                                if isinstance(errors, list):
                                    error_parts.append(f"{field}: {', '.join(str(e) for e in errors)}")
                                else:
                                    error_parts.append(f"{field}: {errors}")
                            if error_parts:
                                error_msg = '; '.join(error_parts)
                except:
                    error_msg = e.response.text if e.response.text else error_msg
            return {'error': error_msg}

    def validate_connection(self):
        """
        Validate connection to Authentik API

        Returns:
            dict: {'success': True} or {'error': 'message'}
        """
        result = self.api_request('GET', 'core/applications/')
        if result and 'error' not in result:
            return {'success': True}
        return result

    def get_default_flow(self, flow_type='authentication'):
        """
        Get default flow by type

        Args:
            flow_type: Flow type (authentication, invalidation, etc.)

        Returns:
            str: Flow PK (UUID) or None
        """
        flows = self.api_request('GET', 'flows/instances/')
        if flows and 'error' not in flows:
            # Find flow by type in slug or designation
            for flow in flows.get('results', []):
                slug = flow.get('slug', '').lower()
                designation = flow.get('designation', '').lower()
                if flow_type in slug or flow_type in designation:
                    return flow['pk']
            # Fallback to first available flow
            if flows.get('results'):
                return flows['results'][0]['pk']
        return None

    def create_oauth_provider(self):
        """
        Create OAuth2 provider in Authentik

        API Endpoint: POST /api/v3/providers/oauth2/

        Returns:
            dict: {'success': True, 'provider': {...}} or {'error': 'message'}
        """
        # Check if provider already exists
        providers = self.api_request('GET', 'providers/oauth2/')
        if providers and 'error' not in providers:
            for provider in providers.get('results', []):
                if provider.get('name') == self.app_name:
                    return {
                        'success': True,
                        'provider': provider,
                        'message': 'Using existing provider'
                    }

        # Get required flows
        auth_flow = self.get_default_flow('authentication')
        if not auth_flow:
            return {'error': 'Could not find authentication flow'}

        invalidation_flow = self.get_default_flow('invalidation')
        if not invalidation_flow:
            invalidation_flow = auth_flow  # Fallback

        # Create provider
        # IMPORTANT: redirect_uris format changed in Authentik 2024.8+
        provider_data = {
            'name': self.app_name,
            'authorization_flow': auth_flow,
            'invalidation_flow': invalidation_flow,
            'client_type': 'confidential',  # Confidential = server-side app with secret
            'redirect_uris': [
                {
                    'matching_mode': 'strict',  # Exact match required
                    'url': f"{self.app_url}/callback"
                }
            ],
            'sub_mode': 'hashed_user_id',  # Privacy: hash user IDs
            'include_claims_in_id_token': True,  # CRITICAL: Include user info in token
        }

        provider = self.api_request('POST', 'providers/oauth2/', provider_data)
        if provider and 'error' not in provider:
            return {
                'success': True,
                'provider': provider,
                'message': 'Provider created successfully'
            }
        return provider

    def create_application(self, provider_pk):
        """
        Create application in Authentik

        API Endpoint: POST /api/v3/core/applications/

        Args:
            provider_pk: Provider UUID (from create_oauth_provider)

        Returns:
            dict: {'success': True, 'application': {...}} or {'error': 'message'}
        """
        # Check if application already exists
        apps = self.api_request('GET', 'core/applications/')
        if apps and 'error' not in apps:
            for app in apps.get('results', []):
                if app.get('slug') == self.app_slug:
                    return {
                        'success': True,
                        'application': app,
                        'message': 'Using existing application'
                    }

        # Create application
        app_data = {
            'name': self.app_name,
            'slug': self.app_slug,
            'provider': provider_pk,  # Link to provider
            'meta_launch_url': self.app_url,  # URL to launch app
        }

        application = self.api_request('POST', 'core/applications/', app_data)
        if application and 'error' not in application:
            return {
                'success': True,
                'application': application,
                'message': 'Application created successfully'
            }
        return application

    def setup(self):
        """
        Execute full setup: validate → create provider → create app → save to .env

        Returns:
            dict: Setup result with credentials or error
        """
        # Step 1: Validate connection
        validation = self.validate_connection()
        if 'error' in validation:
            return {
                'success': False,
                'step': 'validation',
                'error': f"Connection failed: {validation['error']}"
            }

        # Step 2: Create OAuth2 provider
        provider_result = self.create_oauth_provider()
        if 'error' in provider_result:
            return {
                'success': False,
                'step': 'provider',
                'error': f"Provider creation failed: {provider_result['error']}"
            }

        provider = provider_result['provider']

        # Step 3: Create application
        app_result = self.create_application(provider['pk'])
        if 'error' in app_result:
            return {
                'success': False,
                'step': 'application',
                'error': f"Application creation failed: {app_result['error']}"
            }

        # Step 4: Save credentials to .env file
        env_file = '.env'
        if not os.path.exists(env_file):
            # Create from example if exists
            if os.path.exists('.env.example'):
                import shutil
                shutil.copy('.env.example', env_file)
            else:
                # Create minimal .env
                with open(env_file, 'w') as f:
                    f.write('')

        # Update environment variables
        set_key(env_file, 'ENABLE_AUTH', 'true')
        set_key(env_file, 'AUTHENTIK_BASE_URL', self.base_url)
        set_key(env_file, 'AUTHENTIK_CLIENT_ID', provider['client_id'])
        set_key(env_file, 'AUTHENTIK_CLIENT_SECRET', provider['client_secret'])
        set_key(env_file, 'AUTHENTIK_SLUG', self.app_slug)
        set_key(env_file, 'AUTHENTIK_REDIRECT_URI', f"{self.app_url}/callback")
        set_key(env_file, 'AUTHENTIK_API_TOKEN', self.api_token)

        return {
            'success': True,
            'client_id': provider['client_id'],
            'client_secret': provider['client_secret'][:10] + '...',  # Truncate for security
            'redirect_uri': f"{self.app_url}/callback",
            'provider_message': provider_result['message'],
            'app_message': app_result['message']
        }
```

#### Implementación: Rutas web del wizard

Agrega estas rutas a tu aplicación Flask:

```python
from flask import Flask, render_template, request, jsonify, redirect, url_for
from web_setup import WebAuthentikSetup
import os

app = Flask(__name__)

@app.route('/setup')
def setup_page():
    """Setup wizard page - shows form"""
    return render_template('setup.html')

@app.route('/api/setup', methods=['POST'])
def setup_api():
    """Setup API endpoint - processes form and configures Authentik"""
    try:
        # Get form data
        data = request.get_json()

        authentik_url = data.get('authentik_url', '').strip()
        api_token = data.get('api_token', '').strip()
        app_url = data.get('app_url', '').strip()

        # Validate required fields
        if not all([authentik_url, api_token, app_url]):
            return jsonify({
                'success': False,
                'error': 'All fields are required'
            }), 400

        # Execute setup
        setup = WebAuthentikSetup(
            base_url=authentik_url,
            api_token=api_token,
            app_url=app_url
        )

        result = setup.setup()

        if result.get('success'):
            return jsonify({
                'success': True,
                'message': 'Configuration completed successfully!',
                'client_id': result['client_id'],
                'redirect_uri': result['redirect_uri'],
                'next_step': 'Restart the application to apply changes'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'step': result.get('step', 'unknown')
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Setup failed: {str(e)}'
        }), 500
```

#### Implementación: Interfaz HTML del wizard

Crea `templates/setup.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Authentik Setup Wizard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .wizard {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
        }

        .wizard h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }

        .wizard p {
            color: #666;
            margin-bottom: 30px;
            line-height: 1.6;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            color: #333;
            font-weight: 600;
            margin-bottom: 8px;
        }

        .form-group input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }

        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }

        .form-group small {
            display: block;
            color: #999;
            margin-top: 6px;
            font-size: 12px;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 32px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }

        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .alert {
            padding: 16px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: none;
        }

        .alert.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .alert.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .alert.show {
            display: block;
        }

        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 10px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .info-box {
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 16px;
            margin-bottom: 20px;
            border-radius: 4px;
        }

        .info-box h3 {
            color: #1976D2;
            margin-bottom: 8px;
            font-size: 16px;
        }

        .info-box ol {
            margin-left: 20px;
            color: #555;
            font-size: 14px;
            line-height: 1.8;
        }
    </style>
</head>
<body>
    <div class="wizard">
        <h1>🔧 Authentik Setup Wizard</h1>
        <p>Configura automáticamente la autenticación OAuth2 con Authentik en 1 clic.</p>

        <div class="info-box">
            <h3>📋 Antes de comenzar, necesitas:</h3>
            <ol>
                <li>URL de tu instancia Authentik (ej: https://auth.example.com)</li>
                <li>Token de API con permisos de Provider y Application</li>
                <li>URL de esta aplicación (se detecta automáticamente)</li>
            </ol>
        </div>

        <div id="successAlert" class="alert success">
            <strong>✅ ¡Éxito!</strong>
            <p id="successMessage"></p>
        </div>

        <div id="errorAlert" class="alert error">
            <strong>❌ Error</strong>
            <p id="errorMessage"></p>
        </div>

        <form id="setupForm">
            <div class="form-group">
                <label for="authentik_url">URL de Authentik</label>
                <input
                    type="url"
                    id="authentik_url"
                    name="authentik_url"
                    placeholder="https://auth.example.com"
                    required
                >
                <small>URL de tu servidor Authentik (sin trailing slash)</small>
            </div>

            <div class="form-group">
                <label for="api_token">Token de API</label>
                <input
                    type="password"
                    id="api_token"
                    name="api_token"
                    placeholder="••••••••••••••••••••"
                    required
                >
                <small>Token con permisos de Provider y Application (Directory → Tokens)</small>
            </div>

            <div class="form-group">
                <label for="app_url">URL de esta aplicación</label>
                <input
                    type="url"
                    id="app_url"
                    name="app_url"
                    required
                >
                <small>URL donde corre esta aplicación (se detecta automáticamente)</small>
            </div>

            <button type="submit" class="btn" id="submitBtn">
                Configurar Authentik
            </button>
        </form>
    </div>

    <script>
        // Auto-detect application URL
        const protocol = window.location.protocol;
        const host = window.location.host;
        document.getElementById('app_url').value = `${protocol}//${host}`;

        // Form submission
        document.getElementById('setupForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const submitBtn = document.getElementById('submitBtn');
            const successAlert = document.getElementById('successAlert');
            const errorAlert = document.getElementById('errorAlert');

            // Hide alerts
            successAlert.classList.remove('show');
            errorAlert.classList.remove('show');

            // Disable button and show loading
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner"></span> Configurando...';

            try {
                const formData = {
                    authentik_url: document.getElementById('authentik_url').value.trim(),
                    api_token: document.getElementById('api_token').value.trim(),
                    app_url: document.getElementById('app_url').value.trim()
                };

                const response = await fetch('/api/setup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (result.success) {
                    // Show success
                    document.getElementById('successMessage').innerHTML = `
                        ${result.message}<br><br>
                        <strong>Client ID:</strong> ${result.client_id}<br>
                        <strong>Redirect URI:</strong> ${result.redirect_uri}<br><br>
                        <strong>Próximo paso:</strong> ${result.next_step}
                    `;
                    successAlert.classList.add('show');

                    // Clear form
                    document.getElementById('setupForm').reset();

                    // Suggest restart
                    setTimeout(() => {
                        if (confirm('¿Reiniciar la aplicación ahora para aplicar los cambios?')) {
                            // You can implement restart logic here or redirect
                            window.location.href = '/';
                        }
                    }, 2000);
                } else {
                    // Show error
                    document.getElementById('errorMessage').textContent =
                        result.error || 'Ocurrió un error desconocido';
                    errorAlert.classList.add('show');
                }
            } catch (error) {
                document.getElementById('errorMessage').textContent =
                    `Error de conexión: ${error.message}`;
                errorAlert.classList.add('show');
            } finally {
                // Re-enable button
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Configurar Authentik';
            }
        });
    </script>
</body>
</html>
```

#### Flujo de uso del wizard

1. **Usuario accede** a `https://tu-app.com/setup`
2. **Completa el formulario**:
   - URL de Authentik: `https://auth.example.com`
   - Token de API: (creado previamente en Authentik)
   - URL de la app: (auto-detectada)
3. **Clic en "Configurar Authentik"**
4. **El wizard**:
   - Valida conexión con Authentik API
   - Crea OAuth2 Provider
   - Crea Application
   - Guarda credenciales en `.env`
5. **Mensaje de éxito** con client_id
6. **Reiniciar aplicación** para aplicar cambios

#### API de Authentik utilizada

**Endpoints principales**:

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/api/v3/core/applications/` | GET | Listar aplicaciones existentes |
| `/api/v3/core/applications/` | POST | Crear nueva aplicación |
| `/api/v3/providers/oauth2/` | GET | Listar providers OAuth2 |
| `/api/v3/providers/oauth2/` | POST | Crear provider OAuth2 |
| `/api/v3/flows/instances/` | GET | Listar flows disponibles |

**Estructura de datos del Provider**:

```json
{
  "name": "MSG to EML Converter",
  "authorization_flow": "uuid-del-flow-de-autenticacion",
  "invalidation_flow": "uuid-del-flow-de-invalidacion",
  "client_type": "confidential",
  "redirect_uris": [
    {
      "matching_mode": "strict",
      "url": "https://tu-app.com/callback"
    }
  ],
  "sub_mode": "hashed_user_id",
  "include_claims_in_id_token": true
}
```

**Respuesta del Provider** (contiene las credenciales):

```json
{
  "pk": "uuid-del-provider",
  "name": "MSG to EML Converter",
  "client_id": "0EQttwGxHfo2S0uSy7IhtV8qYPWKCkLIG56quYxp",
  "client_secret": "secret-generado-automaticamente-por-authentik",
  "redirect_uris": [...],
  "include_claims_in_id_token": true,
  ...
}
```

#### Consideraciones de seguridad

**🔐 Importante**:

1. **Protege la ruta /setup**:
   ```python
   @app.route('/setup')
   def setup_page():
       # Solo permitir en desarrollo o primera configuración
       if os.path.exists('.env') and os.getenv('ENABLE_AUTH') == 'true':
           return "Setup already completed", 403
       return render_template('setup.html')
   ```

2. **No expongas el token de API**:
   - Nunca lo incluyas en código fuente
   - No lo muestres en logs
   - Guárdalo solo en `.env`

3. **Valida inputs**:
   - URL de Authentik debe ser HTTPS en producción
   - Token debe tener formato válido
   - App URL debe coincidir con el dominio real

4. **Deshabilita /setup después de configurar**:
   ```python
   # En producción, elimina o protege /setup
   if os.getenv('ENVIRONMENT') == 'production':
       @app.route('/setup')
       def setup_disabled():
           return "Setup disabled in production", 404
   ```

#### Troubleshooting del wizard

**Error: "Connection failed: 403 Forbidden"**
- **Causa**: Token de API sin permisos
- **Solución**: Verifica que el token tenga permisos de Provider y Application

**Error: "Could not find authentication flow"**
- **Causa**: No hay flows configurados en Authentik
- **Solución**: Asegúrate que Authentik tiene flows por defecto (se crean en instalación)

**Error: "redirect_uris: This field is required"**
- **Causa**: Formato incorrecto de redirect_uris (versión antigua de Authentik)
- **Solución**: Usa formato string en lugar de lista de objetos:
  ```python
  'redirect_uris': f"{self.app_url}/callback"  # Para Authentik < 2024.8
  ```

**Error: "Provider created but credentials not saved"**
- **Causa**: Permisos de escritura en `.env`
- **Solución**: Verifica permisos del archivo: `chmod 644 .env`

#### Alternativa: Script CLI

Si prefieres un script de línea de comandos en lugar de interfaz web, puedes usar:

```bash
python authentik_auto_setup.py
```

Este script hace lo mismo pero interactivo en la terminal.

---

### 3. Rutas y Callbacks

Las rutas están incluidas en el módulo `auth.py` mediante la función `init_auth_routes()`. Ver sección anterior.

---

### 4. Protección de Rutas

```python
# Ruta protegida - requiere autenticación
@app.route('/dashboard')
@auth.login_required
def dashboard():
    user = auth.get_current_user()
    return render_template('dashboard.html', user=user)

# Ruta con lógica condicional
@app.route('/')
def index():
    if auth.enabled and not auth.is_authenticated():
        return render_template('welcome.html')  # Página pública con botón de login

    user = auth.get_current_user()
    return render_template('index.html', user=user)  # Contenido principal

# Ruta completamente pública
@app.route('/about')
def about():
    return render_template('about.html')

# API endpoint protegido
@app.route('/api/data')
@auth.login_required
def api_data():
    user = auth.get_current_user()
    return jsonify({
        'data': 'sensitive information',
        'user': user['email']
    })
```

---

## Variables de Entorno

### Archivo `.env` completo

```bash
# =============================================================================
# AUTHENTICATION CONFIGURATION
# =============================================================================

# Enable/disable authentication (case-sensitive: must be lowercase 'true')
ENABLE_AUTH=true

# =============================================================================
# AUTHENTIK OAUTH2/OIDC CONFIGURATION
# =============================================================================

# Authentik Server URL (without trailing slash)
# Example: https://auth.example.com
AUTHENTIK_BASE_URL=https://auth.example.com

# OAuth2 Client Credentials
# Get these from: Authentik → Applications → Your App → Provider
AUTHENTIK_CLIENT_ID=0EQttwGxHfo2S0uSy7IhtV8qYPWKCkLIG56quYxp
AUTHENTIK_CLIENT_SECRET=your-secret-here

# Application Slug
# Find in: Authentik → Applications → Your App → Slug field
# IMPORTANT: Use the slug, NOT the client_id
AUTHENTIK_SLUG=msg-eml-converter

# Callback URL
# CRITICAL: Must match EXACTLY what's configured in Authentik redirect_uris
# Development: http://localhost:5000/callback
# Production: https://your-app.com/callback
AUTHENTIK_REDIRECT_URI=https://your-app.com/callback

# =============================================================================
# OPTIONAL CONFIGURATION
# =============================================================================

# Allowed Groups (comma-separated, leave empty to allow all authenticated users)
# Example: admin,developers,editors
AUTHENTIK_ALLOWED_GROUPS=

# Session Lifetime (in hours, default: 24)
SESSION_LIFETIME_HOURS=24

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

# Flask Secret Key
# CRITICAL: Generate a random string for production!
# Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-random-secret-key-here

# =============================================================================
# AUTHENTIK API TOKEN (for auto-configuration wizard)
# =============================================================================

# API Token for automatic setup
# Create in: Authentik → Directory → Tokens
# Required scopes: authentik_core.view_provider, authentik_core.add_provider, etc.
AUTHENTIK_API_TOKEN=your-api-token-here
```

---

## Despliegue en Producción

### Consideraciones importantes

#### 1. ProxyFix Middleware

**CRÍTICO**: Si despliegas detrás de un proxy reverso (Render, Heroku, Nginx, Cloudflare), DEBES usar ProxyFix:

```python
from werkzeug.middleware.proxy_fix import ProxyFix

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
```

Sin esto, Flask generará URLs con `http://` en lugar de `https://`, causando errores de `redirect_uri_mismatch`.

#### 2. Variables de Entorno

En plataformas cloud, configura las variables en el dashboard, NO en un archivo `.env`:

**Render.com**:
- Dashboard → Environment
- Agrega cada variable individualmente
- Guarda → Render redespleará automáticamente

**Railway.app**:
- Settings → Variables
- Usa formato `KEY=value`

**Vercel**:
- Project Settings → Environment Variables
- Configura para Production, Preview, Development según necesites

**Heroku**:
```bash
heroku config:set ENABLE_AUTH=true
heroku config:set AUTHENTIK_BASE_URL=https://auth.example.com
heroku config:set AUTHENTIK_CLIENT_ID=your-client-id
heroku config:set AUTHENTIK_CLIENT_SECRET=your-secret
heroku config:set AUTHENTIK_SLUG=your-app
heroku config:set AUTHENTIK_REDIRECT_URI=https://your-app.herokuapp.com/callback
heroku config:set SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

---

## Despliegue con Docker

### Opción 1: Solo la Aplicación (Authentik externo)

Si ya tienes una instancia de Authentik funcionando en otro servidor, puedes desplegar solo la aplicación MSG Converter con Docker.

#### Paso 1: Crear archivo `.env`

Copia `.env.example` a `.env` y configura las variables:

```bash
cp .env.example .env
nano .env  # o tu editor preferido
```

Configura al menos estas variables:
```bash
# Flask
SECRET_KEY=your-random-secret-key-here  # Genera con: python3 -c "import secrets; print(secrets.token_hex(32))"

# Autenticación
ENABLE_AUTH=true

# Authentik (apuntando a tu instancia externa)
AUTHENTIK_BASE_URL=https://auth.example.com
AUTHENTIK_CLIENT_ID=your-client-id
AUTHENTIK_CLIENT_SECRET=your-secret
AUTHENTIK_SLUG=msg-converter
AUTHENTIK_REDIRECT_URI=http://your-server:5000/callback
```

#### Paso 2: Build y Run

```bash
# Build de la imagen
docker build -t msg-converter .

# Ejecutar el contenedor
docker run -d \
  --name msg-converter \
  -p 5000:5000 \
  --env-file .env \
  --restart unless-stopped \
  msg-converter
```

O usando docker-compose:

```bash
# Iniciar
docker-compose up -d

# Ver logs
docker-compose logs -f app

# Detener
docker-compose down
```

#### Paso 3: Configurar Authentik

1. En Authentik, configura el redirect URI:
   ```
   http://your-server-ip:5000/callback
   ```

2. Sigue las instrucciones de [Configuración del Provider OAuth2 en Authentik](#configuración-del-provider-oauth2-en-authentik)

#### Paso 4: Acceder

Accede a tu aplicación en: `http://your-server-ip:5000`

---

### Opción 2: Aplicación + Authentik (Stack completo)

Despliega tanto MSG Converter como Authentik en el mismo servidor usando `docker-compose.prod.yml`.

#### Paso 1: Preparar el entorno

```bash
# Clonar el repositorio
git clone https://github.com/your-repo/msg-converter.git
cd msg-converter

# Crear archivo .env
cp .env.example .env
```

#### Paso 2: Configurar variables de entorno

Edita `.env` con las siguientes variables **REQUERIDAS**:

```bash
# =============================================================================
# FLASK CONFIGURATION
# =============================================================================
SECRET_KEY=<genera-con: python3 -c "import secrets; print(secrets.token_hex(32))">

# =============================================================================
# AUTHENTIK DATABASE
# =============================================================================
PG_PASS=<password-seguro-para-postgresql>
PG_USER=authentik
PG_DB=authentik

# =============================================================================
# AUTHENTIK SERVER
# =============================================================================
AUTHENTIK_SECRET_KEY=<genera-con: openssl rand -base64 60>

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================
ENABLE_AUTH=false  # Inicia con auth deshabilitada para configurar primero
AUTHENTIK_BASE_URL=http://authentik-server:9000  # URL interna de Docker
APP_PORT=5000
AUTHENTIK_PORT_HTTP=9000
AUTHENTIK_PORT_HTTPS=9443
```

#### Paso 3: Iniciar el stack

```bash
# Iniciar todos los servicios
docker-compose -f docker-compose.prod.yml up -d

# Ver logs de todos los servicios
docker-compose -f docker-compose.prod.yml logs -f

# Ver solo logs de Authentik
docker-compose -f docker-compose.prod.yml logs -f authentik-server
```

Esto iniciará:
- PostgreSQL (base de datos para Authentik)
- Redis (caché para Authentik)
- Authentik Server (puerto 9000 HTTP, 9443 HTTPS)
- Authentik Worker (procesamiento en background)
- MSG Converter (puerto 5000)

#### Paso 4: Configuración inicial de Authentik

1. **Accede a Authentik**: `http://your-server-ip:9000/if/flow/initial-setup/`

2. **Crea el usuario administrador**:
   - Email: tu-email@example.com
   - Password: contraseña-segura

3. **Inicia sesión** en Authentik con las credenciales creadas

#### Paso 5: Crear Provider OAuth2 en Authentik

**Opción A: Auto-configuración con el wizard** (Recomendado)

1. Ve a `http://your-server-ip:5000/setup`
2. Configura:
   - Authentik URL: `http://your-server-ip:9000` (URL externa)
   - Application Name: `MSG to EML Converter`
   - Application URL: `http://your-server-ip:5000`
3. Crea un token de API en Authentik (Directory → Tokens)
4. Sigue el wizard de configuración

**Opción B: Configuración manual**

1. En Authentik, ve a **Applications → Applications**
2. Crea una nueva **Application**:
   - Name: `MSG to EML Converter`
   - Slug: `msg-converter`
   - Provider: (crear nuevo)

3. Crea un **OAuth2/OIDC Provider**:
   - Name: `MSG Converter Provider`
   - Authorization flow: `default-provider-authorization-implicit-consent`
   - Client type: `Confidential`
   - Client ID: (se genera automáticamente, cópialo)
   - Client Secret: (se genera automáticamente, cópialo)
   - Redirect URIs: Agregar:
     ```json
     {
       "matching_mode": "strict",
       "url": "http://your-server-ip:5000/callback"
     }
     ```

4. En **Advanced protocol settings**:
   - ✅ Habilita "Include claims in id_token"

5. En **Scopes**, selecciona:
   - ✅ `authentik default OAuth Mapping: OpenID 'openid'`
   - ✅ `authentik default OAuth Mapping: OpenID 'email'`
   - ✅ `authentik default OAuth Mapping: OpenID 'profile'`

6. Guarda el Provider y la Application

#### Paso 6: Configurar la aplicación MSG Converter

Actualiza `.env` con las credenciales de Authentik:

```bash
# Habilitar autenticación
ENABLE_AUTH=true

# Authentik URLs (para acceso desde fuera de Docker)
AUTHENTIK_BASE_URL=http://your-server-ip:9000

# OAuth2 credentials (copiadas de Authentik)
AUTHENTIK_CLIENT_ID=<client-id-del-provider>
AUTHENTIK_CLIENT_SECRET=<client-secret-del-provider>
AUTHENTIK_SLUG=msg-converter
AUTHENTIK_REDIRECT_URI=http://your-server-ip:5000/callback
```

#### Paso 7: Reiniciar la aplicación

```bash
# Reiniciar solo el contenedor de la app
docker-compose -f docker-compose.prod.yml restart msg-converter

# Ver logs para verificar
docker-compose -f docker-compose.prod.yml logs -f msg-converter
```

#### Paso 8: Probar la autenticación

1. Accede a `http://your-server-ip:5000`
2. Deberías ver la página de bienvenida con el botón "Iniciar Sesión"
3. Haz clic en "Iniciar Sesión"
4. Serás redirigido a Authentik para autenticarte
5. Después de login exitoso, volverás a la aplicación

---

### Comandos útiles de Docker

```bash
# Ver estado de contenedores
docker-compose -f docker-compose.prod.yml ps

# Ver logs en tiempo real
docker-compose -f docker-compose.prod.yml logs -f

# Ver logs de un servicio específico
docker-compose -f docker-compose.prod.yml logs -f msg-converter
docker-compose -f docker-compose.prod.yml logs -f authentik-server

# Reiniciar un servicio
docker-compose -f docker-compose.prod.yml restart msg-converter

# Detener todo
docker-compose -f docker-compose.prod.yml down

# Detener y eliminar volúmenes (⚠️ BORRA TODOS LOS DATOS)
docker-compose -f docker-compose.prod.yml down -v

# Reconstruir imagen de la app
docker-compose -f docker-compose.prod.yml build msg-converter
docker-compose -f docker-compose.prod.yml up -d msg-converter

# Ver uso de recursos
docker stats

# Acceder a shell dentro del contenedor
docker exec -it msg-converter /bin/bash
docker exec -it authentik-server /bin/bash
```

---

### Troubleshooting Docker

#### Error: "Connection refused" al conectar con Authentik

**Causa**: La aplicación intenta conectarse a Authentik usando la URL interna de Docker, pero no puede alcanzarlo.

**Solución**:
- Si ambos están en Docker: usa `AUTHENTIK_BASE_URL=http://authentik-server:9000`
- Si Authentik está en otro servidor: usa la URL externa completa

#### Error: "Network msg-converter-network not found"

**Causa**: El network no se creó correctamente.

**Solución**:
```bash
# Recrear networks
docker network create msg-converter-network
docker network create authentik-network
```

#### Error: "Port already in use"

**Causa**: El puerto ya está siendo usado por otro proceso.

**Solución**:
```bash
# Cambiar puerto en .env
APP_PORT=5001  # o cualquier puerto disponible

# O detener el proceso que usa el puerto
sudo lsof -i :5000
sudo kill -9 <PID>
```

#### Logs de Authentik muestran errores de base de datos

**Causa**: PostgreSQL no inició correctamente o las credenciales son incorrectas.

**Solución**:
```bash
# Verificar que PostgreSQL esté corriendo
docker-compose -f docker-compose.prod.yml ps postgresql

# Ver logs de PostgreSQL
docker-compose -f docker-compose.prod.yml logs postgresql

# Verificar credenciales en .env
grep PG_ .env
```

---

### Backup y Restauración

#### Backup de datos de Authentik

```bash
# Backup de PostgreSQL
docker exec authentik-db pg_dump -U authentik authentik > authentik-backup-$(date +%Y%m%d).sql

# Backup de volúmenes
docker run --rm \
  -v authentik-media:/source \
  -v $(pwd):/backup \
  alpine tar czf /backup/authentik-media-$(date +%Y%m%d).tar.gz -C /source .
```

#### Restauración

```bash
# Restaurar PostgreSQL
docker exec -i authentik-db psql -U authentik authentik < authentik-backup-20251121.sql

# Restaurar volúmenes
docker run --rm \
  -v authentik-media:/target \
  -v $(pwd):/backup \
  alpine tar xzf /backup/authentik-media-20251121.tar.gz -C /target
```

---

### Producción con Reverse Proxy (Nginx/Traefik)

Para usar en producción con HTTPS, se recomienda poner un reverse proxy delante:

#### Ejemplo con Nginx

```nginx
# /etc/nginx/sites-available/msg-converter
server {
    listen 80;
    server_name msg-converter.example.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name msg-converter.example.com;

    # SSL certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/msg-converter.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/msg-converter.example.com/privkey.pem;

    # Proxy to Docker container
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
    }
}
```

Habilitar y recargar:
```bash
sudo ln -s /etc/nginx/sites-available/msg-converter /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**IMPORTANTE**: Actualiza `AUTHENTIK_REDIRECT_URI` en `.env` a:
```bash
AUTHENTIK_REDIRECT_URI=https://msg-converter.example.com/callback
```

Y configura el mismo valor en Authentik (Provider → Redirect URIs).

---

## Configuración del Provider OAuth2 en Authentik

**CRÍTICO**: Después de crear el provider OAuth2 en Authentik (ya sea manualmente o con el wizard), debes configurar correctamente los siguientes parámetros para que la autenticación funcione:

### 1. Habilitar "Include claims in id_token"

Por defecto, Authentik NO incluye los claims del usuario (email, name, preferred_username) en el `id_token`. Debes habilitarlo manualmente.

**Pasos**:
1. Ve a **Authentik → Applications → Applications**
2. Busca tu aplicación (ej: "MSG to EML Converter")
3. Haz clic en el **Provider** asociado
4. Scroll hasta la sección **"Advanced protocol settings"**
5. **✅ HABILITA** el checkbox **"Include claims in id_token"**
6. Haz clic en **"Update"** para guardar

**Sin esto**: Los claims estarán vacíos y tu aplicación mostrará "Usuario" o "None" en lugar del nombre real del usuario.

### 2. Configurar Scope Mappings

Los scope mappings determinan qué información del usuario se incluye en los tokens. Debes asegurarte de tener los mappings estándar de OIDC.

**Pasos**:
1. En la misma página del Provider, busca la sección **"Scopes"**
2. Asegúrate de tener seleccionados:
   - ✅ **authentik default OAuth Mapping: OpenID 'openid'**
   - ✅ **authentik default OAuth Mapping: OpenID 'email'**
   - ✅ **authentik default OAuth Mapping: OpenID 'profile'**
3. Si faltan, agrégalos desde el dropdown **"Add existing scope"**
4. Haz clic en **"Update"** para guardar

**Qué incluye cada scope**:
- `openid`: Claims básicos (sub, iss, aud, exp, iat)
- `email`: Email del usuario y email_verified
- `profile`: Nombre, username, given_name, family_name, nickname, groups

### 3. Configurar Redirect URIs (Formato 2024.8+)

Authentik 2024.8+ requiere un formato específico para los redirect URIs con modo de matching estricto.

**Pasos**:
1. En la página del Provider, busca **"Redirect URIs"**
2. Asegúrate de tener configurado:
   ```
   Matching Mode: strict
   URL: https://tu-app.com/callback
   ```
3. **IMPORTANTE**: La URL debe coincidir EXACTAMENTE con `AUTHENTIK_REDIRECT_URI` en tus variables de entorno
4. Diferencias de mayúsculas/minúsculas, http vs https, o trailing slash causarán errores

### 4. Verificar Configuración del Usuario

Asegúrate de que tu usuario en Authentik tenga la información básica configurada:

**Pasos**:
1. Ve a **Authentik → Directory → Users**
2. Busca tu usuario y ábrelo
3. Verifica que tenga:
   - **Username**: Configurado (requerido)
   - **Name**: Nombre completo (opcional, se mostrará en la app si existe)
   - **Email**: Dirección de email (opcional pero recomendado)
4. Guarda si hiciste cambios

### 5. Verificar que funciona

Después de configurar todo:

1. **Cierra sesión** de tu aplicación si ya estabas logueado
2. **Limpia las cookies** del navegador (o usa ventana incógnita)
3. **Inicia sesión** nuevamente
4. Deberías ver tu nombre/email correctamente en el header de la aplicación

**Si sigue sin funcionar**, revisa los logs de tu aplicación para ver qué claims están llegando en el `id_token`.

---

## Troubleshooting

### Problemas de Configuración

#### Error: "Authentication is DISABLED" en producción

**Causa**: Variable `ENABLE_AUTH` no está configurada o tiene valor incorrecto

**Solución**:
```bash
# Debe ser exactamente 'true' (minúsculas)
ENABLE_AUTH=true  # ✅ Correcto
ENABLE_AUTH=True  # ❌ No funciona
ENABLE_AUTH=TRUE  # ❌ No funciona
```

#### Error: "404 Not Found" en OIDC endpoint

**Causa**: Usando `client_id` en lugar de `slug` en la URL

**Solución**:
```python
# ❌ INCORRECTO (usa client_id):
server_metadata_url=f'{base_url}/application/o/{client_id}/.well-known/openid-configuration'

# ✅ CORRECTO (usa slug):
authorize_url=f'{base_url}/application/o/authorize/'
```

**Verificar**: El slug está en Authentik → Applications → Tu App → campo "Slug"

#### Error: "redirect_uri_mismatch" o "invalid_grant - redirect_uri does not match"

**Causa**: El `redirect_uri` en Authentik no coincide EXACTAMENTE con el generado por Flask

**Diagnóstico**:
1. Accede a `/auth/debug` en tu aplicación (si implementaste el endpoint)
2. Copia el valor de `flask_generates_this_url`
3. Ve a Authentik → Applications → Tu Provider → Redirect URIs
4. Verifica que coincida EXACTAMENTE (case-sensitive, con/sin trailing slash)

**Solución**:
```bash
# En Authentik, configura EXACTAMENTE:
https://your-app.com/callback

# Y en tu .env también EXACTAMENTE lo mismo:
AUTHENTIK_REDIRECT_URI=https://your-app.com/callback

# IMPORTANTE: No pongas trailing slash si Authentik no lo tiene
```

**Para Authentik 2024.8+**: Asegúrate que `matching_mode` sea `"strict"`:
```python
'redirect_uris': [
    {
        'matching_mode': 'strict',
        'url': 'https://your-app.com/callback'
    }
]
```

---

### Problemas de JWKS/Tokens

#### Error: "Invalid key set format"

**Causa**: JWKS vacío con algoritmo HS256, Authlib intenta validar id_token

**Diagnóstico**:
```bash
curl https://your-authentik.com/application/o/your-slug/jwks/
# Si devuelve {} (vacío), tienes este problema
```

**Solución**: Usa configuración manual de endpoints (SIN `server_metadata_url`):

```python
# ❌ EVITA ESTO con HS256:
server_metadata_url=f'{base_url}/application/o/{slug}/.well-known/openid-configuration'

# ✅ USA ESTO en su lugar:
authorize_url=f'{base_url}/application/o/authorize/',
access_token_url=f'{base_url}/application/o/token/',
```

#### Error: "'FlaskOAuth2App' object has no attribute 'userinfo_endpoint'"

**Causa**: Los endpoints no están disponibles como atributos del objeto OAuth

**Solución**: Usa URLs directas:

```python
# ❌ NO funciona:
auth.authentik.userinfo_endpoint

# ✅ Usa esto:
f'{auth.base_url}/application/o/userinfo/'
```

#### Error: "insufficient_scope" (403) al llamar userinfo endpoint

**Causa**: El `access_token` no incluye los scopes necesarios

**Solución**: Extrae la información del `id_token` en lugar de llamar al endpoint:

```python
if 'id_token' in token:
    # JWT format: header.payload.signature
    id_token_parts = token['id_token'].split('.')
    payload = id_token_parts[1]
    payload += '=' * (4 - len(payload) % 4)  # Add padding
    user_info = json.loads(base64.urlsafe_b64decode(payload))
```

Esto es más eficiente y no requiere scopes adicionales.

---

### Problemas de Sesión

#### Error: Cookie demasiado grande - sesión no persiste

**Síntoma**: Usuario se autentica pero inmediatamente vuelve al login

**Warning en logs**:
```
UserWarning: The 'session' cookie is too large: ... 5080 bytes but the limit is 4093 bytes
```

**Causa**: Guardando tokens completos en la sesión

**Solución**: NO guardes tokens en la sesión:

```python
# ❌ NUNCA hagas esto:
session['token'] = token  # Los JWTs son enormes (>2KB cada uno)

# ✅ Solo guarda información esencial del usuario:
session['user'] = {
    'email': user_info.get('email'),
    'name': user_info.get('name'),
    'groups': user_info.get('groups', [])
}
session['expires_at'] = expires_at.isoformat()
session['authenticated'] = True
```

**Por qué**: Los tokens (access_token, id_token, refresh_token) son JWTs grandes. La sesión de Flask se guarda en una cookie, y los navegadores tienen un límite de 4KB. Si la cookie excede este límite, el navegador la ignora silenciosamente.

---

### Problemas de PKCE

#### Error: "invalid_grant" después de login exitoso

**Síntoma**: Login funciona en Authentik, pero falla el intercambio de tokens

**Causa**: Desajuste de PKCE (Proof Key for Code Exchange)

**Diagnóstico**:
- Authlib envía `code_challenge` en el authorize request (si PKCE está habilitado)
- Pero el intercambio manual de tokens con `requests.post()` no envía `code_verifier`
- Authentik rechaza porque el flujo PKCE está incompleto

**Solución 1 - Deshabilitar PKCE** (recomendado para intercambio manual):

```python
self.authentik = self.oauth.register(
    name='authentik',
    client_id=self.client_id,
    client_secret=self.client_secret,
    authorize_url=f'{self.base_url}/application/o/authorize/',
    access_token_url=f'{self.base_url}/application/o/token/',
    client_kwargs={
        'scope': 'openid email profile',
        # NO incluyas 'code_challenge_method' si haces intercambio manual
    }
)
```

**Solución 2 - Usar authorize_access_token()** (si quieres PKCE):

```python
# Habilita PKCE en la configuración:
client_kwargs={
    'scope': 'openid email profile',
    'code_challenge_method': 'S256',
}

# Y en el callback usa el método de Authlib:
token = auth.authentik.authorize_access_token()
# Pero esto podría fallar con JWKS vacío - ver solución arriba
```

**Recomendación**: Usa intercambio manual SIN PKCE para máxima compatibilidad con diferentes configuraciones de Authentik.

---

### Problemas de Proxy/HTTPS

#### Error: redirect_uri tiene http:// en lugar de https://

**Causa**: Flask no detecta que está detrás de un proxy HTTPS

**Solución**: Agrega ProxyFix al inicio de tu aplicación:

```python
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

# CRÍTICO: Esto DEBE estar ANTES de cualquier ruta
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
```

**Cómo funciona**: Los proxies reversos (Nginx, Render, Heroku) agregan headers `X-Forwarded-Proto` y `X-Forwarded-Host`. ProxyFix lee estos headers y los usa para generar URLs correctas con HTTPS.

---

### Problemas de Visualización de Usuario

#### Error: Usuario aparece como "None" o "Usuario" en lugar del nombre real

**Síntoma**: Después de iniciar sesión exitosamente, el header de la aplicación muestra "None" o "Usuario" en lugar del nombre del usuario.

**Causa 1 - Claims no incluidos en id_token** (más común):
- El provider de Authentik no tiene habilitado "Include claims in id_token"
- Los scope mappings (email, profile) no están configurados
- El `id_token` solo contiene claims mínimos (sub, iss, aud, exp, iat)

**Solución**:
1. Ve a **Authentik → Applications → Tu aplicación → Provider**
2. En **"Advanced protocol settings"**, habilita ✅ **"Include claims in id_token"**
3. En **"Scopes"**, asegúrate de tener:
   - ✅ `authentik default OAuth Mapping: OpenID 'openid'`
   - ✅ `authentik default OAuth Mapping: OpenID 'email'`
   - ✅ `authentik default OAuth Mapping: OpenID 'profile'`
4. Guarda y cierra sesión en tu app
5. Inicia sesión nuevamente

**Causa 2 - Usuario sin información configurada**:
- Tu usuario en Authentik no tiene nombre o email configurado

**Solución**:
1. Ve a **Authentik → Directory → Users**
2. Abre tu usuario
3. Asegúrate de tener configurado:
   - **Username**: (requerido)
   - **Name**: Tu nombre completo
   - **Email**: Tu email
4. Guarda y vuelve a iniciar sesión

**Causa 3 - Fallback en el código**:
Si no hay name, preferred_username ni email, el código usa "Usuario" como fallback. Esto indica que ningún claim llegó correctamente.

**Verificación con logs**:
Si tienes acceso a los logs del servidor, busca la sección:
```
=== ID_TOKEN CLAIMS ===
Available claims: [...]
  - email: NOT PRESENT  ← Problema aquí
  - name: NOT PRESENT   ← Problema aquí
  - preferred_username: NOT PRESENT
```

Si todos muestran "NOT PRESENT", el problema es la configuración del provider en Authentik (solución arriba).

---

### Problemas de Logout

#### Error: 404 en logout - URL usa client_id en lugar de slug

**Síntoma**: Al hacer clic en "Cerrar Sesión", obtienes un error 404:
```
https://auth.example.com/application/o/0EQttwGxHfo2S0uSy7IhtV8qYPWKCkLIG56quYxp/end-session/
                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                           client_id (incorrecto)
```

**Causa**: El endpoint de logout usa el client_id en lugar del slug de la aplicación.

**Solución**:
Corrige la URL de logout para usar el slug:

```python
# ❌ INCORRECTO:
logout_url = f"{auth.base_url}/application/o/{auth.client_id}/end-session/"

# ✅ CORRECTO:
logout_url = f"{auth.base_url}/application/o/{auth.slug}/end-session/"
```

**URL correcta**: `https://auth.example.com/application/o/msg-converter/end-session/`

**Nota**: Todos los endpoints de aplicación en Authentik usan el slug, no el client_id:
- ✅ `/application/o/{slug}/.well-known/openid-configuration`
- ✅ `/application/o/{slug}/jwks/`
- ✅ `/application/o/{slug}/end-session/`

Solo los endpoints OAuth2 genéricos usan rutas sin slug:
- `/application/o/authorize/`
- `/application/o/token/`
- `/application/o/userinfo/`

---

## Consideraciones de Seguridad

### 🔐 Mejores Prácticas

1. **SECRET_KEY**: SIEMPRE usa claves aleatorias en producción
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **HTTPS Obligatorio**: NUNCA uses HTTP en producción
   - OAuth2 requiere conexiones seguras
   - Los tokens se transmiten en URLs y headers
   - Los navegadores modernos bloquean cookies inseguras

3. **Cookies Seguras**: Configura Flask correctamente
   ```python
   app.config['SESSION_COOKIE_SECURE'] = True  # Solo HTTPS
   app.config['SESSION_COOKIE_HTTPONLY'] = True  # No accesible desde JS
   app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Protección CSRF
   ```

4. **Token de API**: Limita permisos al mínimo
   - Solo `view` y `write` para Providers y Applications
   - Considera crear tokens de un solo uso para setup
   - Nunca expongas el token en logs o frontend

5. **Grupos de Acceso**: Restringe por grupos cuando sea necesario
   ```bash
   AUTHENTIK_ALLOWED_GROUPS=admin,developers
   ```

6. **Validación de redirect_uris**: Usa `matching_mode: strict`
   ```python
   'redirect_uris': [
       {
           'matching_mode': 'strict',  # No regex, no wildcards
           'url': 'https://your-app.com/callback'
       }
   ]
   ```

7. **Sesiones**: No almacenes información sensible
   ```python
   # ✅ Correcto - solo información básica del usuario
   session['user'] = {'email': user['email'], 'name': user['name']}

   # ❌ Evitar - tokens, contraseñas, datos sensibles
   session['access_token'] = token['access_token']  # NO!
   ```

8. **Logging**: Registra eventos importantes SIN exponer secretos
   ```python
   # ✅ Correcto
   print(f"User {user['email']} logged in from {request.remote_addr}")

   # ❌ NUNCA hagas esto
   print(f"Token: {access_token}")  # NO!
   ```

9. **Expiración de Sesiones**: Configura lifetime apropiado
   ```bash
   # 24 horas para apps internas
   SESSION_LIFETIME_HOURS=24

   # 1 hora para apps públicas con datos sensibles
   SESSION_LIFETIME_HOURS=1
   ```

10. **Rate Limiting**: Implementa límites en endpoints críticos
    ```python
    from flask_limiter import Limiter

    limiter = Limiter(app, default_limits=["200 per day", "50 per hour"])

    @app.route('/login')
    @limiter.limit("10 per minute")
    def login():
        ...
    ```

### 🚫 Evitar

- ❌ No expongas `client_secret` en código fuente o frontend
- ❌ No uses HTTP en producción (solo para desarrollo local)
- ❌ No almacenes tokens en localStorage (usa sesiones server-side)
- ❌ No deshabilites validación SSL (`verify=False`)
- ❌ No uses `SECRET_KEY` por defecto o hardcodeada
- ❌ No compartas tokens de API entre múltiples aplicaciones
- ❌ No ignores warnings de cookies demasiado grandes
- ❌ No uses PKCE sin entender cómo funciona el flujo completo

---

## Estructura de Archivos Recomendada

```
my-app/
├── app.py                          # Aplicación principal Flask
├── auth.py                         # Módulo de autenticación (código de esta guía)
├── web_setup.py                    # Auto-configuración web (opcional)
├── requirements.txt                # Dependencias Python
├── .env.example                    # Plantilla de configuración
├── .env                            # Configuración real (git-ignored!)
├── .gitignore                      # IMPORTANTE: ignorar .env
├── README.md                       # Documentación del proyecto
├── templates/
│   ├── base.html                   # Template base con nav/header
│   ├── index.html                  # Página principal
│   ├── welcome.html                # Página de bienvenida con botón login
│   ├── dashboard.html              # Dashboard protegido
│   └── setup.html                  # Wizard de configuración (opcional)
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
└── docs/
    └── AUTHENTIK_INTEGRATION_GUIDE.md  # Esta guía
```

### `.gitignore` esencial

```
# Environment variables
.env
.env.local
.env.production

# Flask
__pycache__/
*.pyc
instance/
.pytest_cache/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

---

## Dependencias Python

### `requirements.txt`

```txt
# Web Framework
Flask>=3.0.0
gunicorn>=21.2.0

# OAuth2/OIDC Authentication
Authlib>=1.6.0
requests>=2.31.0
cryptography>=41.0.0

# Environment Variables
python-dotenv>=1.0.0

# Optional: Rate limiting
Flask-Limiter>=3.5.0

# Optional: CORS (if building API)
Flask-CORS>=4.0.0
```

**Versiones importantes**:
- `Authlib>=1.6.0` - Versiones anteriores tienen bugs con JWKS
- `Flask>=3.0.0` - Soporte para Python 3.11+
- `cryptography>=41.0.0` - Requerido por Authlib

Instalar:
```bash
pip install -r requirements.txt
```

---

## Ejemplo Completo Mínimo

Aplicación funcional completa en un solo archivo (para testing):

```python
#!/usr/bin/env python3
"""
Minimal Authentik OAuth2 integration example
Tested with Authentik 2024.8+ and Flask 3.0+
"""

import os
import json
import base64
import requests
from flask import Flask, session, redirect, url_for, request, jsonify
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')

# CRITICAL: Enable ProxyFix for production behind proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# OAuth setup
oauth = OAuth(app)
authentik = oauth.register(
    name='authentik',
    client_id=os.getenv('AUTHENTIK_CLIENT_ID'),
    client_secret=os.getenv('AUTHENTIK_CLIENT_SECRET'),
    authorize_url=f"{os.getenv('AUTHENTIK_BASE_URL')}/application/o/authorize/",
    access_token_url=f"{os.getenv('AUTHENTIK_BASE_URL')}/application/o/token/",
    client_kwargs={
        'scope': 'openid email profile',
        # PKCE disabled for manual token exchange
    }
)

# Auth decorator
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
    user = session['user']
    return f"""
    <h1>Welcome, {user['name']}!</h1>
    <p>Email: {user['email']}</p>
    <p><a href="/logout">Logout</a></p>
    """

@app.route('/login')
def login():
    redirect_uri = url_for('callback', _external=True)
    return authentik.authorize_redirect(redirect_uri)

@app.route('/callback')
def callback():
    try:
        code = request.args.get('code')
        if not code:
            return 'No authorization code', 400

        # Exchange code for token
        token_response = requests.post(
            authentik.access_token_url,
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': url_for('callback', _external=True),
                'client_id': os.getenv('AUTHENTIK_CLIENT_ID'),
                'client_secret': os.getenv('AUTHENTIK_CLIENT_SECRET')
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if token_response.status_code != 200:
            return f'Token exchange failed: {token_response.text}', 400

        token = token_response.json()

        # Extract user info from id_token
        user_info = None
        if 'id_token' in token:
            id_token_parts = token['id_token'].split('.')
            payload = id_token_parts[1]
            payload += '=' * (4 - len(payload) % 4)
            user_info = json.loads(base64.urlsafe_b64decode(payload))

        if not user_info:
            return 'Failed to get user info', 400

        # Store minimal user info in session (avoid cookie size limit)
        session['user'] = {
            'email': user_info.get('email'),
            'name': user_info.get('name', user_info.get('preferred_username', 'User'))
        }
        session['expires_at'] = (datetime.now() + timedelta(hours=24)).isoformat()

        return redirect(url_for('index'))

    except Exception as e:
        return f'Authentication failed: {str(e)}', 400

@app.route('/logout')
def logout():
    session.clear()
    logout_url = f"{os.getenv('AUTHENTIK_BASE_URL')}/application/o/{os.getenv('AUTHENTIK_SLUG')}/end-session/"
    return redirect(logout_url)

if __name__ == '__main__':
    app.run(debug=True)
```

**Uso**:
1. Copia el código a `app.py`
2. Configura variables de entorno en `.env`
3. Ejecuta: `python app.py`
4. Accede a `http://localhost:5000`

---

## Referencias y Recursos

### Documentación Oficial

- **Authentik Docs**: https://goauthentik.io/docs/
- **Authentik OAuth2 Provider**: https://goauthentik.io/docs/providers/oauth2/
- **Authentik API Reference**: https://goauthentik.io/developer-docs/api/
- **OAuth2 RFC 6749**: https://datatracker.ietf.org/doc/html/rfc6749
- **OIDC Core Spec**: https://openid.net/specs/openid-connect-core-1_0.html
- **Authlib Documentation**: https://docs.authlib.org/
- **Flask Documentation**: https://flask.palletsprojects.com/
- **Flask Security**: https://flask.palletsprojects.com/en/stable/security/

### Herramientas Útiles

- **JWT Debugger**: https://jwt.io/ - Decodifica y verifica JWTs
- **OAuth2 Debugger**: https://oauthdebugger.com/ - Prueba flujos OAuth2
- **Authentik Community**: https://github.com/goauthentik/authentik/discussions

### Versiones Probadas

Esta guía ha sido probada con:
- ✅ Authentik 2024.8.0 - 2024.10.3
- ✅ Flask 3.0.0+
- ✅ Authlib 1.6.0+
- ✅ Python 3.11+
- ✅ Plataformas: Render.com, Railway.app, Heroku

---

## Changelog

### Versión 2.2 (2025-11-21)

**Nuevas características - Docker**:
- 🐳 Agregada sección completa: "Despliegue con Docker"
- 🐳 Dockerfile multi-stage optimizado para producción
- 🐳 docker-compose.yml para desarrollo/testing local
- 🐳 docker-compose.prod.yml con stack completo (App + Authentik + PostgreSQL + Redis)
- 🐳 .dockerignore para optimizar builds
- 🐳 .env.example con todas las variables documentadas
- 🐳 Guía de configuración de Authentik en Docker paso a paso
- 🐳 Wizard de auto-configuración funciona con Authentik en Docker
- 🐳 Troubleshooting específico de Docker
- 🐳 Comandos útiles de Docker y docker-compose
- 🐳 Guía de backup y restauración de datos
- 🐳 Configuración con reverse proxy (Nginx) para HTTPS
- 🐳 Healthchecks en contenedores
- 🐳 Usuario no-root por seguridad

**Limpieza de archivos**:
- 🧹 Eliminados archivos markdown redundantes:
  * AUTHENTIK_SETUP.md (contenido en AUTHENTIK_INTEGRATION_GUIDE.md)
  * QUICK_AUTH_SETUP.md (contenido en AUTHENTIK_INTEGRATION_GUIDE.md)
  * WEB_SETUP_GUIDE.md (contenido en AUTHENTIK_INTEGRATION_GUIDE.md)
  * START.md (contenido en README.md)
  * DEPLOYMENT.md (contenido en AUTHENTIK_INTEGRATION_GUIDE.md)
  * CHANGELOG.md (changelog ahora en git y en guía)

**Despliegue**:
- Opción 1: Solo app con Authentik externo
- Opción 2: Stack completo (App + Authentik)
- Compatible con desarrollo local y producción
- Soporte para reverse proxy (Nginx/Traefik)

**Versión de la guía**: 2.1 → 2.2

### Versión 2.1 (2025-11-21)

**Nuevas características**:
- ✨ Agregada sección completa: "Configuración del Provider OAuth2 en Authentik"
- ✨ Documentación detallada de configuración de Scope Mappings requeridos
- ✨ Guía paso a paso para habilitar "Include claims in id_token"
- ✨ Sección de troubleshooting: "Problemas de Visualización de Usuario"
- ✨ Sección de troubleshooting: "Problemas de Logout"

**Fixes documentados**:
- 🐛 Fix: Logout URL usando slug en lugar de client_id
- 🐛 Fix: Usuario muestra "None" o "Usuario" por claims faltantes
- 🐛 Fix: Lógica de fallback para display name (name → preferred_username → email)
- 🐛 Fix: Debug logs detallados de id_token claims

**Configuración crítica de Authentik**:
- ✅ `authentik default OAuth Mapping: OpenID 'openid'` (requerido)
- ✅ `authentik default OAuth Mapping: OpenID 'email'` (requerido)
- ✅ `authentik default OAuth Mapping: OpenID 'profile'` (requerido)
- ✅ Habilitar "Include claims in id_token" en Advanced protocol settings

**Versiones probadas en producción**:
- MSG to EML Converter v2.1.20
- Authentik 2024.8+
- Desplegado exitosamente en Render.com

### Versión 2.0 (2025-11-21)

**Cambios mayores**:
- ✨ Agregada solución completa para problemas de PKCE
- ✨ Implementado extracción de user info desde id_token (evita insufficient_scope)
- ✨ Agregada solución para cookies de sesión >4KB
- ✨ Documentado ProxyFix para despliegue detrás de proxies
- ✨ Agregado código de producción completo y probado
- 🐛 Solucionados todos los problemas de JWKS vacío con HS256
- 🐛 Corregidos errores de FlaskOAuth2App attributes
- 📝 Reescrita sección de Troubleshooting con soluciones reales
- 📝 Agregados ejemplos probados en producción

**Compatibilidad**:
- Authentik 2024.8+
- Flask 3.0+
- Python 3.11+

### Versión 1.0 (2025-11-20)

- 🎉 Versión inicial de la guía

---

## Licencia

Esta guía es de código abierto y puede ser adaptada libremente para tus proyectos.

**Contribuciones**: Si encuentras errores o mejoras, por favor reporta en el repositorio del proyecto.

---

## Soporte

**¿Preguntas o problemas?**

1. Revisa la sección de [Troubleshooting](#troubleshooting)
2. Consulta la [documentación oficial de Authentik](https://goauthentik.io/docs/)
3. Busca en [GitHub Discussions](https://github.com/goauthentik/authentik/discussions)
4. Verifica que estés usando las versiones correctas (Authlib >= 1.6.0)

**Última actualización**: 2025-11-21
**Versión de la guía**: 2.2
**Compatible con**: Authentik 2024.8+, Flask 3.0+, Python 3.11+, Docker 20.10+
**Probado en producción**: MSG to EML Converter v2.1.20 en Render.com y Docker
