# Configuración de Autenticación con Authentik

Esta guía te ayudará a configurar la autenticación OAuth2/OIDC con Authentik para proteger tu aplicación de conversión MSG a EML.

## 📋 Tabla de Contenidos

1. [¿Qué es Authentik?](#qué-es-authentik)
2. [Requisitos Previos](#requisitos-previos)
3. [Configuración en Authentik](#configuración-en-authentik)
4. [Configuración de la Aplicación](#configuración-de-la-aplicación)
5. [Variables de Entorno](#variables-de-entorno)
6. [Deployment](#deployment)
7. [Troubleshooting](#troubleshooting)

---

## ¿Qué es Authentik?

[Authentik](https://goauthentik.io/) es una plataforma de Identity Provider (IdP) open-source que proporciona autenticación y autorización mediante OAuth2, OIDC, SAML y más.

**Características:**
- 🔐 Single Sign-On (SSO)
- 👥 Gestión de usuarios y grupos
- 🛡️ Multi-Factor Authentication (MFA)
- 🔑 OAuth2/OIDC Provider
- 🎨 Interfaz moderna y personalizable

---

## Requisitos Previos

- Una instancia de Authentik en funcionamiento
- Acceso de administrador a Authentik
- URL pública de tu aplicación (para el callback)

---

## Configuración en Authentik

### Paso 1: Crear un Provider

1. Inicia sesión en Authentik como administrador
2. Ve a **Applications** → **Providers**
3. Click en **Create** y selecciona **OAuth2/OpenID Provider**

4. Configura el provider:
   ```
   Name: MSG to EML Converter
   Authorization flow: default-authentication-flow (o el tuyo personalizado)
   Client type: Confidential
   Client ID: [se genera automáticamente] - cópialo
   Client Secret: [genera uno nuevo] - cópialo
   Redirect URIs/Origins:
      - http://localhost:5000/callback (desarrollo)
      - https://tu-app.render.com/callback (producción)
   ```

5. Configuración adicional:
   ```
   Scopes: openid, email, profile
   Subject mode: Based on the User's hashed ID
   Include claims in id_token: ✓ (marcado)
   ```

6. Click en **Create**

### Paso 2: Crear una Application

1. Ve a **Applications** → **Applications**
2. Click en **Create**

3. Configura la aplicación:
   ```
   Name: MSG to EML Converter
   Slug: msg-eml-converter
   Provider: [selecciona el provider creado arriba]
   Launch URL: https://tu-app.render.com (opcional)
   ```

4. Click en **Create**

### Paso 3: (Opcional) Configurar Grupos de Acceso

Si quieres restringir el acceso solo a ciertos grupos:

1. Ve a **Directory** → **Groups**
2. Crea un grupo, por ejemplo: `msg-converter-users`
3. Agrega usuarios a ese grupo

4. En tu aplicación, configura la variable de entorno:
   ```
   AUTHENTIK_ALLOWED_GROUPS=msg-converter-users
   ```

---

## Configuración de la Aplicación

### Método 1: Archivo .env (Desarrollo Local)

1. Copia el archivo de ejemplo:
   ```bash
   cp .env.example .env
   ```

2. Edita `.env` con tus credenciales:
   ```bash
   # Habilitar autenticación
   ENABLE_AUTH=true

   # URL de tu instancia de Authentik
   AUTHENTIK_BASE_URL=https://authentik.tudominio.com

   # Credenciales del Provider (obtenidas en Paso 1)
   AUTHENTIK_CLIENT_ID=tu-client-id-aqui
   AUTHENTIK_CLIENT_SECRET=tu-client-secret-aqui

   # URL de callback
   AUTHENTIK_REDIRECT_URI=http://localhost:5000/callback

   # (Opcional) Grupos permitidos
   AUTHENTIK_ALLOWED_GROUPS=msg-converter-users

   # Duración de sesión en horas
   SESSION_LIFETIME_HOURS=24

   # Secret key de Flask (genera una clave aleatoria)
   SECRET_KEY=genera-una-clave-aleatoria-muy-larga
   ```

3. Genera una SECRET_KEY segura:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

### Método 2: Variables de Entorno (Producción)

En tu plataforma de hosting (Render, Railway, etc.), configura estas variables:

```bash
ENABLE_AUTH=true
AUTHENTIK_BASE_URL=https://authentik.tudominio.com
AUTHENTIK_CLIENT_ID=tu-client-id
AUTHENTIK_CLIENT_SECRET=tu-client-secret
AUTHENTIK_REDIRECT_URI=https://tu-app.render.com/callback
AUTHENTIK_ALLOWED_GROUPS=  # opcional
SESSION_LIFETIME_HOURS=24
SECRET_KEY=tu-clave-secreta-muy-larga
```

---

## Variables de Entorno

| Variable | Requerida | Descripción | Ejemplo |
|----------|-----------|-------------|---------|
| `ENABLE_AUTH` | Sí | Habilita/deshabilita autenticación | `true` o `false` |
| `AUTHENTIK_BASE_URL` | Sí* | URL de tu instancia Authentik | `https://auth.ejemplo.com` |
| `AUTHENTIK_CLIENT_ID` | Sí* | Client ID del Provider | `abc123xyz...` |
| `AUTHENTIK_CLIENT_SECRET` | Sí* | Client Secret del Provider | `secret123...` |
| `AUTHENTIK_REDIRECT_URI` | Sí* | URL de callback de tu app | `https://app.com/callback` |
| `AUTHENTIK_ALLOWED_GROUPS` | No | Grupos permitidos (separados por coma) | `grupo1,grupo2` |
| `SESSION_LIFETIME_HOURS` | No | Duración de sesión en horas | `24` (default) |
| `SECRET_KEY` | Sí | Clave secreta de Flask | `random-secret-key` |

\* Solo requeridas si `ENABLE_AUTH=true`

---

## Deployment

### Render.com

1. En tu dashboard de Render, ve a tu Web Service
2. Ve a **Environment** → **Environment Variables**
3. Agrega cada variable de entorno
4. Click en **Save Changes**
5. La aplicación se reiniciará automáticamente

### Railway.app

1. En tu proyecto de Railway
2. Ve a **Variables**
3. Agrega las variables de entorno
4. Los cambios se aplican automáticamente

### Docker

Crea un archivo `.env` y úsalo con Docker:

```bash
docker run -p 5000:5000 --env-file .env msg-converter
```

O con docker-compose, el `.env` se carga automáticamente.

---

## Probando la Configuración

### 1. Verificar Variables

```bash
# Desarrollo local
cat .env

# Producción (ejemplo con Render CLI)
render env list --service=tu-servicio
```

### 2. Iniciar la Aplicación

```bash
python app.py
```

Deberías ver:
```
Authentication ENABLED - Authentik URL: https://authentik.tudominio.com
```

Si ves `Authentication is DISABLED`, verifica que `ENABLE_AUTH=true`.

### 3. Acceder a la Aplicación

1. Abre `http://localhost:5000` (o tu URL de producción)
2. Deberías ser redirigido a la página de login de Authentik
3. Ingresa tus credenciales
4. Serás redirigido de vuelta a la aplicación

### 4. Verificar Sesión

Endpoint de prueba:
```bash
curl http://localhost:5000/auth/status
```

Respuesta esperada:
```json
{
  "enabled": true,
  "authenticated": true,
  "user": {
    "email": "usuario@ejemplo.com",
    "name": "Usuario Ejemplo",
    "preferred_username": "usuario",
    "groups": ["msg-converter-users"]
  }
}
```

---

## Deshabilitando la Autenticación

Para deshabilitarla temporalmente:

```bash
ENABLE_AUTH=false
```

La aplicación funcionará sin autenticación. Útil para desarrollo o si quieres que sea público.

---

## Troubleshooting

### Error: "Missing Authentik configuration"

**Causa:** Variables de entorno no configuradas.

**Solución:**
- Verifica que todas las variables requeridas estén configuradas
- Asegúrate de que `.env` exista (desarrollo local)
- Reinicia la aplicación después de agregar variables

### Error: "Authentication failed"

**Causa:** Client ID o Secret incorrectos.

**Solución:**
- Verifica que el Client ID coincida con el de Authentik
- Regenera el Client Secret si es necesario
- Asegúrate de no tener espacios extra al copiar/pegar

### Error: "Redirect URI mismatch"

**Causa:** La URL de callback no coincide.

**Solución:**
- En Authentik, verifica que la Redirect URI incluya tu URL completa
- Formato correcto: `https://tu-app.com/callback` (sin slash final)
- Debe coincidir exactamente con `AUTHENTIK_REDIRECT_URI`

### Error: "Access denied - not authorized"

**Causa:** El usuario no pertenece a un grupo permitido.

**Solución:**
- Verifica que el usuario esté en un grupo especificado en `AUTHENTIK_ALLOWED_GROUPS`
- O deja `AUTHENTIK_ALLOWED_GROUPS` vacío para permitir todos los usuarios

### La sesión expira muy rápido

**Solución:**
- Aumenta `SESSION_LIFETIME_HOURS`
- Default: 24 horas

### Error: "Bad Gateway" en Render

**Causa:** La aplicación no inicia correctamente.

**Solución:**
1. Verifica los logs en Render
2. Asegúrate de que todas las variables estén configuradas
3. Si `ENABLE_AUTH=true`, verifica que las credenciales de Authentik sean correctas
4. Prueba con `ENABLE_AUTH=false` para aislar el problema

---

## Seguridad

### Mejores Prácticas

1. **SECRET_KEY**: Usa una clave aleatoria fuerte y única
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. **HTTPS**: Siempre usa HTTPS en producción
   - Render lo proporciona automáticamente
   - Nunca uses HTTP para OAuth2 en producción

3. **Client Secret**: Mantenlo secreto
   - No lo incluyas en el código
   - No lo subas a Git
   - Usa variables de entorno

4. **Grupos**: Restringe el acceso usando grupos
   ```bash
   AUTHENTIK_ALLOWED_GROUPS=admins,converters
   ```

5. **Sesiones**: Configura un tiempo de expiración razonable
   ```bash
   SESSION_LIFETIME_HOURS=8  # 8 horas para aplicaciones sensibles
   ```

---

## Características de Autenticación

### Endpoints Disponibles

| Endpoint | Descripción |
|----------|-------------|
| `/login` | Inicia el flujo de login OAuth2 |
| `/logout` | Cierra la sesión y redirige a Authentik |
| `/callback` | Callback de OAuth2 (no acceder directamente) |
| `/auth/status` | Verifica el estado de autenticación (JSON) |

### Información del Usuario

Cuando un usuario está autenticado, la información disponible incluye:
- Email
- Nombre completo
- Username preferido
- Grupos (si están configurados en Authentik)

### Protección de Rutas

Todas las rutas principales están protegidas:
- `/` - Página principal
- `/upload` - Subida de archivos
- `/download/<filename>` - Descarga de archivos
- `/batch-download` - Descarga en lote

---

## Alternativas a Authentik

Si no tienes Authentik, también puedes usar:

- **Keycloak**: Otro IdP open-source popular
- **Auth0**: Servicio SaaS (tiene tier gratuito)
- **Okta**: Para empresas
- **Google OAuth**: Para autenticación con Google
- **GitHub OAuth**: Para desarrolladores

El código puede adaptarse fácilmente a estos providers cambiando la configuración de Authlib.

---

## Soporte

- **Documentación Authentik**: https://goauthentik.io/docs/
- **Issues del proyecto**: Abre un issue en GitHub
- **Authentik Community**: https://github.com/goauthentik/authentik/discussions

---

## Changelog

### v1.0.0
- Soporte inicial para Authentik OAuth2/OIDC
- Autenticación opcional (puede habilitarse/deshabilitarse)
- Soporte para grupos de Authentik
- Endpoints de login/logout
- Información de usuario en sesión
