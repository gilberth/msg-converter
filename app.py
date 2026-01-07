#!/usr/bin/env python3
"""
MSG to EML Converter - Web Application

Flask web application for converting MSG files to EML format.
"""

import os
import shutil
import uuid
from datetime import datetime, timedelta
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from msg_to_eml_converter import MSGToEMLConverter
import threading
import time
from dotenv import load_dotenv
from version import __version__, __version_name__

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Fix for running behind proxy (Render, Heroku, etc.)
# This ensures Flask correctly detects HTTPS protocol and generates proper URLs
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['ALLOWED_EXTENSIONS'] = {'msg'}

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Initialize converter
converter = MSGToEMLConverter()

# Initialize authentication (Generic OIDC - supports Pocket ID, Authentik, Keycloak, etc.)
from auth_oidc import OIDCAuth, init_oidc_routes
try:
    auth = OIDCAuth(app)
    init_oidc_routes(app, auth)
except Exception as e:
    print(f"Warning: Authentication initialization failed: {e}")
    print("Running without authentication")
    # Create a dummy auth object
    class DummyAuth:
        enabled = False
        def login_required(self, f):
            return f
        def is_authenticated(self):
            return False
        def get_current_user(self):
            return None
    auth = DummyAuth()

# Track conversions
conversions = {}

# Setup wizard routes
@app.route('/setup')
def setup_page():
    """Setup wizard page"""
    # Check if already configured
    if auth.enabled:
        return render_template('setup.html', already_configured=True,
                             version=__version__, version_name=__version_name__)
    return render_template('setup.html', already_configured=False,
                         version=__version__, version_name=__version_name__)

@app.route('/setup/configure', methods=['POST'])
def setup_configure():
    """Handle setup configuration for multiple OIDC providers"""
    try:
        data = request.json
        provider = data.get('provider', '').strip()
        app_url = data.get('app_url', '').strip().rstrip('/')

        if not provider or not app_url:
            return jsonify({
                'success': False,
                'error': 'Provider and app_url are required'
            }), 400

        result = None
        env_vars = ""

        # Pocket ID auto-configuration
        if provider == 'pocketid':
            from pocketid_auto_setup import WebPocketIDSetup

            pocketid_url = data.get('pocketid_url', '').strip()
            api_key = data.get('api_key', '').strip()

            if not pocketid_url or not api_key:
                return jsonify({
                    'success': False,
                    'error': 'Pocket ID URL and API Key are required'
                }), 400

            setup = WebPocketIDSetup(pocketid_url, api_key, app_url)
            result = setup.setup()

            if result.get('success'):
                env_vars = f"""ENABLE_AUTH=true
OIDC_PROVIDER=pocketid
OIDC_BASE_URL={pocketid_url}
OIDC_CLIENT_ID={result.get('client_id')}
OIDC_CLIENT_SECRET={result.get('client_secret')}"""

                return jsonify({
                    'success': True,
                    'details': {
                        'provider': 'Pocket ID',
                        'client_id': result.get('client_id'),
                        'redirect_uri': result.get('redirect_uri'),
                    },
                    'env_vars': env_vars
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Setup failed'),
                    'step': result.get('step')
                }), 400

        # Authentik auto-configuration
        elif provider == 'authentik':
            from web_setup import WebAuthentikSetup

            authentik_url = data.get('authentik_url', '').strip()
            api_token = data.get('api_token', '').strip()

            if not authentik_url or not api_token:
                return jsonify({
                    'success': False,
                    'error': 'Authentik URL and API Token are required'
                }), 400

            setup = WebAuthentikSetup(authentik_url, api_token, app_url)
            result = setup.setup()

            if result.get('success'):
                env_vars = f"""ENABLE_AUTH=true
OIDC_PROVIDER=authentik
OIDC_BASE_URL={authentik_url}
OIDC_CLIENT_ID={result.get('client_id')}
OIDC_CLIENT_SECRET={result.get('client_secret')}
OIDC_SLUG={result.get('slug', 'msg-eml-converter')}"""

                return jsonify({
                    'success': True,
                    'details': {
                        'provider': 'Authentik',
                        'client_id': result.get('client_id'),
                        'redirect_uri': result.get('redirect_uri'),
                        'provider_message': result.get('provider_message'),
                        'app_message': result.get('app_message')
                    },
                    'env_vars': env_vars
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Setup failed'),
                    'step': result.get('step')
                }), 400

        # Manual configuration (just generate env vars)
        elif provider == 'manual':
            manual_provider = data.get('manual_provider', 'generic').strip()
            base_url = data.get('base_url', '').strip()
            client_id = data.get('client_id', '').strip()
            client_secret = data.get('client_secret', '').strip()
            slug = data.get('slug', '').strip()

            if not base_url or not client_id or not client_secret:
                return jsonify({
                    'success': False,
                    'error': 'Base URL, Client ID and Client Secret are required'
                }), 400

            env_vars = f"""ENABLE_AUTH=true
OIDC_PROVIDER={manual_provider}
OIDC_BASE_URL={base_url}
OIDC_CLIENT_ID={client_id}
OIDC_CLIENT_SECRET={client_secret}"""

            if slug and manual_provider == 'authentik':
                env_vars += f"\nOIDC_SLUG={slug}"

            return jsonify({
                'success': True,
                'details': {
                    'provider': manual_provider.title(),
                    'client_id': client_id,
                    'redirect_uri': f"{app_url}/callback",
                },
                'env_vars': env_vars
            })

        else:
            return jsonify({
                'success': False,
                'error': f'Unknown provider: {provider}'
            }), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def cleanup_old_files():
    """Clean up files older than 1 hour"""
    while True:
        try:
            cutoff_time = datetime.now() - timedelta(hours=1)

            for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)
                    if os.path.isfile(filepath):
                        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                        if file_time < cutoff_time:
                            os.remove(filepath)
                            print(f"Cleaned up old file: {filepath}")
        except Exception as e:
            print(f"Error during cleanup: {e}")

        # Run cleanup every 30 minutes
        time.sleep(1800)


# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()


@app.route('/')
def index():
    """Main page - shows welcome screen if not authenticated"""
    # If authentication is enabled and user is not logged in, show welcome page
    if auth.enabled and not auth.is_authenticated():
        return render_template('welcome.html',
                             auth_enabled=auth.enabled,
                             version=__version__,
                             version_name=__version_name__)

    # User is authenticated or auth is disabled - show converter
    user = auth.get_current_user() if auth.enabled else None
    return render_template('index.html', user=user, auth_enabled=auth.enabled,
                         version=__version__, version_name=__version_name__)


@app.route('/preview', methods=['POST'])
@auth.login_required
def preview_file():
    """Preview MSG file without converting"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No se seleccionó archivo'}), 400

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Tipo de archivo no permitido. Solo se aceptan archivos .msg'}), 400

    # Generate unique filename
    original_filename = secure_filename(file.filename)
    unique_id = str(uuid.uuid4())
    msg_filename = f"{unique_id}_{original_filename}"
    msg_path = os.path.join(app.config['UPLOAD_FOLDER'], msg_filename)

    try:
        # Save uploaded file temporarily
        file.save(msg_path)

        # Get preview data
        preview_data = converter.preview_file(msg_path)

        return jsonify({
            'success': True,
            'preview': preview_data
        })

    except FileNotFoundError as e:
        print(f"Preview error - File not found: {e}")
        return jsonify({
            'success': False,
            'error': 'Archivo no encontrado'
        }), 404
    except ValueError as e:
        print(f"Preview error - Invalid file: {e}")
        return jsonify({
            'success': False,
            'error': 'Archivo MSG inválido'
        }), 400
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"Preview error: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Error al procesar archivo: {str(e)}'
        }), 500
    finally:
        # Clean up uploaded MSG file
        if os.path.exists(msg_path):
            try:
                os.remove(msg_path)
            except Exception as e:
                print(f"Warning: Could not delete temp file {msg_path}: {e}")


@app.route('/upload', methods=['POST'])
@auth.login_required
def upload_file():
    """Handle file upload and conversion"""
    if 'files[]' not in request.files:
        return jsonify({'error': 'No se seleccionaron archivos'}), 400

    files = request.files.getlist('files[]')

    if not files or files[0].filename == '':
        return jsonify({'error': 'No se seleccionaron archivos'}), 400

    results = []
    errors = []

    for file in files:
        if file and allowed_file(file.filename):
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            unique_id = str(uuid.uuid4())
            msg_filename = f"{unique_id}_{original_filename}"
            msg_path = os.path.join(app.config['UPLOAD_FOLDER'], msg_filename)

            # Save uploaded file
            file.save(msg_path)

            try:
                # Convert MSG to EML
                eml_filename = msg_filename.rsplit('.', 1)[0] + '.eml'
                eml_path = os.path.join(app.config['OUTPUT_FOLDER'], eml_filename)

                converter.convert_file(msg_path, eml_path, verbose=False)

                results.append({
                    'original': original_filename,
                    'eml_filename': eml_filename,
                    'download_url': url_for('download_file', filename=eml_filename)
                })

            except Exception as e:
                errors.append({
                    'filename': original_filename,
                    'error': str(e)
                })
            finally:
                # Clean up uploaded MSG file
                if os.path.exists(msg_path):
                    os.remove(msg_path)
        else:
            errors.append({
                'filename': file.filename,
                'error': 'Tipo de archivo no permitido. Solo se aceptan archivos .msg'
            })

    return jsonify({
        'success': len(results),
        'errors': len(errors),
        'results': results,
        'error_details': errors
    })


@app.route('/download/<filename>')
@auth.login_required
def download_file(filename):
    """Download converted EML file"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], secure_filename(filename))

        if not os.path.exists(filepath):
            flash('Archivo no encontrado', 'error')
            return redirect(url_for('index'))

        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='message/rfc822'
        )
    except Exception as e:
        flash(f'Error al descargar archivo: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/batch-download', methods=['POST'])
@auth.login_required
def batch_download():
    """Download all converted files as a zip"""
    import zipfile
    from io import BytesIO

    try:
        filenames = request.json.get('filenames', [])

        if not filenames:
            return jsonify({'error': 'No hay archivos para descargar'}), 400

        # Create zip file in memory
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename in filenames:
                filepath = os.path.join(app.config['OUTPUT_FOLDER'], secure_filename(filename))
                if os.path.exists(filepath):
                    zf.write(filepath, filename)

        memory_file.seek(0)

        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='converted_emails.zip'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({
        'error': 'Archivo demasiado grande. Tamaño máximo: 50MB'
    }), 413


@app.errorhandler(500)
def internal_error(error):
    """Handle internal server error"""
    return jsonify({
        'error': 'Error interno del servidor'
    }), 500


if __name__ == '__main__':
    # Development server
    app.run(debug=True, host='0.0.0.0', port=5000)
