# Convertidor MSG a EML

Herramienta de Python para convertir archivos MSG de Microsoft Outlook al formato estándar EML (RFC 822).

## 🌐 Aplicación Web

¡Ahora disponible con interfaz web! Convierte tus archivos MSG directamente desde el navegador.

**[Ver Guía de Deployment →](DEPLOYMENT.md)**

## Características

- ✅ **Interfaz Web Moderna** - Arrastra y suelta archivos para convertir
- ✅ **Autenticación OAuth2/OIDC** - Soporte para Authentik (opcional)
- ✅ **Eliminación Automática** - Los archivos se borran después de 1 hora
- ✅ Convierte archivos MSG individuales a formato EML
- ✅ Procesamiento por lotes de múltiples archivos
- ✅ Preserva todos los metadatos del correo (remitente, destinatarios, asunto, fecha)
- ✅ Mantiene el formato HTML y texto plano
- ✅ Conserva todos los archivos adjuntos
- ✅ Interfaz de línea de comandos (CLI)
- ✅ API de Python para integración en otros proyectos
- ✅ Descarga en ZIP para conversiones múltiples

## Requisitos

- Python 3.6 o superior
- pip (gestor de paquetes de Python)

## Instalación

1. Clona el repositorio:

```bash
git clone <repository-url>
cd msg-converter
```

2. Instala las dependencias:

```bash
pip install -r requirements.txt
```

## Uso

### Aplicación Web

#### Ejecutar Localmente

1. Instala las dependencias:
```bash
pip install -r requirements.txt
```

2. Inicia la aplicación:
```bash
python app.py
```

3. Abre tu navegador en: `http://localhost:5000`

4. Arrastra archivos MSG o haz clic para seleccionar

5. ¡Descarga tus archivos EML convertidos!

#### Deployment en la Nube

Para publicar la aplicación en internet, consulta la **[Guía de Deployment](DEPLOYMENT.md)** con instrucciones para:
- Render.com (Recomendado - Gratis)
- Railway.app
- Fly.io
- PythonAnywhere
- Docker

#### Autenticación con Authentik (Opcional)

La aplicación soporta autenticación OAuth2/OIDC con Authentik para controlar el acceso.

**Configurar autenticación:**
- Ver **[Guía de Authentik](AUTHENTIK_SETUP.md)** para instrucciones detalladas
- Configura `ENABLE_AUTH=true` en variables de entorno
- Funciona con grupos de usuarios
- Sesiones configurables

**Sin autenticación:**
- Por defecto está deshabilitada (`ENABLE_AUTH=false`)
- La aplicación es pública y accesible para todos

### Línea de Comandos (CLI)

#### Convertir un archivo individual

```bash
python msg_to_eml_converter.py email.msg
```

Esto creará `email.eml` en el mismo directorio.

#### Especificar archivo de salida personalizado

```bash
python msg_to_eml_converter.py email.msg -o salida.eml
```

#### Convertir todos los archivos MSG en un directorio

```bash
python msg_to_eml_converter.py -d /ruta/a/mensajes
```

#### Convertir directorio con salida personalizada

```bash
python msg_to_eml_converter.py -d /ruta/a/mensajes -o /ruta/salida
```

#### Modo verbose (detallado)

```bash
python msg_to_eml_converter.py email.msg -v
```

### Como librería de Python

```python
from msg_to_eml_converter import MSGToEMLConverter

# Crear instancia del convertidor
converter = MSGToEMLConverter()

# Convertir un archivo individual
converter.convert_file('email.msg', 'email.eml', verbose=True)

# Convertir un directorio completo
converter.convert_directory(
    input_dir='/ruta/mensajes',
    output_dir='/ruta/salida',
    verbose=True
)
```

## Opciones de Línea de Comandos

```
usage: msg_to_eml_converter.py [-h] [-o OUTPUT] [-d] [-v] [input]

Convert Microsoft Outlook MSG files to EML format

positional arguments:
  input                 Input MSG file or directory

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output EML file or directory
  -d, --directory       Process all MSG files in input directory
  -v, --verbose         Verbose output
```

## Ejemplos de Uso

### Ejemplo 1: Conversión Simple

```bash
# Convertir mensaje.msg a mensaje.eml
python msg_to_eml_converter.py mensaje.msg
```

### Ejemplo 2: Procesamiento por Lotes

```bash
# Convertir todos los .msg en la carpeta 'inbox'
python msg_to_eml_converter.py -d inbox -o converted
```

### Ejemplo 3: Integración en Script

