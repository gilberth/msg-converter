#!/usr/bin/env python3
"""
Web-based setup wizard for Authentik configuration
"""

import os
import requests
from dotenv import set_key


class WebAuthentikSetup:
    """Web-based Authentik setup handler"""

    def __init__(self, base_url, api_token, app_url):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.app_url = app_url.rstrip('/')
        self.app_name = "MSG to EML Converter"
        self.app_slug = "msg-eml-converter"

    def api_request(self, method, endpoint, data=None):
        """Make API request to Authentik"""
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
            return {'error': 'Request timeout. Check your Authentik URL and network connection.'}
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = error_detail.get('detail', error_msg)
                except:
                    error_msg = e.response.text if e.response.text else error_msg
            return {'error': error_msg}

    def validate_connection(self):
        """Validate connection to Authentik"""
        result = self.api_request('GET', 'core/applications/')
        if result and 'error' not in result:
            return {'success': True}
        return result

    def get_default_flow(self):
        """Get default authentication flow"""
        flows = self.api_request('GET', 'flows/instances/')
        if flows and 'error' not in flows:
            for flow in flows.get('results', []):
                if 'authentication' in flow.get('slug', '').lower():
                    return flow['pk']
            if flows.get('results'):
                return flows['results'][0]['pk']
        return None

    def create_oauth_provider(self):
        """Create OAuth2 provider"""
        # Check if exists
        providers = self.api_request('GET', 'providers/oauth2/')
        if providers and 'error' not in providers:
            for provider in providers.get('results', []):
                if provider.get('name') == self.app_name:
                    return {
                        'success': True,
                        'provider': provider,
                        'message': 'Using existing provider'
                    }

        # Get default flow
        flow = self.get_default_flow()
        if not flow:
            return {'error': 'Could not find authentication flow'}

        # Create provider
        provider_data = {
            'name': self.app_name,
            'authorization_flow': flow,
            'client_type': 'confidential',
            'redirect_uris': f"{self.app_url}/callback",
            'sub_mode': 'hashed_user_id',
            'include_claims_in_id_token': True,
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
        """Create application"""
        # Check if exists
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
            'provider': provider_pk,
            'meta_launch_url': self.app_url,
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
        """Execute full setup"""
        # Step 1: Validate connection
        validation = self.validate_connection()
        if 'error' in validation:
            return {
                'success': False,
                'step': 'validation',
                'error': f"Connection failed: {validation['error']}"
            }

        # Step 2: Create provider
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

        # Step 4: Save to environment
        env_file = '.env'
        if not os.path.exists(env_file):
            # Create from example
            if os.path.exists('.env.example'):
                import shutil
                shutil.copy('.env.example', env_file)
            else:
                # Create minimal .env
                with open(env_file, 'w') as f:
                    f.write('')

        set_key(env_file, 'ENABLE_AUTH', 'true')
        set_key(env_file, 'AUTHENTIK_BASE_URL', self.base_url)
        set_key(env_file, 'AUTHENTIK_CLIENT_ID', provider['client_id'])
        set_key(env_file, 'AUTHENTIK_CLIENT_SECRET', provider['client_secret'])
        set_key(env_file, 'AUTHENTIK_REDIRECT_URI', f"{self.app_url}/callback")
        set_key(env_file, 'AUTHENTIK_API_TOKEN', self.api_token)

        return {
            'success': True,
            'client_id': provider['client_id'],
            'client_secret': provider['client_secret'][:10] + '...',  # Truncate for display
            'redirect_uri': f"{self.app_url}/callback",
            'provider_message': provider_result['message'],
            'app_message': app_result['message']
        }
