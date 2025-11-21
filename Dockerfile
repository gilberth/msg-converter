# Dockerfile para MSG to EML Converter
# Multi-stage build para optimizar tamaño de imagen

# Stage 1: Builder
FROM python:3.11-slim as builder

# Instalar dependencias de compilación
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias en directorio aislado
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Crear usuario no-root por seguridad
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/uploads /app/converted && \
    chown -R appuser:appuser /app

# Copiar dependencias instaladas desde builder
COPY --from=builder /root/.local /home/appuser/.local

# Configurar PATH para usar paquetes de usuario
ENV PATH=/home/appuser/.local/bin:$PATH

# Establecer directorio de trabajo
WORKDIR /app

# Copiar código de la aplicación
COPY --chown=appuser:appuser . .

# Cambiar a usuario no-root
USER appuser

# Exponer puerto
EXPOSE 5000

# Variables de entorno por defecto (pueden ser sobreescritas)
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000', timeout=5)"

# Comando de inicio
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
