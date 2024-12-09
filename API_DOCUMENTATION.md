# Documentación Detallada API - Sistema de Loterías y Pagos

## Tabla de Contenidos
1. [Introducción](#1-introducción)
2. [Autenticación](#2-autenticación)
3. [Loterías](#3-loterías)
4. [Apuestas](#4-apuestas)
5. [Pagos](#5-pagos)
6. [Manejo de Errores](#6-manejo-de-errores)
7. [Webhooks](#7-webhooks)
8. [Buenas Prácticas](#8-buenas-prácticas)

## 1. Introducción

### 1.1 Base URL
```
Desarrollo: http://localhost:8000/api
Producción: https://api.tudominio.com/api
```

### 1.2 Versionado
La API está actualmente en su versión 1. El versionado está incluido en la URL base.

### 1.3 Formatos
- Todas las solicitudes deben enviar y recibir datos en formato JSON
- Las fechas se manejan en formato ISO 8601: `YYYY-MM-DDTHH:mm:ssZ`
- Los montos se manejan en centavos (sin decimales)

## 2. Autenticación

### 2.1 Login

**Endpoint:** `POST /api/auth/login/`

**Descripción:** Autentica al usuario y retorna tokens de acceso y refresco.

**Request Body:**
```json
{
    "phone_number": "+573001234567",
    "pin": "1234"
}
```

**Response Exitosa (200 OK):**
```json
{
    "tokens": {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    },
    "user": {
        "id": "uuid",
        "phone_number": "+573001234567",
        "email": "usuario@ejemplo.com",
        "first_name": "Juan",
        "last_name": "Pérez",
        "balance": {
            "amount": 150000,
            "last_updated": "2024-12-09T10:00:00Z"
        }
    }
}
```

**Posibles Errores:**
```json
// 400 Bad Request - Credenciales incorrectas
{
    "error": "Credenciales inválidas",
    "code": "INVALID_CREDENTIALS"
}

// 400 Bad Request - Usuario inactivo
{
    "error": "Usuario inactivo",
    "code": "INACTIVE_USER"
}
```

### 2.2 Refresh Token

**Endpoint:** `POST /api/auth/token/refresh/`

**Request Body:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response Exitosa (200 OK):**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

## 3. Loterías

### 3.1 Listar Loterías Disponibles

**Endpoint:** `GET /api/lottery/`

**Headers:**
```http
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `active` (boolean): Filtrar solo loterías activas
- `draw_day` (string): Filtrar por día de sorteo
- `page` (int): Número de página
- `page_size` (int): Elementos por página

**Response Exitosa (200 OK):**
```json
{
    "count": 15,
    "next": "http://api.../lottery/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "name": "Lotería de Boyacá",
            "code": "BOYACA",
            "draw_day": "SATURDAY",
            "draw_time": "22:30:00",
            "next_draw": "2024-12-14T22:30:00Z",
            "major_prize": {
                "amount": "15000000000",
                "fraction_amount": "2490000000"
            },
            "fractions": {
                "count": 4,
                "price": "5000"
            },
            "betting_limits": {
                "min": "5000",
                "max": "15000000000"
            },
            "status": {
                "is_active": true,
                "can_bet": true,
                "closes_in": "2h 30m"
            }
        }
    ]
}
```

### 3.2 Obtener Detalle de Lotería

**Endpoint:** `GET /api/lottery/{lottery_id}/`

**Response Exitosa (200 OK):**
```json
{
    "id": "uuid",
    "name": "Lotería de Boyacá",
    "code": "BOYACA",
    "draw_day": "SATURDAY",
    "draw_time": "22:30:00",
    "next_draw": "2024-12-14T22:30:00Z",
    "major_prize": {
        "amount": "15000000000",
        "fraction_amount": "2490000000"
    },
    "fractions": {
        "count": 4,
        "price": "5000"
    },
    "prize_plan": {
        "major": {
            "amount": "15000000000",
            "description": "Premio Mayor"
        },
        "secos": [
            {
                "name": "Premio Fortuna",
                "amount": "1000000000",
                "quantity": 1
            },
            // ... más premios secos
        ],
        "approximations": {
            "same_series": [
                {
                    "description": "Tres primeras cifras",
                    "amount": "20000000",
                    "quantity": 9
                },
                // ... más aproximaciones
            ],
            "different_series": [
                {
                    "description": "Mayor en diferente serie",
                    "amount": "4000000",
                    "quantity": 469
                },
                // ... más aproximaciones
            ]
        }
    },
    "last_results": {
        "date": "2024-12-07",
        "winning_number": "1234",
        "series": "123",
        "winners": {
            "major": 1,
            "secos": 5,
            "approximations": 156
        }
    }
}
```

### 3.3 Obtener Últimos Resultados

**Endpoint:** `GET /api/lottery/results/`

**Query Parameters:**
- `lottery_id` (uuid): Filtrar por lotería específica
- `start_date` (YYYY-MM-DD): Fecha inicial
- `end_date` (YYYY-MM-DD): Fecha final
- `page` (int): Número de página
- `page_size` (int): Elementos por página

**Response Exitosa (200 OK):**
```json
{
    "count": 45,
    "next": "http://api.../lottery/results/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid",
            "lottery": {
                "id": "uuid",
                "name": "Lotería de Boyacá",
                "code": "BOYACA"
            },
            "draw_date": "2024-12-07",
            "draw_number": "2720",
            "winning_number": "1234",
            "series": "123",
            "prizes_awarded": {
                "major": {
                    "number": "1234",
                    "series": "123",
                    "amount": "15000000000",
                    "winners": 1
                },
                "secos": [
                    {
                        "name": "Premio Fortuna",
                        "number": "5678",
                        "series": "456",
                        "amount": "1000000000",
                        "winners": 1
                    }
                ],
                "approximations": {
                    "same_series": [
                        {
                            "type": "THREE_FIRST",
                            "winners": 9,
                            "amount_per_winner": "20000000"
                        }
                    ]
                }
            }
        }
    ]
}
```

## 4. Apuestas

### 4.1 Crear Apuesta

**Endpoint:** `POST /api/lottery/bets/`

**Headers:**
```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
    "lottery_id": "uuid-loteria",
    "number": "1234",
    "series": "123",
    "amount": 5000,
    "fractions": 1,
    "payment_type": "BALANCE", // BALANCE o DIRECT
    "payment_data": {
        // Solo si payment_type es DIRECT
        "payment_method": "CARD",
        "token": "tok_test_..."
    }
}
```

**Response Exitosa (201 Created):**
```json
{
    "id": "uuid-apuesta",
    "created_at": "2024-12-09T10:00:00Z",
    "lottery": {
        "id": "uuid-loteria",
        "name": "Lotería de Boyacá"
    },
    "number": "1234",
    "series": "123",
    "amount": 5000,
    "fractions": 1,
    "status": "PENDING",
    "draw_date": "2024-12-14",
    "payment": {
        "type": "BALANCE",
        "status": "COMPLETED",
        "transaction_id": "uuid-transaction" // Si es pago directo
    },
    "potential_prizes": {
        "major": {
            "amount": "2490000000",
            "description": "Premio Mayor Completo"
        },
        "approximations": [
            {
                "type": "THREE_FIRST",
                "amount": "20000000",
                "description": "Tres primeras cifras"
            }
        ]
    }
}
```

**Validaciones y Errores:**
```json
// 400 Bad Request - Número inválido
{
    "error": "Número debe ser de 4 dígitos",
    "code": "INVALID_NUMBER",
    "field": "number"
}

// 400 Bad Request - Serie inválida
{
    "error": "Serie debe corresponder al rango de la lotería",
    "code": "INVALID_SERIES",
    "field": "series"
}

// 400 Bad Request - Saldo insuficiente
{
    "error": "Saldo insuficiente para realizar la apuesta",
    "code": "INSUFFICIENT_BALANCE",
    "current_balance": 3000,
    "required_amount": 5000
}

// 400 Bad Request - Lotería cerrada
{
    "error": "La lotería está cerrada para apuestas",
    "code": "LOTTERY_CLOSED",
    "closes_at": "2024-12-14T20:00:00Z"
}
```

### 4.2 Listar Apuestas

**Endpoint:** `GET /api/lottery/bets/`

**Query Parameters:**
- `status` (string): PENDING, PLAYED, WON, LOST
- `lottery_id` (uuid): Filtrar por lotería
- `start_date` (YYYY-MM-DD): Fecha inicial
- `end_date` (YYYY-MM-DD): Fecha final
- `page` (int): Número de página
- `page_size` (int): Elementos por página

**Response Exitosa (200 OK):**
```json
{
    "count": 25,
    "next": "http://api.../bets/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid-apuesta",
            "created_at": "2024-12-09T10:00:00Z",
            "lottery": {
                "id": "uuid-loteria",
                "name": "Lotería de Boyacá",
                "draw_day": "SATURDAY"
            },
            "number": "1234",
            "series": "123",
            "amount": 5000,
            "status": "PLAYED",
            "draw_date": "2024-12-07",
            "result": {
                "status": "WON",
                "winning_number": "1234",
                "winning_series": "123",
                "prize_type": "THREE_FIRST",
                "prize_amount": 20000000,
                "claimed_at": "2024-12-08T10:00:00Z"
            },
            "payment": {
                "type": "BALANCE",
                "status": "COMPLETED",
                "transaction_id": "uuid-transaction"
            }
        }
    ]
}
```

### 4.3 Obtener Detalle de Apuesta

**Endpoint:** `GET /api/lottery/bets/{bet_id}/`

**Response Exitosa (200 OK):**
```json
{
    "id": "uuid-apuesta",
    "created_at": "2024-12-09T10:00:00Z",
    "updated_at": "2024-12-09T10:00:00Z",
    "lottery": {
        "id": "uuid-loteria",
        "name": "Lotería de Boyacá",
        "draw_day": "SATURDAY",
        "draw_time": "22:30:00"
    },
    "number": "1234",
    "series": "123",
    "amount": 5000,
    "fractions": 1,
    "status": "PENDING",
    "draw_date": "2024-12-14",
    "payment": {
        "type": "DIRECT",
        "method": "CARD",
        "status": "COMPLETED",
        "transaction": {
            "id": "uuid-transaction",
            "created_at": "2024-12-09T10:00:00Z",
            "status": "APPROVED",
            "payment_method": {
                "type": "CARD",
                "last_four": "4242",
                "brand": "VISA"
            }
        }
    },
    "potential_prizes": {
        "major": {
            "amount": "2490000000",
            "description": "Premio Mayor Completo"
        },
        "approximations": [
            {
                "type": "THREE_FIRST",
                "amount": "20000000",
                "description": "Tres primeras cifras"
            }
        ]
    },
    "result": null // Se actualiza después del sorteo
}
```

### 4.4 Cancelar Apuesta

**Endpoint:** `POST /api/lottery/bets/{bet_id}/cancel/`

**Condiciones:**
- Solo se puede cancelar si la lotería aún no está cerrada
- Solo el propietario puede cancelar
- Solo apuestas en estado PENDING

**Response Exitosa (200 OK):**
```json
{
    "id": "uuid-apuesta",
    "status": "CANCELLED",
    "cancelled_at": "2024-12-09T11:00:00Z",
    "refund": {
        "amount": 5000,
        "type": "BALANCE",
        "status": "COMPLETED"
    }
}
```

## 5. Pagos

### 5.1 Métodos de Pago Disponibles

#### 5.1.1 Tarjeta de Crédito/Débito
- Visa
- MasterCard
- American Express
- Diners Club

#### 5.1.2 Transferencias
- PSE (Bancos colombianos)
- Nequi
- Bancolombia Transfer

#### 5.1.3 Efectivo
- Bancolombia Corresponsales
- Efecty (próximamente)

### 5.2 Tokenización de Tarjeta

**Endpoint:** `POST /api/payments/tokenize_card/`

**Headers:**
```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
    "number": "4242424242424242",
    "cvc": "123",
    "exp_month": "12",
    "exp_year": "25",
    "card_holder": "JUAN PEREZ"
}
```

**Response Exitosa (200 OK):**
```json
{
    "id": "tok_test_123...",
    "created_at": "2024-12-09T10:00:00Z",
    "brand": "VISA",
    "name": "VISA-4242",
    "last_four": "4242",
    "bin": "424242",
    "exp_year": "25",
    "exp_month": "12",
    "card_holder": "JUAN PEREZ",
    "expires_at": "2024-12-09T11:00:00Z"
}
```

**Tarjetas de Prueba:**
```text
// Tarjeta Aprobada
Número: 4242424242424242
CVC: Cualquier número de 3 dígitos
Fecha: Cualquier fecha futura

