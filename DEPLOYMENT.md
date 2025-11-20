# Guía de Deployment - Convertidor MSG a EML

Esta aplicación Flask requiere un servidor que ejecute Python. GitHub Pages **NO es compatible** porque solo sirve sitios estáticos.

## Opciones de Hosting Gratuito

### 1. Render (Recomendado) ⭐

**Ventajas:**
- Completamente gratuito
- Deploy automático desde GitHub
- SSL incluido
- Muy fácil de configurar

**Pasos:**

1. Crea una cuenta en [Render.com](https://render.com)

2. Conecta tu repositorio de GitHub

3. Crea un nuevo **Web Service**

4. Configura:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Environment:** Python 3

5. Agrega variables de entorno:
   ```
   SECRET_KEY=tu-clave-secreta-aleatoria
   PYTHON_VERSION=3.11.6
   ```

6. Click en **Deploy** y espera

Tu aplicación estará disponible en: `https://tu-app.onrender.com`

---

### 2. Railway.app

**Ventajas:**
- Deploy desde GitHub
- $5 gratis al mes
- SSL automático

**Pasos:**

1. Crea cuenta en [Railway.app](https://railway.app)

2. Click en "New Project" → "Deploy from GitHub repo"

3. Selecciona tu repositorio

4. Railway detectará automáticamente que es una app Python/Flask

5. Agrega variable de entorno:
   ```
   SECRET_KEY=tu-clave-secreta-aleatoria
   ```

6. Railway automáticamente hace el deploy

URL: `https://tu-app.railway.app`

---

### 3. Fly.io

**Ventajas:**
- Tier gratuito generoso
- Deploy rápido
- Múltiples regiones

**Pasos:**

1. Instala Fly CLI:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. Autentícate:
   ```bash
   fly auth login
   ```

3. En el directorio del proyecto:
   ```bash
   fly launch
   ```

4. Sigue las instrucciones (usa la configuración predeterminada)

5. Deploy:
   ```bash
   fly deploy
   ```

---

### 4. PythonAnywhere

**Ventajas:**
- Específico para Python
- Tier gratuito permanente
- No requiere tarjeta de crédito

**Pasos:**

1. Crea cuenta en [PythonAnywhere.com](https://www.pythonanywhere.com)

2. Abre una consola Bash

3. Clona tu repositorio:
   ```bash
   git clone https://github.com/tu-usuario/msg-converter.git
   cd msg-converter
   ```

4. Crea un virtualenv:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 myenv
   pip install -r requirements.txt
   ```

5. En el dashboard, ve a "Web" → "Add a new web app"

6. Selecciona Flask y configura:
   - Source code: `/home/tu-usuario/msg-converter`
   - Working directory: `/home/tu-usuario/msg-converter`
   - WSGI configuration file: edita y apunta a `app.py`

7. Recarga la web app

URL: `https://tu-usuario.pythonanywhere.com`

---

### 5. Heroku (Clásico)

**Nota:** Heroku eliminó su tier gratuito, pero incluido por referencia.

**Pasos:**

1. Instala Heroku CLI

2. Login:
   ```bash
   heroku login
   ```

3. Crea app:
   ```bash
   heroku create tu-app-nombre
   ```

4. Agrega variable de entorno:
   ```bash
   heroku config:set SECRET_KEY=tu-clave-secreta
   ```

5. Deploy:
   ```bash
   git push heroku main
   ```

URL: `https://tu-app-nombre.herokuapp.com`

---

## Deploy con Docker

Si prefieres usar Docker en cualquier plataforma:

### Construcción Local

```bash
# Construir imagen
docker build -t msg-converter .

# Ejecutar contenedor
docker run -p 5000:5000 \
  -e SECRET_KEY=tu-clave-secreta \
  msg-converter
```

Visita: `http://localhost:5000`

### Docker Compose

```bash
# Iniciar
docker-compose up -d

# Detener
docker-compose down
```

---

## Variables de Entorno Importantes

Configura estas variables en tu plataforma de hosting:

```bash
SECRET_KEY=genera-una-clave-aleatoria-segura-aqui
FLASK_ENV=production
MAX_CONTENT_LENGTH=52428800  # 50MB en bytes (opcional)
```

### Generar SECRET_KEY segura:

```python
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Deployment Automático con GitHub Actions

Crea `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Render

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Render Deploy
        run: |
          curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK }}
```

Agrega `RENDER_DEPLOY_HOOK` en GitHub Secrets.

---

## Testing Local

Antes de hacer deploy, prueba localmente:

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar en modo desarrollo
python app.py

# O con Gunicorn (producción)
gunicorn app:app
```

Visita: `http://localhost:5000`

---

## Solución de Problemas

### Error: "Application Error"

- Verifica que todas las dependencias estén en `requirements.txt`
- Revisa los logs: `heroku logs --tail` (Heroku) o similar

### Error: "Module not found"

- Asegúrate de que `requirements.txt` esté actualizado
- Ejecuta: `pip freeze > requirements.txt`

### Archivos no se guardan

- Algunos servicios tienen sistemas de archivos efímeros
- Considera usar almacenamiento en la nube (S3, Cloudinary) para archivos permanentes

### Timeout en conversión

- Aumenta el timeout en Gunicorn:
  ```
  gunicorn --timeout 120 app:app
  ```

---

## Recomendación Final

**Para deployment rápido y fácil:** Usa **Render.com**

**Para control total:** Usa **Docker en cualquier VPS**

**Para aprendizaje:** Usa **PythonAnywhere**

---

## Checklist Pre-Deployment

- [ ] `SECRET_KEY` configurada
- [ ] `requirements.txt` actualizado
- [ ] Probado localmente
- [ ] `.gitignore` configurado
- [ ] Variables de entorno configuradas
- [ ] SSL/HTTPS habilitado
- [ ] Logs configurados

---

## Monitoreo

Después del deploy, monitorea:

- Uso de memoria
- Tiempo de respuesta
- Errores en logs
- Uso de disco (archivos temporales)

---

## Próximos Pasos

1. Elige una plataforma de hosting
2. Sigue los pasos específicos de esa plataforma
3. Configura las variables de entorno
4. Haz deploy
5. ¡Comparte tu URL!

Para más ayuda, consulta la documentación oficial de cada plataforma.
