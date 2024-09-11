#!/bin/bash

# Crear la estructura de directorios
mkdir -p app/{api/v1/endpoints,core,models,schemas,services}
mkdir -p tests/{api,services}
mkdir -p lambdas/{create_game,process_purchase,generate_winners,notify_players,generate_social_content}
mkdir -p infrastructure/{terraform,cloudformation}
mkdir -p scripts

# Crear archivos principales
touch app/main.py
touch app/api/dependencies.py
touch app/api/v1/api.py
touch app/core/{config.py,security.py,events.py}
touch tests/conftest.py

# Crear archivos de endpoints
for endpoint in auth users lotteries tickets payments; do
    touch app/api/v1/endpoints/${endpoint}.py
done

# Crear archivos de modelos y esquemas
for file in user lottery ticket payment; do
    touch app/models/${file}.py
    touch app/schemas/${file}.py
done

# Crear archivos de servicios
touch app/services/{lottery_integration.py,payment_gateway.py,notification_service.py}

# Crear archivos de Lambda
for lambda in create_game process_purchase generate_winners notify_players generate_social_content; do
    touch lambdas/${lambda}/handler.py
done

# Crear archivos de infraestructura
touch infrastructure/terraform/{main.tf,variables.tf,outputs.tf}
touch infrastructure/cloudformation/template.yaml

# Crear scripts
touch scripts/{deploy.sh,test.sh}

# Crear archivos de configuración
touch {.env,.env.example,requirements.txt,requirements-dev.txt}

echo "Estructura del proyecto creada con éxito."

# Crear un entorno virtual
python3 -m venv env

echo "Entorno virtual creado. Actívalo con 'source env/bin/activate'"

# Instalar FastAPI y dependencias básicas
venv/bin/pip install fastapi uvicorn

echo "FastAPI y Uvicorn instalados en el entorno virtual."

echo "Configuración completa. Puedes comenzar a trabajar en tu proyecto."