// Tarjeta Declinada
Número: 4111111111111111
CVC: Cualquier número de 3 dígitos
Fecha: Cualquier fecha futura
```

### 5.3 Crear Transacción

#### 5.3.1 Pago con Tarjeta

**Endpoint:** `POST /api/payments/create_transaction/`

**Request Body:**
```json
{
    "amount": 50000,
    "payment_method": {
        "type": "CARD",
        "token": "tok_test_123..."
    },
    "currency": "COP",
    "description": "Recarga de saldo",
    "payment_type": "BALANCE_RECHARGE"
}
```

#### 5.3.2 Pago con Nequi

**Request Body:**
```json
{
    "amount": 50000,
    "payment_method": {
        "type": "NEQUI",
        "phone_number": "3001234567"
    },
    "currency": "COP",
    "description": "Recarga de saldo",
    "payment_type": "BALANCE_RECHARGE"
}
```

#### 5.3.3 Pago con PSE

**Request Body:**
```json
{
    "amount": 50000,
    "payment_method": {
        "type": "PSE",
        "bank_code": "1022",
        "document_type": "CC",
        "document_number": "123456789",
        "email": "usuario@ejemplo.com"
    },
    "currency": "COP",
    "description": "Recarga de saldo",
    "payment_type": "BALANCE_RECHARGE"
}
```

**Response Exitosa (200 OK):**
```json
{
    "id": "transaction-id",
    "created_at": "2024-12-09T10:00:00Z",
    "status": "PENDING",
    "amount": 50000,
    "currency": "COP",
    "payment_method": {
        "type": "CARD",
        "last_four": "4242",
        "brand": "VISA"
    },
    "payment_type": "BALANCE_RECHARGE",
    "redirect_url": null, // URL para PSE o otros métodos que requieren redirección
    "processing_url": null // URL para métodos que requieren procesamiento adicional
}
```

### 5.4 Verificar Estado de Transacción

**Endpoint:** `GET /api/payments/transactions/{transaction_id}/`

**Response Exitosa (200 OK):**
```json
{
    "id": "transaction-id",
    "created_at": "2024-12-09T10:00:00Z",
    "updated_at": "2024-12-09T10:01:00Z",
    "status": "APPROVED",
    "amount": 50000,
    "currency": "COP",
    "payment_method": {
        "type": "CARD",
        "last_four": "4242",
        "brand": "VISA",
        "installments": 1
    },
    "payment_type": "BALANCE_RECHARGE",
    "status_detail": {
        "status": "APPROVED",
        "message": "Transacción aprobada",
        "code": "200",
        "reason": "00"
    }
}
```

### 5.5 Consultar Balance

**Endpoint:** `GET /api/payments/balance/`

**Response Exitosa (200 OK):**
```json
{
    "balance": 150000,
    "last_updated": "2024-12-09T10:00:00Z",
    "available_for_bets": true,
    "transactions": {
        "count": 10,
        "last_transaction": {
            "id": "transaction-id",
            "type": "DEPOSIT",
            "amount": 50000,
            "created_at": "2024-12-09T10:00:00Z",
            "status": "APPROVED"
        }
    }
}
```

### 5.6 Historial de Transacciones

**Endpoint:** `GET /api/payments/transactions/`

**Query Parameters:**
- `status`: PENDING, APPROVED, DECLINED, ERROR
- `payment_method`: CARD, NEQUI, PSE
- `start_date`: YYYY-MM-DD
- `end_date`: YYYY-MM-DD
- `type`: DEPOSIT, WITHDRAWAL, BET
- `page`: Número de página
- `page_size`: Elementos por página

**Response Exitosa (200 OK):**
```json
{
    "count": 25,
    "next": "http://api.../transactions/?page=2",
    "previous": null,
    "results": [
        {
            "id": "transaction-id",
            "created_at": "2024-12-09T10:00:00Z",
            "status": "APPROVED",
            "amount": 50000,
            "currency": "COP",
            "payment_method": {
                "type": "CARD",
                "last_four": "4242",
                "brand": "VISA"
            },
            "payment_type": "BALANCE_RECHARGE",
            "related_bet": null // ID de apuesta si es un pago de apuesta
        }
    ]
}
```

## 6. Manejo de Errores

### 6.1 Estructura de Errores
Todos los errores siguen esta estructura:
```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Mensaje descriptivo del error",
        "details": {}, // Detalles adicionales específicos del error
        "field": "campo_con_error" // Solo en errores de validación
    }
}
```

### 6.2 Códigos de Estado HTTP
- `200 OK`: Solicitud exitosa
- `201 Created`: Recurso creado exitosamente
- `400 Bad Request`: Error en la solicitud
- `401 Unauthorized`: Token inválido o expirado
- `403 Forbidden`: Sin permisos para el recurso
- `404 Not Found`: Recurso no encontrado
- `409 Conflict`: Conflicto con el estado actual
- `422 Unprocessable Entity`: Error de validación
- `500 Internal Server Error`: Error del servidor

### 6.3 Códigos de Error Específicos

#### 6.3.1 Errores de Autenticación
```json
{
    "error": {
        "code": "INVALID_CREDENTIALS",
        "message": "Credenciales inválidas"
    }
}

