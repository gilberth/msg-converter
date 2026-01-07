#!/usr/bin/env python3
"""
Auto-configuración para Pocket ID

Este script configura automáticamente la aplicación en Pocket ID
sin necesidad de configurar manualmente Client ID y Secret.
"""

import os
import sys
import requests
import json
import secrets
from dotenv import load_dotenv, set_key

load_dotenv()


class PocketIDAutoSetup:
    """Configuración automática de Pocket ID"""

    def __init__(self):
        self.base_url = None
        self.api_key = None
        self.app_url = None
        self.app_name = "MSG to EML Converter"
        self.client_id = f"msg-eml-converter-{secrets.token_hex(4)}"

    def setup(self):
        """Ejecutar configuración automática"""
        print("=" * 60)
        print("  Auto-configuración de Pocket ID para MSG to EML Converter")
        print("=" * 60)
        print()

        # Paso 1: Obtener información de Pocket ID
        self.get_pocketid_info()

        # Paso 2: Validar conexión
        if not self.validate_connection():
            return False

        # Paso 3: Crear Cliente OIDC
        client = self.create_oidc_client()
        if not client:
            return False

        # Paso 4: Generar Client Secret
        client_secret = self.create_client_secret(client['id'])
        if not client_secret:
            return False

        # Paso 5: Guardar configuración en .env
        self.save_to_env(client['id'], client_secret)

        print()
        print("=" * 60)
        print("  Configuración completada exitosamente!")
        print("=" * 60)
        print()
        print("Las credenciales han sido guardadas en el archivo .env")
        print()
        print("Ahora puedes ejecutar la aplicación con:")
        print("  python app.py")
        print()

        return True

    def get_pocketid_info(self):
        """Obtener información de conexión a Pocket ID"""
        print("Paso 1: Información de Pocket ID")
        print()

        # URL de Pocket ID
        self.base_url = os.environ.get('OIDC_BASE_URL') or os.environ.get('POCKETID_URL')
        if not self.base_url:
            self.base_url = input("URL de tu instancia Pocket ID (ej: https://auth.ejemplo.com): ").strip()

        # Limpiar URL (quitar trailing slash)
        self.base_url = self.base_url.rstrip('/')

        # API Key
        self.api_key = os.environ.get('POCKETID_API_KEY')
        if not self.api_key:
            print()
            print("Necesitas un API Key de Pocket ID.")
            print("Para obtenerlo:")
            print("  1. Inicia sesión en Pocket ID como administrador")
            print("  2. Ve a Settings -> API Keys")
            print("  3. Crea un nuevo API Key")
            print()
            self.api_key = input("API Key de Pocket ID: ").strip()

        # URL de la aplicación
        self.app_url = os.environ.get('APP_URL')
        if not self.app_url:
            print()
            self.app_url = input("URL de tu aplicación (ej: https://msg-converter.onrender.com): ").strip()

        self.app_url = self.app_url.rstrip('/')

        print()
        print(f"  URL Pocket ID: {self.base_url}")
        print(f"  URL Aplicación: {self.app_url}")
        print()

    def api_request(self, method, endpoint, data=None):
        """Realizar petición a la API de Pocket ID"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Método no soportado: {method}")

            if response.status_code >= 400:
                print(f"  Error API ({response.status_code}): {response.text}")
                return None

            # Some endpoints return empty response
            if response.text:
                return response.json()
            return {}

        except requests.exceptions.RequestException as e:
            print(f"  Error en la petición API: {e}")
            return None

    def validate_connection(self):
        """Validar conexión con Pocket ID"""
        print("Paso 2: Validando conexión con Pocket ID...")

        # Test de conexión usando el endpoint de clientes
        result = self.api_request('GET', 'oidc/clients')
        if result is None:
            print()
            print("  No se pudo conectar con Pocket ID")
            print()
            print("  Verifica:")
            print("    - La URL de Pocket ID es correcta")
            print("    - El API Key es válido")
            print("    - Tienes conexión a internet")
            return False

        print("  Conexión exitosa con Pocket ID")
        print()
        return True

    def check_existing_client(self):
        """Verificar si ya existe un cliente con el mismo nombre"""
        clients = self.api_request('GET', 'oidc/clients')
        if clients and 'data' in clients:
            for client in clients['data']:
                if client.get('name') == self.app_name:
                    return client
        return None

    def create_oidc_client(self):
        """Crear Cliente OIDC en Pocket ID"""
        print("Paso 3: Creando Cliente OIDC")

        # Verificar si ya existe
        existing = self.check_existing_client()
        if existing:
            print(f"  Cliente '{self.app_name}' ya existe")
            use_existing = input("  ¿Usar el cliente existente? (s/n): ").strip().lower()
            if use_existing == 's':
                print(f"  Usando cliente existente: {existing['id']}")
                return existing
            else:
                # Generar nuevo ID único
                self.client_id = f"msg-eml-{secrets.token_hex(4)}"

        # Crear cliente
        callback_url = f"{self.app_url}/callback"
        
        client_data = {
            'id': self.client_id,
            'name': self.app_name,
            'callbackURLs': [callback_url],
            'logoutCallbackURLs': [self.app_url],
            'isPublic': False,
            'pkceEnabled': False,
            'requiresReauthentication': False,
            'launchURL': self.app_url,
            'isGroupRestricted': False,
            'credentials': {
                'federatedIdentities': []
            }
        }

        client = self.api_request('POST', 'oidc/clients', client_data)
        if not client:
            print("  Error al crear cliente")
            return None

        print(f"  Cliente creado exitosamente")
        print(f"    ID: {client.get('id', self.client_id)}")
        print(f"    Callback URL: {callback_url}")
        print()

        return client

    def create_client_secret(self, client_id):
        """Generar Client Secret para el cliente OIDC"""
        print("Paso 4: Generando Client Secret")

        result = self.api_request('POST', f'oidc/clients/{client_id}/secret')
        if not result:
            print("  Error al generar client secret")
            return None

        client_secret = result.get('secret') or result.get('clientSecret')
        if not client_secret:
            print("  No se recibió el client secret")
            print(f"  Respuesta: {result}")
            return None

        print("  Client Secret generado exitosamente")
        print()

        return client_secret

    def save_to_env(self, client_id, client_secret):
        """Guardar configuración en archivo .env"""
        print("Paso 5: Guardando configuración")

        env_file = '.env'

        # Crear .env si no existe
        if not os.path.exists(env_file):
            if os.path.exists('.env.example'):
                with open('.env.example', 'r') as f_example:
                    with open(env_file, 'w') as f_env:
                        f_env.write(f_example.read())
            else:
                with open(env_file, 'w') as f_env:
                    f_env.write("# MSG to EML Converter - Environment Variables\n")

        # Actualizar variables
        set_key(env_file, 'ENABLE_AUTH', 'true')
        set_key(env_file, 'OIDC_PROVIDER', 'pocketid')
        set_key(env_file, 'OIDC_BASE_URL', self.base_url)
        set_key(env_file, 'OIDC_CLIENT_ID', client_id)
        set_key(env_file, 'OIDC_CLIENT_SECRET', client_secret)

        # Guardar también el API Key para futuras configuraciones
        set_key(env_file, 'POCKETID_API_KEY', self.api_key)

        print(f"  Configuración guardada en {env_file}")
        print()
        print("  Variables configuradas:")
        print(f"    ENABLE_AUTH=true")
        print(f"    OIDC_PROVIDER=pocketid")
        print(f"    OIDC_BASE_URL={self.base_url}")
        print(f"    OIDC_CLIENT_ID={client_id}")
        print(f"    OIDC_CLIENT_SECRET=***")


class WebPocketIDSetup:
    """Setup de Pocket ID para uso desde la web (sin input interactivo)"""

    def __init__(self, pocketid_url, api_key, app_url):
        self.base_url = pocketid_url.rstrip('/')
        self.api_key = api_key
        self.app_url = app_url.rstrip('/')
        self.app_name = "MSG to EML Converter"
        self.client_id = f"msg-eml-converter-{secrets.token_hex(4)}"

    def api_request(self, method, endpoint, data=None):
        """Realizar petición a la API de Pocket ID"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=10)
            else:
                raise ValueError(f"Método no soportado: {method}")

            if response.status_code >= 400:
                return {'error': response.text, 'status_code': response.status_code}

            if response.text:
                return response.json()
            return {}

        except requests.exceptions.Timeout:
            return {'error': 'Connection timeout'}
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}

    def setup(self):
        """Ejecutar configuración y retornar resultado"""
        result = {
            'success': False,
            'error': None,
            'step': None,
            'client_id': None,
            'client_secret': None,
            'redirect_uri': f"{self.app_url}/callback"
        }

        # Paso 1: Validar conexión
        test = self.api_request('GET', 'oidc/clients')
        if isinstance(test, dict) and 'error' in test:
            result['error'] = f"No se pudo conectar con Pocket ID: {test['error']}"
            result['step'] = 'connection'
            return result

        # Paso 2: Verificar si ya existe
        existing_client = None
        if test and 'data' in test:
            for client in test['data']:
                if client.get('name') == self.app_name:
                    existing_client = client
                    break

        # Paso 3: Crear o usar cliente existente
        if existing_client:
            client = existing_client
            result['client_message'] = 'Using existing client'
        else:
            client_data = {
                'id': self.client_id,
                'name': self.app_name,
                'callbackURLs': [result['redirect_uri']],
                'logoutCallbackURLs': [self.app_url],
                'isPublic': False,
                'pkceEnabled': False,
                'requiresReauthentication': False,
                'launchURL': self.app_url,
                'isGroupRestricted': False,
                'credentials': {'federatedIdentities': []}
            }

            client = self.api_request('POST', 'oidc/clients', client_data)
            if isinstance(client, dict) and 'error' in client:
                result['error'] = f"Error creating client: {client['error']}"
                result['step'] = 'create_client'
                return result
            result['client_message'] = 'Client created successfully'

        client_id = client.get('id', self.client_id)
        result['client_id'] = client_id

        # Paso 4: Generar secret
        secret_response = self.api_request('POST', f'oidc/clients/{client_id}/secret')
        if isinstance(secret_response, dict) and 'error' in secret_response:
            result['error'] = f"Error generating secret: {secret_response['error']}"
            result['step'] = 'create_secret'
            return result

        client_secret = secret_response.get('secret') or secret_response.get('clientSecret')
        if not client_secret:
            result['error'] = 'No client secret received from API'
            result['step'] = 'create_secret'
            return result

        result['client_secret'] = client_secret
        result['success'] = True

        return result


def main():
    """Función principal"""
    setup = PocketIDAutoSetup()

    if setup.setup():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
