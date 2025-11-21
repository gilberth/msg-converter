# 🌐 Configuración Web de Authentik

## Setup desde el Navegador (Render/Railway/etc.)

¿Tu aplicación ya está desplegada en Render, Railway u otra plataforma? ¡Puedes configurar Authentik directamente desde el navegador!

---

## ⚡ Acceso Rápido

Simplemente navega a:
```
https://tu-app.onrender.com/setup
```

O haz clic en el link **"Configurar autenticación"** que aparece en la página principal.

---

## 📋 Pasos del Wizard

### Paso 1: Preparación

Antes de comenzar, necesitas:

1. **URL de Authentik**
   - La URL completa de tu instancia
   - Ejemplo: `https://auth.tudominio.com`

2. **Token de API de Authentik**
   - Ve a tu Authentik → **Directory** → **Tokens**
   - Click en **Create**
   - Configura:
     ```
     Identifier: msg-converter-web-setup
     User: (tu usuario admin)
     Scope: Marca "view" y "write"
     Expires: 2025-12-31 (o fecha futura)
     ```
   - Click **Create** y **copia el token**

3. **URL de tu aplicación**
   - Se detecta automáticamente
   - Ejemplo: `https://tu-app.onrender.com`

### Paso 2: Wizard Web

1. **Ve a `/setup`** en tu aplicación

2. **Lee la información** en el paso 1

3. **Click en "Continuar"**

4. **Completa el formulario**:
   - URL de Authentik: `https://auth.tudominio.com`
   - Token de API: `ak_xxxxx...` (el que copiaste)
   - URL de la aplicación: (ya aparece automáticamente)

5. **Click en "Configurar automáticamente"**

6. **Espera** mientras el wizard:
   - Conecta con Authentik
   - Crea el Provider OAuth2
   - Crea la Application
   - Genera credenciales
   - Configura variables de entorno

7. **¡Listo!** Verás un mensaje de éxito

### Paso 3: Reiniciar la Aplicación

**Importante:** Después de la configuración, necesitas reiniciar la aplicación:

#### En Render:
1. Ve al dashboard de Render
2. Selecciona tu servicio
3. Click en **Manual Deploy** → **Deploy latest commit**
4. O simplemente espera al próximo deploy automático

#### En Railway:
1. La aplicación se reiniciará automáticamente
2. O ve al dashboard y reinicia manualmente

#### En Fly.io:
```bash
fly apps restart tu-app
```

---

## ✅ Verificación

Después del reinicio:

1. Ve a la página principal: `https://tu-app.onrender.com`
2. Deberías ser redirigido a Authentik para login
3. Ingresa tus credenciales
4. Serás redirigido de vuelta a la aplicación
5. ¡Autenticación funcionando! 🎉

---

## 🔧 Variables de Entorno Creadas

El wizard crea automáticamente estas variables en el archivo `.env` del servidor:

```bash
ENABLE_AUTH=true
AUTHENTIK_BASE_URL=https://auth.tudominio.com
AUTHENTIK_CLIENT_ID=abc123xyz...
AUTHENTIK_CLIENT_SECRET=secret123...
AUTHENTIK_REDIRECT_URI=https://tu-app.onrender.com/callback
```

**Nota:** En Render/Railway, estas variables solo existen en el servidor, no en tu código local.

---

## 🔄 Reconfigurar

Si necesitas cambiar la configuración:

1. Ve a `/setup` nuevamente
2. Verás un mensaje indicando que ya está configurado
3. Para reconfigurar:
   - Opción A: Ejecuta el wizard localmente: `python authentik_auto_setup.py`
   - Opción B: Elimina las variables de entorno y vuelve a `/setup`

---

## 📊 Diagrama de Flujo

```
┌─────────────────────────┐
│ Usuario va a /setup     │
└───────────┬─────────────┘
            │
            v
┌─────────────────────────┐
│ Wizard muestra          │
│ formulario              │
└───────────┬─────────────┘
            │
            v
┌─────────────────────────┐
│ Usuario completa:       │
│ - URL Authentik         │
│ - Token API             │
│ - URL App               │
└───────────┬─────────────┘
            │
            v
┌─────────────────────────┐
│ Wizard ejecuta:         │
│ 1. Validar conexión     │
│ 2. Crear Provider       │
│ 3. Crear Application    │
│ 4. Guardar credenciales │
└───────────┬─────────────┘
            │
            v
┌─────────────────────────┐
│ Mensaje de éxito        │
│ "Reiniciar aplicación"  │
└───────────┬─────────────┘
            │
            v
┌─────────────────────────┐
│ Usuario reinicia app    │
│ en plataforma de hosting│
└───────────┬─────────────┘
            │
            v
┌─────────────────────────┐
│ ✅ Authentik funcionando│
└─────────────────────────┘
```

