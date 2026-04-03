#!/bin/bash

# Script de despliegue para desarrollo local

echo "Setting up development environment..."

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    python -m venv venv
fi

# Activar entorno virtual
source venv/Scripts/activate

# Instalar dependencias
pip install -r requirements.txt

# Instalar pre-commit hooks
pre-commit install

echo "Development environment setup complete!"