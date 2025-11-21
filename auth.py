#!/usr/bin/env python3
"""
Authentication module for Authentik OAuth2/OIDC
"""

import os
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
        # Note: PKCE disabled because we use manual token exchange with requests
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
                # PKCE disabled - manual token exchange with requests doesn't support it
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

        # Use url_for to generate callback URL dynamically
        # This ensures it matches exactly with what we use in the callback
        redirect_uri = url_for('callback', _external=True)
        return auth.authentik.authorize_redirect(redirect_uri)

    @app.route('/callback')
    def callback():
        """OAuth2 callback handler"""
        if not auth.enabled:
            return redirect(url_for('index'))

        try:
            # Get authorization code from callback URL
            code = request.args.get('code')
            if not code:
                return jsonify({
                    'error': 'Authentication failed',
                    'message': 'No authorization code received'
                }), 400

            # Exchange authorization code for access token using requests directly
            # This avoids Authlib's automatic id_token parsing which fails with empty JWKS (HS256)
            # IMPORTANT: redirect_uri must match exactly what was used in authorize step
            redirect_uri_used = url_for('callback', _external=True)

            token_response = requests.post(
                auth.authentik.access_token_url,
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': redirect_uri_used,
                    'client_id': auth.client_id,
                    'client_secret': auth.client_secret
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            if token_response.status_code != 200:
                error_detail = token_response.json() if token_response.text else {}
                return jsonify({
                    'error': 'Token exchange failed',
                    'message': f'Failed to exchange authorization code: {token_response.text}',
                    'debug_info': {
                        'redirect_uri_sent': redirect_uri_used,
                        'status_code': token_response.status_code,
                        'authentik_error': error_detail.get('error', 'unknown'),
                        'authentik_description': error_detail.get('error_description', 'No description'),
                        'possible_causes': [
                            'Redirect URI in Authentik does not EXACTLY match: ' + redirect_uri_used,
                            'Authorization code expired (codes expire after ~60 seconds)',
                            'Authorization code already used (codes are single-use)',
                            'Client credentials (client_id/client_secret) incorrect'
                        ],
                        'action_required': f'Go to Authentik and verify redirect_uris contains EXACTLY: {redirect_uri_used}'
                    }
                }), token_response.status_code

            token = token_response.json()

            # Debug: Log token info (without exposing the actual token)
            print(f"Token exchange successful. Token type: {token.get('token_type', 'unknown')}")
            print(f"Access token present: {'access_token' in token}")
            print(f"Token scope: {token.get('scope', 'not provided')}")

            # Get user info from userinfo endpoint using the access token
            userinfo_url = f'{auth.base_url}/application/o/userinfo/'
            print(f"Calling userinfo endpoint: {userinfo_url}")

            userinfo_response = requests.get(
                userinfo_url,
                headers={'Authorization': f'Bearer {token["access_token"]}'}
            )

            print(f"Userinfo response status: {userinfo_response.status_code}")
            print(f"Userinfo response headers: {dict(userinfo_response.headers)}")

            if userinfo_response.status_code != 200:
                error_details = {
                    'status_code': userinfo_response.status_code,
                    'response_text': userinfo_response.text,
                    'response_headers': dict(userinfo_response.headers),
                    'endpoint_used': userinfo_url,
                    'token_type': token.get('token_type', 'unknown'),
                    'token_scope': token.get('scope', 'not provided')
                }

                return jsonify({
                    'error': 'Failed to get user info',
                    'message': f'Userinfo endpoint returned status {userinfo_response.status_code}',
                    'details': error_details
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

    @app.route('/auth/debug')
    def auth_debug():
        """Debug endpoint to show OAuth2 configuration and redirect_uri"""
        if not auth.enabled:
            return jsonify({'error': 'Authentication is disabled'})

        callback_url = url_for('callback', _external=True)

        debug_info = {
            'CRITICAL_CHECK': {
                'flask_generates_this_url': callback_url,
                'authentik_must_have_EXACTLY_this': callback_url,
                'case_sensitive': True,
                'must_match_exactly': 'YES - Even one character difference causes invalid_grant',
            },
            'flask_environment': {
                'protocol': request.scheme,
                'host': request.host,
                'is_secure': request.is_secure,
                'url_root': request.url_root,
                'callback_endpoint': url_for('callback', _external=True),
            },
            'authentik_config': {
                'base_url': auth.base_url,
                'client_id': f'{auth.client_id[:15]}...',
                'slug': auth.slug,
                'authorize_url': f'{auth.base_url}/application/o/authorize/',
                'token_url': f'{auth.base_url}/application/o/token/',
                'userinfo_url': f'{auth.base_url}/application/o/userinfo/',
            },
            'fix_instructions': {
                'step_1': f'Go to: {auth.base_url}/if/admin/',
                'step_2': 'Navigate to: Applications → Applications',
                'step_3': 'Find your app (MSG to EML Converter)',
                'step_4': 'Click on it → Go to Provider tab',
                'step_5': f'Add/Edit Redirect URI to EXACTLY: {callback_url}',
                'step_6': 'Make sure matching_mode is "strict"',
                'step_7': 'Save and try login again',
            },
            'authentik_2024_note': 'Authentik 2024.8.5+ and 2024.10.3+ use STRICT matching (CVE-2024-52289 fix)',
            'common_mistakes': [
                'http:// vs https://',
                'Trailing slash: /callback vs /callback/',
                'Case mismatch: /Callback vs /callback',
                'Wrong domain',
                'Port number mismatch'
            ]
        }

        return jsonify(debug_info)
