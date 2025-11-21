#!/usr/bin/env python3
"""
Auto-configuración para Authentik

Este script configura automáticamente la aplicación en Authentik
sin necesidad de configurar manualmente Client ID y Secret.
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv, set_key

load_dotenv()


class AuthentikAutoSetup:
    """Configuración automática de Authentik"""

    def __init__(self):
        self.base_url = None
        self.api_token = None
        self.app_url = None
        self.app_name = "MSG to EML Converter"
        self.app_slug = "msg-eml-converter"

    def setup(self):
        """Ejecutar configuración automática"""
        print("=" * 60)
        print("🔧 Auto-configuración de Authentik para MSG to EML Converter")
        print("=" * 60)
        print()

        # Paso 1: Obtener información de Authentik
        self.get_authentik_info()

        # Paso 2: Crear Provider OAuth2
        provider = self.create_oauth_provider()
        if not provider:
            return False

        # Paso 3: Crear Application
        application = self.create_application(provider)
        if not application:
            return False

        # Paso 4: Guardar configuración en .env
        self.save_to_env(provider)

        print()
        print("=" * 60)
        print("✅ Configuración completada exitosamente!")
        print("=" * 60)
        print()
        print("Las credenciales han sido guardadas en el archivo .env")
        print()
        print("Ahora puedes ejecutar la aplicación con:")
        print("  python app.py")
        print()

        return True

    def get_authentik_info(self):
        """Obtener información de conexión a Authentik"""
        print("📋 Paso 1: Información de Authentik")
        print()

        # URL de Authentik
        self.base_url = os.environ.get('AUTHENTIK_BASE_URL')
        if not self.base_url:
            self.base_url = input("URL de tu instancia Authentik (ej: https://auth.ejemplo.com): ").strip()

        # Limpiar URL (quitar trailing slash)
        self.base_url = self.base_url.rstrip('/')

        # Token de API
        self.api_token = os.environ.get('AUTHENTIK_API_TOKEN')
        if not self.api_token:
            print()
            print("Necesitas un token de API de Authentik.")
            print("Para obtenerlo:")
            print("  1. Inicia sesión en Authentik como administrador")
            print("  2. Ve a Directory → Tokens")
            print("  3. Crea un nuevo token con scope 'view' y 'write'")
            print()
            self.api_token = input("Token de API de Authentik: ").strip()

        # URL de la aplicación
        self.app_url = os.environ.get('AUTHENTIK_REDIRECT_URI', '').replace('/callback', '')
        if not self.app_url:
            print()
            self.app_url = input("URL de tu aplicación (ej: https://msg-converter.onrender.com o http://localhost:5000): ").strip()

        self.app_url = self.app_url.rstrip('/')

        print()
        print(f"✓ URL Authentik: {self.base_url}")
        print(f"✓ URL Aplicación: {self.app_url}")
        print()

    def api_request(self, method, endpoint, data=None):
        """Realizar petición a la API de Authentik"""
        url = f"{self.base_url}/api/v3/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            else:
                raise ValueError(f"Método no soportado: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"❌ Error en la petición API: {e}")
            if hasattr(e.response, 'text'):
                print(f"Respuesta: {e.response.text}")
            return None

    def get_default_flow(self):
        """Obtener el flujo de autenticación por defecto"""
        flows = self.api_request('GET', 'flows/instances/')
        if not flows:
            return None

        # Buscar flujo de autenticación por defecto
        for flow in flows.get('results', []):
            if 'authentication' in flow.get('slug', '').lower():
                return flow['pk']

        # Si no encuentra, usar el primero
        if flows.get('results'):
            return flows['results'][0]['pk']

        return None

    def create_oauth_provider(self):
        """Crear Provider OAuth2 en Authentik"""
        print("📋 Paso 2: Creando Provider OAuth2")
        print()

        # Verificar si ya existe
        providers = self.api_request('GET', 'providers/oauth2/')
        if providers:
            for provider in providers.get('results', []):
                if provider.get('name') == self.app_name:
                    print(f"⚠️  Provider '{self.app_name}' ya existe")
                    use_existing = input("¿Usar el provider existente? (s/n): ").strip().lower()
                    if use_existing == 's':
                        print(f"✓ Usando provider existente")
                        return provider
                    else:
                        # Actualizar slug para crear uno nuevo
                        import time
                        self.app_slug = f"{self.app_slug}-{int(time.time())}"

        # Obtener flujo por defecto
        flow = self.get_default_flow()
        if not flow:
            print("❌ No se pudo obtener un flujo de autenticación")
            return None

        # Crear provider
        provider_data = {
            'name': self.app_name,
            'authorization_flow': flow,
            'client_type': 'confidential',
            'redirect_uris': f"{self.app_url}/callback",
            'sub_mode': 'hashed_user_id',
            'include_claims_in_id_token': True,
            'signing_key': None,  # Usar clave por defecto
            'property_mappings': []  # Usar mappings por defecto
        }

        provider = self.api_request('POST', 'providers/oauth2/', provider_data)
        if not provider:
            print("❌ Error al crear provider")
            return None

        print(f"✓ Provider creado exitosamente")
        print(f"  Client ID: {provider.get('client_id', 'N/A')}")
        print()

        return provider

    def create_application(self, provider):
        """Crear Application en Authentik"""
        print("📋 Paso 3: Creando Application")
        print()

        # Verificar si ya existe
        apps = self.api_request('GET', 'core/applications/')
        if apps:
            for app in apps.get('results', []):
                if app.get('slug') == self.app_slug:
                    print(f"⚠️  Application '{self.app_name}' ya existe")
                    print(f"✓ Usando application existente")
                    return app

        # Crear application
        app_data = {
            'name': self.app_name,
            'slug': self.app_slug,
            'provider': provider['pk'],
            'meta_launch_url': self.app_url,
            'policy_engine_mode': 'any',
            'open_in_new_tab': False
        }

        application = self.api_request('POST', 'core/applications/', app_data)
        if not application:
            print("❌ Error al crear application")
            return None

        print(f"✓ Application creada exitosamente")
        print()

        return application

    def save_to_env(self, provider):
        """Guardar configuración en archivo .env"""
        print("📋 Paso 4: Guardando configuración")
        print()

        env_file = '.env'

        # Crear .env si no existe
        if not os.path.exists(env_file):
            with open('.env.example', 'r') as f_example:
                with open(env_file, 'w') as f_env:
                    f_env.write(f_example.read())

        # Actualizar variables
        set_key(env_file, 'ENABLE_AUTH', 'true')
        set_key(env_file, 'AUTHENTIK_BASE_URL', self.base_url)
        set_key(env_file, 'AUTHENTIK_CLIENT_ID', provider['client_id'])
        set_key(env_file, 'AUTHENTIK_CLIENT_SECRET', provider['client_secret'])
        set_key(env_file, 'AUTHENTIK_REDIRECT_URI', f"{self.app_url}/callback")

        # Guardar también el token de API para futuras configuraciones
        set_key(env_file, 'AUTHENTIK_API_TOKEN', self.api_token)

        print(f"✓ Configuración guardada en {env_file}")

    def validate_connection(self):
        """Validar conexión con Authentik"""
        print("🔍 Validando conexión con Authentik...")
        print()

        # Test de conexión
        result = self.api_request('GET', 'core/applications/')
        if result is None:
            print("❌ No se pudo conectar con Authentik")
            print()
            print("Verifica:")
            print("  - La URL de Authentik es correcta")
            print("  - El token de API es válido")
            print("  - Tienes conexión a internet")
            return False

        print("✓ Conexión exitosa con Authentik")
        print()
        return True


def main():
    """Función principal"""
    setup = AuthentikAutoSetup()

    # Obtener información
    setup.get_authentik_info()

    # Validar conexión
    if not setup.validate_connection():
        sys.exit(1)

    # Ejecutar setup
    if setup.setup():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
