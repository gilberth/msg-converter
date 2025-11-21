# Changelog

Todas las versiones y cambios notables de este proyecto serán documentados en este archivo.

---

## [2.1.0] - 2025-11-21 - "Authentication Edition"

### 🎉 Agregado
- **Wizard Web de Configuración**: Interfaz web en `/setup` para configurar Authentik desde el navegador
- **Sistema de Versiones**: Footer con número de versión y nombre de edición en todas las páginas
- **Autenticación OAuth2/OIDC**: Soporte completo para Authentik
  - Auto-configuración desde CLI (`authentik_auto_setup.py`)
  - Auto-configuración desde interfaz web (`/setup`)
  - Configuración manual documentada
- **Control de Acceso por Grupos**: Soporte para restringir acceso por grupos de Authentik
- **Sesiones Configurables**: Tiempo de expiración de sesión personalizable
- **Información de Usuario**: Barra superior con nombre/email del usuario autenticado

### 🔧 Corregido
- **Estructura MIME Multipart**: Corregida jerarquía para HTML + adjuntos
- **Texto no aparecía**: Solucionado error donde el texto del mensaje no se mostraba en EML
- **Solo última imagen**: Corregido error donde solo se mostraba la última imagen adjunta
- **Imágenes inline**: Implementado soporte correcto para imágenes embebidas en HTML
- **API Authentik**: Corregido error 400 Bad Request (redirect_uris debe ser lista)

### 📚 Documentación
- `AUTHENTIK_SETUP.md`: Guía completa de configuración manual (35+ pasos)
- `QUICK_AUTH_SETUP.md`: Guía rápida de auto-configuración CLI
- `WEB_SETUP_GUIDE.md`: Guía de configuración desde interfaz web
- `DEPLOYMENT.md`: Instrucciones para 5+ plataformas de hosting
- `CHANGELOG.md`: Este archivo de cambios

### 🔐 Seguridad
- Autenticación opcional (habilitada/deshabilitada con variable de entorno)
- Tokens de API nunca expuestos en logs
- Variables sensibles en `.env` (excluido de Git)
- Limpieza automática de archivos después de 1 hora

---

## [2.0.0] - 2025-11-20 - "Web Application Release"

### 🎉 Agregado
- **Aplicación Web Completa**: Interfaz moderna con Flask
- **Interfaz Drag-and-Drop**: Arrastra archivos MSG para convertir
- **Conversión por Lotes**: Sube y convierte múltiples archivos simultáneamente
- **Descarga en ZIP**: Descarga todos los archivos convertidos en un solo ZIP
- **Diseño Responsive**: Funciona en móvil, tablet y desktop
- **Feedback Visual**: Barra de progreso y mensajes de estado
- **Limpieza Automática**: Thread que elimina archivos después de 1 hora

### 🛠️ Técnico
- Flask 3.0+ como framework web
- Bootstrap 5.3 para UI
- Gunicorn para servidor de producción
- Docker y docker-compose configurados
- Procfile para Heroku/Render

### 📚 Documentación
- `README.md` actualizado con sección de aplicación web
- `START.md`: Guía de inicio rápido
- `DEPLOYMENT.md`: Guía de deployment

---

## [1.0.0] - 2025-11-20 - "Initial Release"

### 🎉 Agregado
- **Convertidor CLI**: Script de línea de comandos para convertir MSG a EML
- **Conversión Individual**: Convierte un archivo MSG a la vez
- **Conversión por Directorio**: Procesa todos los MSG en una carpeta
- **Preservación de Metadatos**: Mantiene remitente, destinatarios, asunto, fecha
- **Soporte HTML**: Preserva formato HTML y texto plano
- **Adjuntos**: Conserva todos los archivos adjuntos
- **API Python**: Clase `MSGToEMLConverter` para integración

### 🛠️ Técnico
- Python 3.6+ compatible
- Librería `extract-msg` para lectura de MSG
- Formato MIME/RFC 822 estándar para EML
- Tests unitarios incluidos

### 📚 Documentación
- `README.md`: Documentación completa
- `example.py`: 5 ejemplos de uso
- `LICENSE`: Licencia MIT

---

## Formato

Este changelog sigue el formato [Keep a Changelog](https://keepachangelog.com/es/1.0.0/),
y este proyecto adhiere a [Versionado Semántico](https://semver.org/lang/es/).

### Tipos de Cambios
- **Agregado** para nuevas características
- **Cambiado** para cambios en funcionalidad existente
- **Obsoleto** para características que serán removidas
- **Removido** para características removidas
- **Corregido** para corrección de bugs
- **Seguridad** para vulnerabilidades
