# backend_project_GOLD

# Lottery Aggregator Platform(provisional)

Este proyecto es una plataforma agregadora de loterías construida con FastAPI y servicios de AWS para una infraestructura serverless y escalable.

## Estructura del Proyecto

```
lottery_aggregator/
│
├── app/                  # Código principal de la aplicación
│   ├── api/              # Definiciones de la API
│   ├── core/             # Configuraciones centrales
│   ├── models/           # Modelos de la base de datos
│   ├── schemas/          # Esquemas Pydantic
│   ├── services/         # Lógica de negocio
│   └── main.py           # Punto de entrada de la aplicación
│
├── tests/                # Pruebas
├── lambdas/              # Funciones AWS Lambda
├── infrastructure/       # Código de infraestructura (Terraform, CloudFormation)
├── scripts/              # Scripts de utilidad
└── ...                   # Otros archivos de configuración
```

## Requisitos

- Python 3.8+
- FastAPI
- Uvicorn (para servidor ASGI)
- AWS CLI configurado (para despliegue)
- Terraform (para gestión de infraestructura)

## Configuración del Entorno

1. Clonar el repositorio:
   ```
   git clone https://github.com/tu-usuario/lottery-aggregator.git
   cd lottery-aggregator
   ```

2. Crear y activar un entorno virtual:
   ```
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instalar las dependencias:
   ```
   pip install -r requirements.txt
   ```

4. Configurar las variables de entorno:
   ```
   cp .env.example .env
   # Edita .env con tus configuraciones
   ```

## Ejecución del Proyecto

Para ejecutar el proyecto localmente:

```
uvicorn app.main:app --reload
```

La API estará disponible en `http://localhost:8000`.

## Pruebas

Para ejecutar las pruebas:

```
pytest
```

## Despliegue

1. Asegúrate de tener AWS CLI configurado correctamente.

2. Usa el script de despliegue:
   ```
   ./scripts/deploy.sh
   ```

## Desarrollo

- La lógica principal de la API se encuentra en `app/api/v1/endpoints/`.
- Los modelos de datos están en `app/models/`.
- Los esquemas de validación están en `app/schemas/`.
- La lógica de negocio se implementa en `app/services/`.

## Licencia

[MIT License](LICENSE)
