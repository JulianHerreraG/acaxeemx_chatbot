# Guía de Arquitectura

## Visión General

Esta arquitectura está diseñada para un chatbot escalable y mantenible usando Python, Firebase y APIs de LLM.

## Componentes Principales

### 1. API Layer (src/api/)
- **FastAPI**: Framework web asíncrono para endpoints REST
- Endpoints principales: `/chat`, `/health`

### 2. Business Logic (src/chatbot/)
- **ChatbotService**: Orquesta la lógica del chatbot
- Manejo de conversaciones y contexto

### 3. Data Layer (src/database/)
- **FirebaseClient**: Abstracción para Firestore
- Almacenamiento de conversaciones

### 4. LLM Integration (src/llm/)
- **LLMClient**: Interfaz común para proveedores de LLM
- Implementaciones específicas para OpenAI y Anthropic

### 5. Configuration (src/config.py)
- Gestión centralizada de configuración
- Variables de entorno

### 6. Utils (src/utils/)
- Funciones auxiliares
- Logging y validación

## Buenas Prácticas Implementadas

- **Separación de responsabilidades**: Cada módulo tiene una responsabilidad clara
- **Inyección de dependencias**: Configuración externa
- **Testing**: Cobertura con pytest
- **Linting**: Black, Flake8, MyPy
- **CI/CD**: GitHub Actions
- **Contenedorización**: Docker
- **Gestión de dependencias**: requirements.txt y pyproject.toml

## Escalabilidad

- Arquitectura modular permite agregar nuevos proveedores de LLM
- Firebase escala automáticamente
- API REST permite integración con múltiples clientes

## Seguridad

- API keys en variables de entorno
- Validación de entrada con Pydantic
- Manejo de errores apropiado