#!/usr/bin/env python3
"""
Generic OIDC Authentication Module

Supports any OIDC-compliant provider including:
- Pocket ID
- Authentik
- Keycloak
- Google
- Azure AD
- Auth0
- And more...
"""

import os
import json
import base64
import requests
from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from authlib.integrations.flask_client import OAuth
from datetime import datetime, timedelta


class OIDCAuth:
    """Generic OIDC authentication handler"""

    # Known provider configurations (endpoints relative to base URL)
    PROVIDER_PRESETS = {
        'pocketid': {
            'discovery_path': '/.well-known/openid-configuration',
            'scopes': 'openid email profile',
            'logout_path': '/oidc/logout',
        },
        'authentik': {
            'authorize_path': '/application/o/authorize/',
            'token_path': '/application/o/token/',
            'userinfo_path': '/application/o/userinfo/',
            'logout_path': '/application/o/{slug}/end-session/',
            'scopes': 'openid email profile',
        },
        'keycloak': {
            'discovery_path': '/realms/{realm}/.well-known/openid-configuration',
            'scopes': 'openid email profile',
        },
        'google': {
            'discovery_url': 'https://accounts.google.com/.well-known/openid-configuration',
            'scopes': 'openid email profile',
        },
        'azure': {
            'discovery_path': '/{tenant}/v2.0/.well-known/openid-configuration',
            'scopes': 'openid email profile',
        },
        'auth0': {
            'discovery_path': '/.well-known/openid-configuration',
            'scopes': 'openid email profile',
        },
        'generic': {
            'discovery_path': '/.well-known/openid-configuration',
            'scopes': 'openid email profile',
        }
    }

    def __init__(self, app):
        self.app = app
        self.enabled = os.environ.get('ENABLE_AUTH', 'false').lower() == 'true'

        if not self.enabled:
            print("Authentication is DISABLED")
            return

        # Load configuration
        self._load_config()
        
        # Initialize OAuth
        self._init_oauth()

        print(f"Authentication ENABLED - Provider: {self.provider_type}")
        print(f"  Base URL: {self.base_url}")

    def _load_config(self):
        """Load OIDC configuration from environment variables"""
        # Determine provider type
        self.provider_type = os.environ.get('OIDC_PROVIDER', 'generic').lower()
        
        # Support legacy Authentik variables for backwards compatibility
        if self._has_legacy_authentik_config():
            print("Detected legacy Authentik configuration, migrating...")
            self._migrate_authentik_config()
        
        # Core OIDC settings
        self.base_url = os.environ.get('OIDC_BASE_URL', '').rstrip('/')
        self.client_id = os.environ.get('OIDC_CLIENT_ID', '')
        self.client_secret = os.environ.get('OIDC_CLIENT_SECRET', '')
        self.scopes = os.environ.get('OIDC_SCOPES', 'openid email profile')
        
        # Optional settings
        self.slug = os.environ.get('OIDC_SLUG', '')  # For Authentik
        self.realm = os.environ.get('OIDC_REALM', '')  # For Keycloak
        self.tenant = os.environ.get('OIDC_TENANT', 'common')  # For Azure
        
        # Access control
        self.allowed_groups = os.environ.get('OIDC_ALLOWED_GROUPS', '').split(',')
        self.allowed_groups = [g.strip() for g in self.allowed_groups if g.strip()]
        
        # Session settings
        self.session_lifetime = int(os.environ.get('SESSION_LIFETIME_HOURS', '24'))
        
        # Custom endpoints (override auto-discovery)
        self.custom_discovery_url = os.environ.get('OIDC_DISCOVERY_URL', '')
        self.custom_authorize_url = os.environ.get('OIDC_AUTHORIZE_URL', '')
        self.custom_token_url = os.environ.get('OIDC_TOKEN_URL', '')
        self.custom_userinfo_url = os.environ.get('OIDC_USERINFO_URL', '')
        self.custom_logout_url = os.environ.get('OIDC_LOGOUT_URL', '')
        
        # Validate required settings
        if not all([self.base_url, self.client_id, self.client_secret]):
            raise ValueError(
                "Missing OIDC configuration. Required: "
                "OIDC_BASE_URL, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET"
            )

    def _has_legacy_authentik_config(self):
        """Check if legacy Authentik environment variables are present"""
        return (
            os.environ.get('AUTHENTIK_BASE_URL') and 
            os.environ.get('AUTHENTIK_CLIENT_ID') and
            not os.environ.get('OIDC_BASE_URL')
        )

    def _migrate_authentik_config(self):
        """Migrate legacy Authentik config to generic OIDC format"""
        # Map old variables to new ones (in memory only)
        os.environ.setdefault('OIDC_PROVIDER', 'authentik')
        os.environ.setdefault('OIDC_BASE_URL', os.environ.get('AUTHENTIK_BASE_URL', ''))
        os.environ.setdefault('OIDC_CLIENT_ID', os.environ.get('AUTHENTIK_CLIENT_ID', ''))
        os.environ.setdefault('OIDC_CLIENT_SECRET', os.environ.get('AUTHENTIK_CLIENT_SECRET', ''))
        os.environ.setdefault('OIDC_SLUG', os.environ.get('AUTHENTIK_SLUG', ''))
        os.environ.setdefault('OIDC_ALLOWED_GROUPS', os.environ.get('AUTHENTIK_ALLOWED_GROUPS', ''))

    def _get_endpoints(self):
        """Get OIDC endpoints based on provider type"""
        preset = self.PROVIDER_PRESETS.get(self.provider_type, self.PROVIDER_PRESETS['generic'])
        
        endpoints = {
            'discovery_url': None,
            'authorize_url': None,
            'token_url': None,
            'userinfo_url': None,
            'logout_url': None,
        }
        
        # Custom endpoints take priority
        if self.custom_discovery_url:
            endpoints['discovery_url'] = self.custom_discovery_url
        elif self.custom_authorize_url and self.custom_token_url:
            # Manual endpoint configuration
            endpoints['authorize_url'] = self.custom_authorize_url
            endpoints['token_url'] = self.custom_token_url
            endpoints['userinfo_url'] = self.custom_userinfo_url
        else:
            # Use preset configuration
            if 'discovery_url' in preset:
                endpoints['discovery_url'] = preset['discovery_url']
            elif 'discovery_path' in preset:
                path = preset['discovery_path'].format(
                    slug=self.slug,
                    realm=self.realm,
                    tenant=self.tenant
                )
                endpoints['discovery_url'] = f"{self.base_url}{path}"
            elif 'authorize_path' in preset:
                # Manual paths for providers without discovery
                endpoints['authorize_url'] = f"{self.base_url}{preset['authorize_path']}"
                endpoints['token_url'] = f"{self.base_url}{preset['token_path']}"
                endpoints['userinfo_url'] = f"{self.base_url}{preset['userinfo_path']}"
        
        # Logout URL
        if self.custom_logout_url:
            endpoints['logout_url'] = self.custom_logout_url
        elif 'logout_path' in preset:
            path = preset['logout_path'].format(slug=self.slug, realm=self.realm)
            endpoints['logout_url'] = f"{self.base_url}{path}"
        
        return endpoints

    def _init_oauth(self):
        """Initialize OAuth client"""
        self.oauth = OAuth(self.app)
        endpoints = self._get_endpoints()
        
        # Store endpoints for later use
        self.endpoints = endpoints
        
        # Register OAuth client
        client_kwargs = {'scope': self.scopes}
        
        register_args = {
            'name': 'oidc_provider',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'client_kwargs': client_kwargs,
        }
        
        # Use discovery URL if available (preferred - automatic configuration)
        if endpoints['discovery_url']:
            register_args['server_metadata_url'] = endpoints['discovery_url']
            print(f"  Using OIDC Discovery: {endpoints['discovery_url']}")
        else:
            # Manual endpoint configuration
            register_args['authorize_url'] = endpoints['authorize_url']
            register_args['access_token_url'] = endpoints['token_url']
            register_args['userinfo_endpoint'] = endpoints['userinfo_url']
            print(f"  Using manual endpoints")
        
        self.oidc = self.oauth.register(**register_args)

    def login_required(self, f):
        """Decorator to require authentication for a route"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.enabled:
                return f(*args, **kwargs)

            if not self.is_authenticated():
                session['next'] = request.url
                return redirect(url_for('login'))

            if self.is_session_expired():
                session.clear()
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
            return True
        
        user_groups = user_info.get('groups', [])
        for group in self.allowed_groups:
            if group in user_groups:
                return True
        return False

    def get_current_user(self):
        """Get current authenticated user info"""
        return session.get('user')

    def _decode_id_token(self, id_token):
        """Decode JWT id_token without verification (already validated by HTTPS + client auth)"""
        try:
            parts = id_token.split('.')
            if len(parts) >= 2:
                payload = parts[1]
                # Add padding if needed
                payload += '=' * (4 - len(payload) % 4)
                return json.loads(base64.urlsafe_b64decode(payload))
        except Exception as e:
            print(f"Warning: Failed to decode id_token: {e}")
        return None

    def _get_user_info_from_token(self, token):
        """Extract user info from token response"""
        user_info = None
        
        # Try id_token first (standard OIDC)
        if 'id_token' in token:
            user_info = self._decode_id_token(token['id_token'])
            if user_info:
                print("User info extracted from id_token")
                return user_info
        
        # Fallback to userinfo endpoint
        access_token = token.get('access_token')
        if access_token:
            try:
                # Get userinfo endpoint
                userinfo_url = None
                if self.endpoints.get('userinfo_url'):
                    userinfo_url = self.endpoints['userinfo_url']
                elif hasattr(self.oidc, 'userinfo_endpoint'):
                    userinfo_url = self.oidc.userinfo_endpoint
                else:
                    # Try to get from server metadata
                    userinfo_url = f"{self.base_url}/userinfo"
                
                response = requests.get(
                    userinfo_url,
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                
                if response.status_code == 200:
                    user_info = response.json()
                    print("User info fetched from userinfo endpoint")
                else:
                    print(f"Userinfo request failed: {response.status_code}")
            except Exception as e:
                print(f"Error fetching userinfo: {e}")
        
        return user_info


def init_oidc_routes(app, auth):
    """Initialize OIDC authentication routes"""

    @app.route('/login')
    def login():
        """Initiate OAuth2/OIDC login flow"""
        if not auth.enabled:
            return redirect(url_for('index'))
        
        redirect_uri = url_for('callback', _external=True)
        return auth.oidc.authorize_redirect(redirect_uri)

    @app.route('/callback')
    def callback():
        """OAuth2/OIDC callback handler"""
        if not auth.enabled:
            return redirect(url_for('index'))

        try:
            # Get authorization code
            code = request.args.get('code')
            if not code:
                return jsonify({
                    'error': 'Authentication failed',
                    'message': 'No authorization code received'
                }), 400

            # Exchange code for token
            redirect_uri = url_for('callback', _external=True)
            
            # Try using authlib's token exchange first
            try:
                token = auth.oidc.authorize_access_token()
            except Exception as e:
                print(f"Authlib token exchange failed: {e}, trying manual exchange...")
                # Manual token exchange as fallback
                token = _manual_token_exchange(auth, code, redirect_uri)
            
            if not token:
                return jsonify({
                    'error': 'Token exchange failed',
                    'message': 'Could not obtain access token'
                }), 400

            # Get user info
            user_info = auth._get_user_info_from_token(token)
            
            if not user_info:
                return jsonify({
                    'error': 'Failed to get user info',
                    'message': 'Could not retrieve user information from provider'
                }), 400

            # Check group membership
            if auth.allowed_groups and not auth.check_group_membership(user_info):
                return jsonify({
                    'error': 'Access denied',
                    'message': 'You are not authorized to access this application.'
                }), 403

            # Calculate session expiration
            expires_at = datetime.now() + timedelta(hours=auth.session_lifetime)

            # Store user in session
            display_name = (
                user_info.get('name') or 
                user_info.get('preferred_username') or 
                user_info.get('email', 'User')
            )

            session['user'] = {
                'email': user_info.get('email'),
                'name': display_name,
                'preferred_username': user_info.get('preferred_username'),
                'groups': user_info.get('groups', []),
                'sub': user_info.get('sub'),
            }
            session['expires_at'] = expires_at.isoformat()
            session['authenticated'] = True

            # Redirect to original URL or home
            next_url = session.pop('next', None)
            return redirect(next_url or url_for('index'))

        except Exception as e:
            print(f"Authentication error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'error': 'Authentication failed',
                'message': str(e)
            }), 500

    @app.route('/logout')
    def logout():
        """Logout user"""
        if not auth.enabled:
            return redirect(url_for('index'))

        # Clear session
        session.clear()

        # Redirect to provider logout if available
        if auth.endpoints.get('logout_url'):
            return redirect(auth.endpoints['logout_url'])
        
        return redirect(url_for('index'))

    @app.route('/auth/status')
    def auth_status():
        """Check authentication status"""
        if not auth.enabled:
            return jsonify({
                'enabled': False,
                'authenticated': False,
                'message': 'Authentication is disabled'
            })

        return jsonify({
            'enabled': True,
            'authenticated': auth.is_authenticated(),
            'user': auth.get_current_user(),
            'provider': auth.provider_type
        })

    @app.route('/auth/debug')
    def auth_debug():
        """Debug endpoint for OAuth2/OIDC configuration"""
        if not auth.enabled:
            return jsonify({'error': 'Authentication is disabled'})

        callback_url = url_for('callback', _external=True)

        return jsonify({
            'provider': auth.provider_type,
            'callback_url': callback_url,
            'base_url': auth.base_url,
            'client_id_preview': f'{auth.client_id[:15]}...' if len(auth.client_id) > 15 else auth.client_id,
            'scopes': auth.scopes,
            'endpoints': {
                'discovery': auth.endpoints.get('discovery_url'),
                'authorize': auth.endpoints.get('authorize_url'),
                'token': auth.endpoints.get('token_url'),
                'userinfo': auth.endpoints.get('userinfo_url'),
                'logout': auth.endpoints.get('logout_url'),
            },
            'flask_config': {
                'protocol': request.scheme,
                'host': request.host,
            },
            'important': f'Ensure your OIDC provider has this exact callback URL: {callback_url}'
        })


def _manual_token_exchange(auth, code, redirect_uri):
    """Manual token exchange as fallback when authlib fails"""
    try:
        # Determine token endpoint
        token_url = auth.endpoints.get('token_url')
        if not token_url:
            # Try to get from discovery
            token_url = f"{auth.base_url}/oauth/token"
        
        response = requests.post(
            token_url,
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri,
                'client_id': auth.client_id,
                'client_secret': auth.client_secret,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Token exchange failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Manual token exchange error: {e}")
        return None