{
    "error": {
        "code": "TOKEN_EXPIRED",
        "message": "Token expirado",
        "details": {
            "expired_at": "2024-12-09T10:00:00Z"
        }
    }
}
```

#### 6.3.2 Errores de Apuestas
```json
{
    "error": {
        "code": "LOTTERY_CLOSED",
        "message": "Lotería cerrada para apuestas",
        "details": {
            "closes_at": "2024-12-14T20:00:00Z",
            "current_time": "2024-12-14T20:30:00Z"
        }
    }
}

{
    "error": {
        "code": "INSUFFICIENT_BALANCE",
        "message": "Saldo insuficiente",
        "details": {
            "current_balance": 3000,
            "required_amount": 5000
        }
    }
}
```

#### 6.3.3 Errores de Pago
```json
{
    "error": {
        "code": "PAYMENT_DECLINED",
        "message": "Pago rechazado por el banco",
        "details": {
            "reason": "INSUFFICIENT_FUNDS",
            "bank_message": "Fondos insuficientes"
        }
    }
}
```

## 7. Webhooks

### 7.1 Configuración
Los webhooks deben configurarse en el panel de administración proporcionando una URL HTTPS válida.

### 7.2 Eventos Disponibles

#### 7.2.1 Transacciones
```json
{
    "event": "transaction.updated",
    "data": {
        "transaction_id": "uuid",
        "status": "APPROVED",
        "created_at": "2024-12-09T10:00:00Z",
        "amount": 50000,
        "currency": "COP"
    },
    "sent_at": "2024-12-09T10:01:00Z"
}
```

#### 7.2.2 Resultados de Lotería
```json
{
    "event": "lottery.result",
    "data": {
        "lottery_id": "uuid",
        "draw_date": "2024-12-14",
        "winning_number": "1234",
        "series": "123"
    },
    "sent_at": "2024-12-14T22:35:00Z"
}
```

#### 7.2.3 Estado de Apuestas
```json
{
    "event": "bet.status_updated",
    "data": {
        "bet_id": "uuid",
        "status": "WON",
        "prize_amount": 20000000,
        "updated_at": "2024-12-14T22:40:00Z"
    },
    "sent_at": "2024-12-14T22:40:00Z"
}
```

### 7.3 Seguridad de Webhooks
- Cada webhook incluye una firma en el header `X-Wompi-Signature`
- La firma debe validarse usando la clave secreta proporcionada
- Los eventos se reenvían en caso de fallo hasta 5 veces

## 8. Buenas Prácticas

### 8.1 Manejo de Tokens
```javascript
// Ejemplo de manejo de tokens en el cliente
class TokenManager {
    static async refreshTokenIfNeeded() {
        const expiresAt = localStorage.getItem('tokenExpiresAt');
        if (Date.now() >= expiresAt - 30000) { // 30 segundos antes
            await this.refreshToken();
        }
    }

