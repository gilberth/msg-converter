# Convertidor MSG a EML

Herramienta de Python para convertir archivos MSG de Microsoft Outlook al formato estándar EML (RFC 822).

## Características

- ✅ Convierte archivos MSG individuales a formato EML
- ✅ Procesamiento por lotes de directorios completos
- ✅ Preserva todos los metadatos del correo (remitente, destinatarios, asunto, fecha)
- ✅ Mantiene el formato HTML y texto plano
- ✅ Conserva todos los archivos adjuntos
- ✅ Interfaz de línea de comandos fácil de usar
- ✅ API de Python para integración en otros proyectos

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

### Línea de Comandos

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
├── msg_to_eml_converter.py   # Script principal del convertidor
├── test_converter.py          # Tests unitarios
├── requirements.txt           # Dependencias de Python
├── .gitignore                 # Archivos ignorados por Git
└── README.md                  # Esta documentación
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

## Changelog

### v1.0.0 (2025-11-20)
- Versión inicial
- Conversión de MSG a EML
- Soporte para archivos individuales y directorios
- Preservación de adjuntos y metadatos
- Tests unitarios incluidos
