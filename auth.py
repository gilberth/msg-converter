#!/usr/bin/env python3
"""
Authentication module for Authentik OAuth2/OIDC
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
        self.enabled = os.environ.get('ENABLE_AUTH', 'false').lower() == 'true'

        if not self.enabled:
            print("Authentication is DISABLED")
            return

        # Configuration
        self.base_url = os.environ.get('AUTHENTIK_BASE_URL', '')
        self.client_id = os.environ.get('AUTHENTIK_CLIENT_ID', '')
        self.client_secret = os.environ.get('AUTHENTIK_CLIENT_SECRET', '')
        self.redirect_uri = os.environ.get('AUTHENTIK_REDIRECT_URI', '')
        self.slug = os.environ.get('AUTHENTIK_SLUG', '')  # Application slug for OIDC endpoint
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
        # Note: The OIDC discovery URL uses the application slug, not the client_id
        # Note: Manual configuration to avoid JWKS validation issues when using HS256
        self.authentik = self.oauth.register(
            name='authentik',
            client_id=self.client_id,
            client_secret=self.client_secret,
            # Use manual endpoint configuration instead of server_metadata_url
            # to avoid automatic JWKS fetching and validation
            authorize_url=f'{self.base_url}/application/o/authorize/',
            access_token_url=f'{self.base_url}/application/o/token/',
            userinfo_endpoint=f'{self.base_url}/application/o/userinfo/',
            client_kwargs={
                'scope': 'openid email profile',
                'code_challenge_method': 'S256',  # Enable PKCE
            }
        )

        print(f"Authentication ENABLED - Authentik URL: {self.base_url}")

    def login_required(self, f):
        """Decorator to require authentication for a route"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not self.enabled:
                # Authentication disabled, allow access
                return f(*args, **kwargs)

            if not self.is_authenticated():
                # Store the original URL to redirect after login
                session['next'] = request.url
                return redirect(url_for('login'))

            # Check session expiration
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
            # No group restrictions
            return True

        user_groups = user_info.get('groups', [])

        # Check if user is in any of the allowed groups
        for group in self.allowed_groups:
            if group in user_groups:
                return True

        return False

    def get_current_user(self):
        """Get current authenticated user info"""
        return session.get('user')


def init_auth_routes(app, auth):
    """Initialize authentication routes"""

    @app.route('/login')
    def login():
        """Initiate OAuth2 login flow"""
        if not auth.enabled:
            return redirect(url_for('index'))

        redirect_uri = auth.redirect_uri
        return auth.authentik.authorize_redirect(redirect_uri)

    @app.route('/callback')
    def callback():
        """OAuth2 callback handler"""
        if not auth.enabled:
            return redirect(url_for('index'))

        try:
            # Get access token
            # Note: This may fail with "Invalid key set format" if JWKS parsing fails
            # We use userinfo endpoint as fallback which is more reliable
            token = auth.authentik.authorize_access_token()

            # Get user info from userinfo endpoint (more reliable than parsing id_token)
            user_info = auth.authentik.userinfo(token=token)

            # Check group membership if configured
            if auth.allowed_groups and not auth.check_group_membership(user_info):
                return jsonify({
                    'error': 'Access denied',
                    'message': 'You are not authorized to access this application. Please contact your administrator.'
                }), 403

            # Calculate session expiration
            session_lifetime = int(os.environ.get('SESSION_LIFETIME_HOURS', '24'))
            expires_at = datetime.now() + timedelta(hours=session_lifetime)

            # Store user info in session
            session['user'] = {
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'preferred_username': user_info.get('preferred_username'),
                'groups': user_info.get('groups', [])
            }
            session['token'] = token
            session['expires_at'] = expires_at.isoformat()

            # Redirect to original URL or home
            next_url = session.pop('next', None)
            return redirect(next_url or url_for('index'))

        except ValueError as e:
            # Handle specific JWKS parsing errors
            error_msg = str(e)
            print(f"Authentication error (ValueError): {error_msg}")

            if "Invalid key set format" in error_msg:
                return jsonify({
                    'error': 'Authentication failed',
                    'message': 'JWKS validation error. Please ensure Authentik is properly configured.',
                    'detail': 'The OAuth provider returned an invalid key format. Check that AUTHENTIK_SLUG is correct.',
                    'troubleshooting': {
                        'check_slug': 'Verify AUTHENTIK_SLUG matches your application slug in Authentik',
                        'check_provider': 'Ensure the OAuth2 provider is correctly configured in Authentik',
                        'check_url': f'Verify this URL is accessible: {auth.base_url}/application/o/{auth.slug}/.well-known/openid-configuration'
                    }
                }), 500

            return jsonify({
                'error': 'Authentication failed',
                'message': str(e)
            }), 500

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

        # Redirect to Authentik logout
        logout_url = f"{auth.base_url}/application/o/{auth.client_id}/end-session/"
        return redirect(logout_url)

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
            'user': auth.get_current_user()
        })