    static async refreshToken() {
        const refresh = localStorage.getItem('refreshToken');
        const response = await api.post('/auth/token/refresh/', { refresh });
        this.setTokens(response.data);
    }
}
```

### 8.2 Polling de Estado
```javascript
// Ejemplo de polling para estado de transacción
async function checkTransactionStatus(transactionId) {
    const maxAttempts = 20;
    const interval = 3000;
    let attempts = 0;

    while (attempts < maxAttempts) {
        const response = await api.get(`/payments/transactions/${transactionId}/`);
        if (response.data.status !== 'PENDING') {
            return response.data;
        }
        await new Promise(resolve => setTimeout(resolve, interval));
        attempts++;
    }
    throw new Error('Transaction timeout');
}
```

### 8.3 Manejo de Errores en Cliente
```javascript
async function handleApiError(error) {
    if (error.response) {
        switch (error.response.status) {
            case 401:
                await TokenManager.refreshTokenIfNeeded();
                // Reintentar solicitud
                break;
            case 403:
                // Redirigir a login
                break;
            case 422:
                // Mostrar errores de validación
                const errors = error.response.data.error.details;
                break;
            default:
                // Mostrar error genérico
        }
    }
}
```

### 8.4 Validaciones Recomendadas
- Validar formato de números antes de enviar
- Verificar montos mínimos y máximos
- Confirmar horarios de lotería
- Validar saldo disponible
- Verificar estado de transacciones anteriores
