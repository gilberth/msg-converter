# 🚀 Inicio Rápido - Convertidor MSG a EML

## Opción 1: Aplicación Web (Recomendado)

### Paso 1: Instalar Dependencias

```bash
pip install -r requirements.txt
```

### Paso 2: Ejecutar la Aplicación

```bash
python app.py
```

### Paso 3: Abrir en el Navegador

Visita: **http://localhost:5000**

¡Listo! Ahora puedes arrastrar y soltar archivos MSG para convertirlos.

---

## Opción 2: Línea de Comandos

### Conversión Simple

```bash
python msg_to_eml_converter.py email.msg
```

### Conversión de Múltiples Archivos

```bash
python msg_to_eml_converter.py -d carpeta_con_mensajes
```

---

## Opción 3: Docker

### Con Docker

```bash
docker build -t msg-converter .
docker run -p 5000:5000 msg-converter
```

### Con Docker Compose

```bash
docker-compose up
```

Visita: **http://localhost:5000**

---

## Publicar en Internet

Para publicar la aplicación web en internet **gratis**, consulta:

**📖 [DEPLOYMENT.md](DEPLOYMENT.md)**

Opciones gratuitas disponibles:
- ✅ **Render.com** (Recomendado)
- ✅ Railway.app
- ✅ Fly.io
- ✅ PythonAnywhere

---

## Ayuda Rápida

### Problemas con Dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Error de Puerto en Uso

Cambia el puerto en `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=8080)  # Cambiar 5000 a 8080
```

### Ver Logs en Tiempo Real

```bash
python app.py  # Los logs aparecerán en la terminal
```

---

## Próximos Pasos

1. ✅ Ejecuta la aplicación localmente
2. 📝 Prueba con algunos archivos MSG
3. 🌐 Despliega en la nube (ver DEPLOYMENT.md)
4. 📣 Comparte tu URL

---

## Más Información

- **README.md** - Documentación completa
- **DEPLOYMENT.md** - Guía de deployment
- **example.py** - Ejemplos de uso programático

¿Necesitas ayuda? Abre un issue en el repositorio.
