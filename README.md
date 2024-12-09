# Sistema de Loterías y Pagos

## Tabla de Contenidos
1. [Configuración del Sistema](#1-configuración-del-sistema)
2. [Estructura del Proyecto](#2-estructura-del-proyecto)
3. [Modelos de Datos](#3-modelos-de-datos)
4. [API Endpoints](#4-api-endpoints)
5. [Integración con Wompi](#5-integración-con-wompi)
6. [Guía de Instalación](#6-guía-de-instalación)
7. [Flujos del Sistema](#7-flujos-del-sistema)
8. [Seguridad](#8-seguridad)

## 1. Configuración del Sistema

### 1.1 Requisitos Técnicos
- Python 3.10+
- PostgreSQL 12+
- Redis (opcional, para caché)
- Git

### 1.2 Dependencias Principales
```txt
Django==5.1.2
djangorestframework==3.14.0
djangorestframework-simplejwt==5.3.1
psycopg2-binary==2.9.9
python-dotenv==1.0.0
requests==2.31.0
drf-yasg==1.21.7
```

### 1.3 Variables de Entorno
```env
# Django Settings
DEBUG=True
SECRET_KEY=tu-clave-secreta-aqui
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings
DB_NAME=lottery_db
DB_USER=postgres
DB_PASSWORD=tu-contraseña
DB_HOST=localhost
DB_PORT=5432

# JWT Settings
JWT_ACCESS_TOKEN_LIFETIME=1
JWT_REFRESH_TOKEN_LIFETIME=1440

# Wompi Settings
WOMPI_PUBLIC_KEY=pub_test_X9MFHHbwAZ9LKzVhYGbRH9PGZhvDq0Lw
WOMPI_PRIVATE_KEY=prv_test_kg1A0gyXlMYTwEuPbFHuXBgZ8gxmLFRF
WOMPI_EVENTS_KEY=test_events_XNxZcHJ08Nw9VWJ6blEldlYGRewLTlCN

# Site Settings
SITE_URL=http://localhost:8000
```

## 2. Estructura del Proyecto

```
backend_GOLD/
├── apps/
│   ├── default/               # Modelos y utilidades base
│   ├── authentication/        # Sistema de autenticación
│   ├── users/                # Gestión de usuarios
│   ├── lottery/              # Sistema de loterías
│   └── payments/             # Sistema de pagos
├── backend_GOLD/             # Configuración principal
├── manage.py
└── requirements.txt
```

## 3. Modelos de Datos

### 3.1 Usuarios (users.User)
```python
class User(AbstractUser, BaseModel):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    identification = models.CharField(max_length=20, unique=True)
    birth_date = models.DateField()
    is_active = models.BooleanField(default=True)
```

### 3.2 Loterías (lottery.Lottery)
```python
class Lottery(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    draw_day = models.CharField(max_length=10)
    fraction_count = models.PositiveIntegerField()
    fraction_price = models.DecimalField(max_digits=10, decimal_places=2)
    major_prize_amount = models.DecimalField(max_digits=20, decimal_places=2)
```

### 3.3 Transacciones (payments.Transaction)
```python
class Transaction(BaseModel):
    user = models.ForeignKey('users.User', on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    wompi_id = models.CharField(max_length=100)
    reference = models.CharField(max_length=100, unique=True)
    payment_method = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
```

## 4. API Endpoints

### 4.1 Autenticación
```http
POST /api/auth/login/
{
    "phone_number": "string",
    "pin": "string"
}

POST /api/auth/logout/
{
    "refresh_token": "string"
}
```

### 4.2 Loterías
```http
GET /api/lottery/results/
GET /api/lottery/results/{id}/
GET /api/lottery/results/latest/

POST /api/lottery/bets/
{
    "lottery": "uuid",
    "number": "1234",
    "series": "123",
    "amount": 5000
}

GET /api/lottery/bets/history/
```

### 4.3 Pagos
```http
POST /api/payments/tokenize_card/
{
    "number": "4242424242424242",
    "cvc": "123",
    "exp_month": "12",
    "exp_year": "25",
    "card_holder": "NOMBRE"
}

POST /api/payments/create_transaction/
{
    "amount": 50000,
    "payment_method": "CARD",
    "card_token": "tok_test_..."
}

GET /api/payments/balance/
GET /api/payments/history/
```

## 5. Integración con Wompi

### 5.1 Ambiente de Pruebas
- URL Base: https://sandbox.wompi.co/v1
- Tarjetas de prueba:
  ```
  Exitosa: 4242424242424242
  Rechazada: 4111111111111111
  ```

### 5.2 Flujo de Pago
1. Tokenización de tarjeta
2. Creación de transacción
3. Procesamiento de pago
4. Verificación de estado
5. Actualización de saldo

## 6. Guía de Instalación

### 6.1 Configuración Inicial
```bash
# Clonar repositorio
git clone <repository-url>
cd backend_GOLD

# Crear entorno virtual
python -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar base de datos
createdb lottery_db
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar servidor
python manage.py runserver
```

### 6.2 Configuración de Wompi
1. Registrarse en comercios.wompi.co
2. Obtener llaves de prueba
3. Configurar Webhook URL
4. Configurar URLs de redirección

## 7. Flujos del Sistema

### 7.1 Flujo de Apuesta
1. Usuario verifica saldo
2. Selecciona lotería
3. Ingresa número y serie
4. Confirma apuesta
5. Se descuenta saldo

### 7.2 Flujo de Pago
1. Usuario inicia transacción
2. Selecciona método de pago
3. Completa información
4. Wompi procesa pago
5. Sistema actualiza saldo

## 8. Seguridad

### 8.1 Autenticación
- JWT Token
- Expiración de token: 1 minuto
- Refresh token: 24 horas

### 8.2 Permisos
```python
# Permisos personalizados para cada vista
class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
```

### 8.3 Validaciones
- Verificación de edad
- Límites de montos
- Formato de números
- Estados de transacciones

## 9. Mantenimiento

### 9.1 Logs
- Transacciones
- Errores de pago
- Intentos de autenticación
- Resultados de loterías

### 9.2 Monitoreo
- Estado de transacciones
- Saldos de usuarios
- Resultados de sorteos
- Wompi webhooks

### 9.3 Backups
- Base de datos: diario
- Archivos media: semanal
- Logs: rotación semanal