```python
#!/usr/bin/env python3
from msg_to_eml_converter import MSGToEMLConverter
import sys

def convertir_correos(directorio_entrada):
    converter = MSGToEMLConverter()

    try:
        archivos = converter.convert_directory(
            input_dir=directorio_entrada,
            output_dir='convertidos',
            verbose=True
        )
        print(f"Convertidos {len(archivos)} archivos exitosamente")
        return True
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    convertir_correos('mis_mensajes')
```

## Estructura del Proyecto

```
msg-converter/
├── app.py                      # Aplicación web Flask
├── msg_to_eml_converter.py     # Motor de conversión
├── templates/
│   └── index.html              # Interfaz web
├── static/
│   ├── css/
│   │   └── style.css           # Estilos
│   └── js/
│       └── app.js              # Lógica frontend
├── test_converter.py           # Tests unitarios
├── example.py                  # Ejemplos de uso
├── requirements.txt            # Dependencias Python
├── Dockerfile                  # Configuración Docker
├── docker-compose.yml          # Docker Compose
├── Procfile                    # Configuración Heroku/Render
├── DEPLOYMENT.md               # Guía de deployment
├── .gitignore                  # Archivos ignorados
├── LICENSE                     # Licencia MIT
└── README.md                   # Esta documentación
```

## Ejecutar Tests

```bash
python test_converter.py
```

O con unittest directamente:

```bash
python -m unittest test_converter.py -v
```

## Formato de Archivos

### MSG (Microsoft Outlook Message)
Formato propietario de Microsoft usado por Outlook para almacenar mensajes de correo electrónico, incluyendo:
- Contenido del mensaje
- Metadatos (remitente, destinatarios, fecha, etc.)
- Archivos adjuntos
- Propiedades extendidas de MAPI

### EML (Email Message)
Formato estándar de correo electrónico basado en RFC 822 y MIME, compatible con la mayoría de clientes de correo:
- Thunderbird
- Apple Mail
- Gmail
- Outlook (también soporta EML)
- Y muchos otros

## Características Técnicas

### Metadatos Preservados

- **Subject**: Asunto del correo
- **From**: Remitente
- **To**: Destinatarios principales
- **Cc**: Con copia
- **Bcc**: Con copia oculta
- **Date**: Fecha y hora del mensaje
- **Message-ID**: Identificador único del mensaje

### Contenido Soportado

- Texto plano
- HTML (formato enriquecido)
- Archivos adjuntos (todos los tipos)
- Codificación UTF-8 para caracteres internacionales

## Solución de Problemas

### Error: "No module named 'extract_msg'"

Instala las dependencias:
```bash
pip install -r requirements.txt
```

### Error: "MSG file not found"

Verifica que la ruta al archivo MSG sea correcta y que el archivo exista.

### Error al leer archivo MSG corrupto

Algunos archivos MSG pueden estar dañados. Intenta abrirlos en Outlook primero para verificar que sean válidos.

## Limitaciones Conocidas

- Los archivos MSG muy grandes (>100MB) pueden tardar tiempo en procesarse
- Algunas propiedades avanzadas de MAPI pueden no transferirse completamente
- La firma digital de Outlook no se preserva en el formato EML

## Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Haz fork del proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

## Licencia

Este proyecto está disponible bajo la licencia MIT.

## Soporte

Para reportar bugs o solicitar nuevas características, por favor abre un issue en el repositorio.

## Screenshots

### Interfaz Web
![Captura de la aplicación web con interfaz moderna de drag-and-drop]

### Línea de Comandos
```bash
$ python msg_to_eml_converter.py email.msg -v
Reading MSG file: email.msg
  Subject: Reunión de Proyecto
  From: juan@example.com
  To: maria@example.com
  Attachments: 2
Creating EML file: email.eml
Conversion completed successfully!
```

## Tecnologías Utilizadas

- **Backend:** Python 3.11, Flask, Gunicorn
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla), Bootstrap 5
- **Conversión:** extract-msg library
- **Deployment:** Docker, Heroku, Render, Railway

## Changelog

### v2.0.0 (2025-11-20)
- 🎉 Aplicación web con interfaz moderna
- ✨ Drag-and-drop para subir archivos
- 📦 Descarga en ZIP para múltiples archivos
- 🐳 Soporte completo para Docker
- 📚 Guía de deployment detallada
- 🔒 Limpieza automática de archivos (1 hora)

### v1.0.0 (2025-11-20)
- Versión inicial CLI
- Conversión de MSG a EML
- Soporte para archivos individuales y directorios
- Preservación de adjuntos y metadatos
- Tests unitarios incluidos