---

## 🆚 Comparación de Métodos

| Método | Dónde | Complejidad | Mejor para |
|--------|-------|-------------|------------|
| **Wizard Web** | Navegador | Muy fácil | Apps ya desplegadas |
| **Script Python** | Terminal local | Fácil | Desarrollo local |
| **Manual** | Authentik UI | Media | Control total |

---

## 💡 Consejos

### Seguridad del Token API

- **No compartas** el token de API
- **Revócalo** después de la configuración si quieres
- **Crea tokens temporales** para setup únicamente

### En Render

- Las variables se guardan en el servidor
- No necesitas configurarlas manualmente en el dashboard
- Pero el archivo `.env` no es persistente entre deploys
- **Recomendación:** Después del wizard, copia las variables al dashboard de Render para que persistan

### Migración a Producción

Si configuraste localmente primero:

1. Exporta las variables del `.env` local
2. Ve al dashboard de tu plataforma (Render/Railway)
3. Agrega las variables manualmente
4. O usa el wizard web directamente en producción

---

## 🚨 Troubleshooting

### Error: "Request timeout"

**Causa:** No se puede conectar a Authentik

**Solución:**
- Verifica que la URL de Authentik sea correcta
- Asegúrate de que Authentik esté accesible desde internet
- Si Authentik está en red local, no funcionará desde Render

### Error: "Token de API inválido"

**Causa:** Token expirado o sin permisos

**Solución:**
- Crea un nuevo token en Authentik
- Asegúrate de marcar scopes 'view' y 'write'
- Verifica que el token no haya expirado

### Error: "Provider creation failed"

**Causa:** Permisos insuficientes o provider duplicado

**Solución:**
- Verifica que el token tenga permisos 'write'
- Si ya existe un provider, el wizard lo detectará y lo reutilizará

### El wizard se completa pero no funciona

**Causa:** App no se reinició

**Solución:**
- **Reinicia la aplicación** en tu plataforma
- Las variables de entorno solo se cargan al iniciar
- En Render: Manual Deploy
- En Railway: Auto-restart

### Variables no persisten en Render

**Causa:** El archivo `.env` no es persistente

**Solución:**
1. Después del wizard, toma nota de las variables
2. Ve a Render → Environment
3. Agrégalas manualmente:
   ```
   ENABLE_AUTH=true
   AUTHENTIK_BASE_URL=...
   AUTHENTIK_CLIENT_ID=...
   AUTHENTIK_CLIENT_SECRET=...
   AUTHENTIK_REDIRECT_URI=...
   ```

---

## 📚 Recursos Adicionales

- [Guía Rápida CLI](QUICK_AUTH_SETUP.md) - Setup desde terminal
- [Guía Completa](AUTHENTIK_SETUP.md) - Configuración manual detallada
- [Documentación Authentik](https://goauthentik.io/docs/)

---

## ✨ Ventajas del Wizard Web

✅ **No necesitas acceso al servidor**
- Todo desde el navegador
- Perfecto para apps en la nube

✅ **Interfaz visual**
- Paso a paso guiado
- Feedback en tiempo real
- Mensajes de error claros

✅ **Detección automática**
- URL de la app se detecta sola
- Reutiliza configuración existente
- Evita duplicados

✅ **Sin dependencias**
- No necesitas Python local
- No necesitas clonar el repo
- Solo un navegador

---

## 🎯 Resumen

1. Ve a `https://tu-app.onrender.com/setup`
2. Completa 3 campos (URL + Token + URL App)
3. Click "Configurar automáticamente"
4. Reinicia la app en Render/Railway
5. ¡Listo!

**Tiempo total: ~5 minutos** ⏱️

---

¡Disfruta de tu aplicación con autenticación! 🔐
