# ⚡ Configuración Rápida de Autenticación

## Opción 1: Auto-Configuración (Recomendado) 🚀

Esta es la forma MÁS RÁPIDA de configurar autenticación con Authentik.

### Requisitos

- Una instancia de Authentik funcionando
- Acceso de administrador a Authentik
- 5 minutos de tu tiempo

### Pasos

#### 1. Crear Token de API en Authentik

1. Inicia sesión en Authentik como administrador
2. Ve a **Directory** → **Tokens**
3. Click en **Create**
4. Configura:
   ```
   Identifier: msg-converter-setup
   User: (tu usuario admin)
   Scope: Selecciona "view" y "write"
   Expires: 2025-12-31 (o fecha futura)
   ```
5. Click en **Create**
6. **COPIA EL TOKEN** que aparece (no podrás verlo de nuevo)

#### 2. Ejecutar Script de Auto-Configuración

```bash
# Instala dependencias si no lo has hecho
pip install -r requirements.txt

# Ejecuta el script de auto-configuración
python authentik_auto_setup.py
```

#### 3. Responder Preguntas del Script

El script te preguntará:

```
URL de tu instancia Authentik (ej: https://auth.ejemplo.com):
→ https://tu-authentik.com

Token de API de Authentik:
→ [pega el token copiado en el paso 1]

URL de tu aplicación (ej: http://localhost:5000):
→ http://localhost:5000  (o tu URL de producción)
```

#### 4. ¡Listo!

El script:
- ✅ Crea automáticamente el Provider OAuth2 en Authentik
- ✅ Crea automáticamente la Application en Authentik
- ✅ Genera Client ID y Secret
- ✅ Guarda todo en el archivo `.env`

**Ahora puedes ejecutar:**
```bash
python app.py
```

---

## Opción 2: Configuración Manual

Si prefieres configurar manualmente, sigue la guía completa: [AUTHENTIK_SETUP.md](AUTHENTIK_SETUP.md)

---

## Ejemplo Completo (Auto-Configuración)

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd msg-converter

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Auto-configuración
python authentik_auto_setup.py

# Responder preguntas:
# URL de Authentik: https://auth.midominio.com
# Token de API: ak_KJHSDFkjhsdf87234hksdjfh234
# URL de la app: http://localhost:5000

# 4. Iniciar aplicación
python app.py

# 5. Abrir navegador
# http://localhost:5000
```

**Tiempo total: ~3 minutos** ⏱️

---

## Variables de Entorno Mínimas

Con auto-configuración solo necesitas:

```bash
# En tu servidor/plataforma (Render, Railway, etc.)
AUTHENTIK_BASE_URL=https://tu-authentik.com
AUTHENTIK_API_TOKEN=tu-token-aqui
```

El script puede ejecutarse en el servidor para generar las credenciales.

---

## Para Producción (Render, Railway, etc.)

### Método A: Ejecutar Script en Primera Ejecución

1. Configura variables en tu plataforma:
   ```
   AUTHENTIK_BASE_URL=https://tu-authentik.com
   AUTHENTIK_API_TOKEN=tu-token
   AUTHENTIK_REDIRECT_URI=https://tu-app.onrender.com/callback
   ```

2. Agrega a tus comandos de inicio:
   ```bash
   # En Render, Railway, etc.
   python authentik_auto_setup.py && gunicorn app:app
   ```

3. El script se ejecutará una vez, configurará todo, y luego iniciará la app

### Método B: Ejecutar Localmente y Copiar Credenciales

1. Ejecuta el script localmente:
   ```bash
   python authentik_auto_setup.py
   ```

2. Abre el archivo `.env` generado

3. Copia las variables a tu plataforma de hosting:
   ```
   ENABLE_AUTH=true
   AUTHENTIK_BASE_URL=...
   AUTHENTIK_CLIENT_ID=...
   AUTHENTIK_CLIENT_SECRET=...
   AUTHENTIK_REDIRECT_URI=...
   ```

---

## Actualizar Configuración

Si cambias la URL de tu aplicación:

```bash
# Edita .env o configura variable:
export AUTHENTIK_REDIRECT_URI=https://nueva-url.com/callback

# Re-ejecuta el script:
python authentik_auto_setup.py

# El script detectará la configuración existente y la actualizará
```

---

## Desinstalar/Limpiar

Para eliminar la configuración de Authentik:

1. Inicia sesión en Authentik
2. Ve a **Applications** → **Applications**
3. Elimina "MSG to EML Converter"
4. Ve a **Applications** → **Providers**
5. Elimina "MSG to EML Converter"
6. Elimina el archivo `.env` local

---

## Troubleshooting

### Error: "No se pudo conectar con Authentik"

**Solución:**
- Verifica que la URL de Authentik sea correcta
- Asegúrate de incluir `https://` o `http://`
- Verifica que el token de API sea válido
- Comprueba que tienes acceso a internet

### Error: "Token de API inválido"

**Solución:**
- El token puede haber expirado
- Crea un nuevo token en Authentik
- Asegúrate de que el token tenga scopes 'view' y 'write'

### Error: "Provider ya existe"

**Solución:**
- El script detectará providers existentes
- Te preguntará si quieres usar el existente
- Responde 's' para reutilizarlo o 'n' para crear uno nuevo

### El script se ejecuta pero la app no funciona

**Solución:**
- Verifica que `.env` tenga `ENABLE_AUTH=true`
- Reinicia la aplicación después de ejecutar el script
- Revisa los logs: `python app.py`

---

## Características del Auto-Setup

✅ **Detección de configuración existente**
- No crea duplicados
- Puede reutilizar providers/applications existentes

✅ **Validación de conexión**
- Verifica la conexión antes de crear nada
- Mensajes de error claros

✅ **Configuración automática completa**
- Crea Provider OAuth2
- Crea Application
- Genera credenciales
- Guarda en .env

✅ **Interactivo y fácil de usar**
- Preguntas claras
- Valores por defecto inteligentes
- Feedback visual del progreso

---

## Comparación: Auto vs Manual

| Característica | Auto-Setup | Manual |
|----------------|------------|--------|
| Tiempo | ~3 minutos | ~15 minutos |
| Complejidad | Fácil | Media |
| Pasos | 3 comandos | 10+ pasos |
| Errores | Menos propenso | Más propenso |
| Requisitos | Token API | Configuración manual |
| Reversible | Sí | Sí |

---

## Preguntas Frecuentes

**¿Es seguro el token de API?**
- Sí, se guarda en `.env` que está en `.gitignore`
- Nunca lo subas a Git
- Puedes revocarlo en Authentik cuando quieras

**¿Puedo ejecutar el script varias veces?**
- Sí, el script detecta configuración existente
- Puedes actualizar URLs o settings

**¿Funciona con otras plataformas además de Authentik?**
- Actualmente solo Authentik
- Podría adaptarse a Keycloak, Auth0, etc.

**¿Necesito dejar el token de API después?**
- No, puedes removerlo de `.env` después de la configuración inicial
- Solo es necesario para el auto-setup

---

## Soporte

Si tienes problemas:
1. Revisa los logs: `python authentik_auto_setup.py`
2. Verifica la [documentación completa](AUTHENTIK_SETUP.md)
3. Abre un issue en GitHub

---

¡Disfruta de tu aplicación con autenticación en 3 minutos! 🎉
