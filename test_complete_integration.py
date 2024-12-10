import requests
import json
import uuid
from datetime import datetime, timedelta
import time
from typing import Dict, List, Any


class CompleteIntegrationTest:
    def __init__(self, base_url: str, wompi_keys: Dict[str, str], lottery_api_key: str):
        self.base_url = base_url
        self.wompi_base_url = "https://sandbox.wompi.co/v1"
        self.wompi_keys = wompi_keys
        self.lottery_api_key = lottery_api_key
        self.access_token = None
        self.user_data = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0
            }
        }

    def _add_test_result(self, name: str, success: bool, data: Dict[str, Any]):
        self.results["tests"].append({
            "name": name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        self.results["summary"]["total"] += 1
        if success:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1

    def _get_headers(self, with_auth: bool = True) -> Dict:
        headers = {
            'Content-Type': 'application/json'
        }
        if with_auth and self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        return headers

    def test_registration(self) -> bool:
        """Prueba el registro de usuario"""
        test_name = "User Registration"
        try:
            data = {
                "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
                "phone_number": f"+5730{uuid.uuid4().hex[:8]}"[:15],
                "first_name": "Test",
                "last_name": "User",
                "identification": f"CC{uuid.uuid4().hex[:8]}",
                "pin": "1234",
                "birth_date": "1990-01-01"
            }

            response = requests.post(
                f"{self.base_url}/users/",
                headers=self._get_headers(False),
                json=data
            )

            success = response.status_code == 201
            self._add_test_result(
                test_name,
                success,
                {
                    "status_code": response.status_code,
                    "response": response.json()
                }
            )

            if success:
                self.user_data = data

            return success

        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return False

    def test_login(self) -> bool:
        """Prueba el login"""
        test_name = "User Login"
        try:
            data = {
                "phone_number": self.user_data["phone_number"],
                "pin": self.user_data["pin"]
            }

            response = requests.post(
                f"{self.base_url}/auth/login/",
                headers=self._get_headers(False),
                json=data
            )

            success = response.status_code == 200
            response_data = response.json()
            
            if success:
                self.access_token = response_data["tokens"]["access"]

            self._add_test_result(
                test_name,
                success,
                {
                    "status_code": response.status_code,
                    "response": response_data
                }
            )

            return success

        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return False

    def test_get_available_lotteries(self) -> List[Dict]:
        """Prueba obtener loterías disponibles"""
        test_name = "Get Available Lotteries"
        try:
            response = requests.get(
                "https://lottery-results-api.onrender.com/results",
                headers={
                    **self._get_headers(),
                    'x-api-key': self.lottery_api_key
                }
            )

            success = response.status_code == 200
            response_data = response.json()

            self._add_test_result(
                test_name,
                success,
                {
                    "status_code": response.status_code,
                    "response": response_data
                }
            )

            return response_data if success and isinstance(response_data, list) else []

        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return []

    def test_card_payment(self) -> Dict:
        """Prueba el flujo completo de pago con tarjeta"""
        # 1. Tokenizar tarjeta
        card_token = self.tokenize_test_card()
        if not card_token:
            return None

        # 2. Crear transacción
        transaction = self.create_transaction(card_token)
        if not transaction:
            return None

        # 3. Verificar estado de transacción
        return self.verify_transaction(transaction.get("id"))

    def tokenize_test_card(self) -> str:
        """Tokeniza una tarjeta de prueba"""
        test_name = "Card Tokenization"
        try:
            response = requests.post(
                f"{self.wompi_base_url}/tokens/cards",
                headers={
                    'Authorization': f'Bearer {self.wompi_keys["public_key"]}'
                },
                json={
                    "number": "4242424242424242",
                    "cvc": "123",
                    "exp_month": "12",
                    "exp_year": "28",
                    "card_holder": "Test User"
                }
            )

            success = response.status_code == 201
            response_data = response.json()

            self._add_test_result(
                test_name,
                success,
                {
                    "status_code": response.status_code,
                    "response": response_data
                }
            )

            return response_data.get("data", {}).get("id") if success else None

        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def create_transaction(self, card_token: str) -> Dict:
        """Crea una transacción de pago"""
        test_name = "Create Payment Transaction"
        try:
            print("\n" + "="*50)
            print("INICIANDO CREACIÓN DE TRANSACCIÓN")
            print("="*50)

            print("\n[1] VALIDACIÓN DE DATOS INICIALES")
            print(f"✓ Card token recibido: {card_token}")
            print(f"✓ Card token length: {len(card_token)}")
            print(f"✓ Card token format check: {'tok_test' in card_token}")
            print(f"✓ Public key disponible: {bool(self.wompi_keys.get('public_key'))}")
            print(f"✓ Integrity key disponible: {bool(self.wompi_keys.get('integrity_key'))}")

            print("\n[2] OBTENCIÓN DE ACCEPTANCE TOKEN")
            acceptance_token = self.get_acceptance_token()
            print(f"✓ Token obtenido: {acceptance_token[:30]}...")
            print(f"✓ Token length: {len(acceptance_token)}")

            print("\n[3] GENERACIÓN DE DATOS DE TRANSACCIÓN")
            reference = f"TEST-{uuid.uuid4().hex[:8]}"
            amount_in_cents = 5000000  # $50.000
            currency = "COP"
            payment_method_type = "CARD"
            
            print(f"✓ Reference generada: {reference}")
            print(f"✓ Reference format check: {'TEST-' in reference}")
            print(f"✓ Monto en centavos: {amount_in_cents} ({amount_in_cents/100} {currency})")
            
            print("\n[4] CONSTRUCCIÓN DE FIRMA DE INTEGRIDAD")
            print("Elementos en orden según documentación Wompi:")
            
            # El orden correcto es: reference + amount + currency + integrity_key
            signature_elements = [
                ("Reference", reference),
                ("Amount", str(amount_in_cents)),
                ("Currency", currency),
                ("Integrity Key", self.wompi_keys['integrity_key'])
            ]

            # Construir el string de integridad en el orden documentado
            integrity_string = ''.join(value for _, value in signature_elements)
            
            # Logging de cada elemento
            print("\nValidación de elementos:")
            for name, value in signature_elements[:-1]:  # Excluimos integrity key del log
                print(f"• {name}:")
                print(f"   - Valor: {value}")
                print(f"   - Tipo: {type(value)}")
                print(f"   - Longitud: {len(value)}")
                print(f"   - Encoding check: {value.encode('utf-8')[:10]}")
            print("• Integrity Key: [HIDDEN]")

            print("\n[5] GENERACIÓN DE HASH")
            masked_string = integrity_string.replace(self.wompi_keys['integrity_key'], 'INTEGRITY_KEY')
            print(f"✓ String completo para hash (masked): {masked_string}")
            print(f"✓ String length: {len(integrity_string)}")
            
            # Generar hash según documentación Wompi
            import hashlib
            m = hashlib.sha256()
            m.update(integrity_string.encode())
            integrity = m.hexdigest()
            
            print(f"✓ Hash generado: {integrity}")
            print(f"✓ Hash length: {len(integrity)}")
            print(f"✓ Hash validation: {all(c in '0123456789abcdef' for c in integrity)}")
            
            data = {
                "amount_in_cents": amount_in_cents,
                "currency": currency,
                "customer_email": self.user_data["email"],
                "reference": reference,
                "payment_method": {
                    "type": payment_method_type,
                    "token": card_token,
                    "installments": 1
                },
                "acceptance_token": acceptance_token,
                "signature": integrity
            }

            print("\n[6] CONSTRUCCIÓN DE PAYLOAD")
            print("Payload completo (datos sensibles ocultos):")
            masked_data = {
                **data,
                "debug_info": {
                    "signature_components": {
                        "reference": reference,
                        "amount": str(amount_in_cents),
                        "currency": currency,
                        "integrity_key": "HIDDEN"
                    },
                    "signature_string": masked_string,
                    "final_hash": integrity
                }
            }
            print(json.dumps(masked_data, indent=2))

            print("\n[7] ENVIANDO PETICIÓN")
            print(f"URL: {self.wompi_base_url}/transactions")
            print("Headers:", {
                'Authorization': f'Bearer {self.wompi_keys["public_key"][:10]}...',
                'Content-Type': 'application/json'
            })

            response = requests.post(
                f"{self.wompi_base_url}/transactions",
                headers={
                    'Authorization': f'Bearer {self.wompi_keys["public_key"]}',
                    'Content-Type': 'application/json'
                },
                json=data
            )

            success = response.status_code == 201
            response_data = response.json()

            print("\n[8] RESPUESTA RECIBIDA")
            print(f"✓ Status Code: {response.status_code}")
            print(f"✓ Success: {success}")
            print("Response headers:", dict(response.headers))
            print("\nResponse body:")
            print(json.dumps(response_data, indent=2))

            if not success:
                print("\n❌ ERROR EN LA TRANSACCIÓN")
                print("-"*50)
                if "error" in response_data:
                    print(f"Tipo de error: {response_data['error'].get('type')}")
                    print("\nMensajes de error:")
                    for field, messages in response_data['error'].get('messages', {}).items():
                        print(f"• {field}: {', '.join(messages)}")
                
                print("\nInformación de debugging adicional:")
                print("1. Valores de entrada:")
                print(f"   • Amount: {amount_in_cents} cents = ${amount_in_cents/100}")
                print(f"   • Currency: {currency}")
                print(f"   • Reference format: {reference}")
                print(f"   • Payment method: {payment_method_type}")
                print(f"   • Card token format: {card_token}")
                print("\n2. Generación de firma:")
                print(f"   • Raw string length: {len(integrity_string)}")
                print(f"   • Final hash length: {len(integrity)}")
                print(f"   • Hash validation: {'Passed' if len(integrity) == 64 else 'Failed'}")
                print(f"   • Signature components order: reference > amount > currency > integrity_key")
                
            self._add_test_result(
                test_name,
                success,
                {
                    "status_code": response.status_code,
                    "response": response_data,
                    "request_data": masked_data,
                    "debug_info": {
                        "signature_process": {
                            "components_order": [
                                "reference",
                                "amount",
                                "currency",
                                "integrity_key"
                            ],
                            "lengths": {
                                "integrity_string": len(integrity_string),
                                "final_hash": len(integrity),
                                "reference": len(reference)
                            },
                            "validations": {
                                "hash_format": all(c in '0123456789abcdef' for c in integrity),
                                "reference_format": reference.startswith("TEST-")
                            }
                        }
                    }
                }
            )

            return response_data.get("data") if success else None

        except Exception as e:
            print(f"\n❌ EXCEPCIÓN NO CONTROLADA")
            print("-"*50)
            print(f"Error: {str(e)}")
            print("\nStack trace:")
            import traceback
            print(traceback.format_exc())
            
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def verify_transaction(self, transaction_id: str) -> Dict:
        """Verifica el estado de una transacción"""
        test_name = "Verify Transaction"
        try:
            response = requests.get(
                f"{self.wompi_base_url}/transactions/{transaction_id}",
                headers={
                    'Authorization': f'Bearer {self.wompi_keys["private_key"]}'
                }
            )

            success = response.status_code == 200
            response_data = response.json()

            self._add_test_result(
                test_name,
                success,
                {
                    "status_code": response.status_code,
                    "response": response_data
                }
            )

            return response_data if success else None

        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def test_place_bet(self, lottery_data: dict) -> Dict:
        """Prueba realizar una apuesta"""
        test_name = "Place Bet"
        try:
            data = {
                "lottery": lottery_data['nombre_loteria'],  # Usamos el nombre en lugar del ID
                "number": "1234",
                "series": lottery_data['numero_serie'],
                "amount": 5000,
                "payment_type": "BALANCE",
                "draw_date": lottery_data['fecha']  # Incluimos la fecha del sorteo
            }

            response = requests.post(
                f"{self.base_url}/lottery/bets/",
                headers=self._get_headers(),
                json=data
            )

            success = response.status_code == 201
            response_data = response.json()

            self._add_test_result(
                test_name,
                success,
                {
                    "status_code": response.status_code,
                    "response": response_data
                }
            )

            return response_data if success else None

        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def get_acceptance_token(self) -> str:
        """Obtiene el token de aceptación de Wompi"""
        print("\n=== Obteniendo acceptance token ===")
        try:
            response = requests.get(
                f"{self.wompi_base_url}/merchants/{self.wompi_keys['public_key']}",
                headers={
                    'Authorization': f'Bearer {self.wompi_keys["public_key"]}'
                }
            )
            print(f"Status code: {response.status_code}")
            response_data = response.json()
            token = response_data.get('data', {}).get('presigned_acceptance', {}).get('acceptance_token')
            print(f"Token obtenido: {token[:30]}...")
            return token
        except Exception as e:
            print(f"❌ Error obteniendo acceptance token: {str(e)}")
            return None

    def run_all_tests(self):
        """Ejecuta todas las pruebas en secuencia"""
        print("Iniciando pruebas de integración completa...")

        # 1. Registro de usuario
        if not self.test_registration():
            print("❌ Error en registro de usuario")
            return self.results
        print("✅ Registro exitoso")

        # 2. Login
        if not self.test_login():
            print("❌ Error en login")
            return self.results
        print("✅ Login exitoso")

        # 3. Obtener loterías disponibles
        lotteries = self.test_get_available_lotteries()
        if not lotteries:
            print("❌ Error obteniendo loterías")
            return self.results
        print(f"✅ {len(lotteries)} loterías obtenidas")

        # 4. Realizar pago con tarjeta
        payment_result = self.test_card_payment()
        if not payment_result:
            print("❌ Error en pago")
            return self.results
        print("✅ Pago procesado")

        # 5. Realizar apuesta
        if lotteries:
            bet_result = self.test_place_bet(lotteries[0])
            if not bet_result:
                print("❌ Error en apuesta")
                return self.results
            print("✅ Apuesta realizada")

        return self.results


def main():
    # Configuración
    BASE_URL = "http://localhost:8000/api"
    WOMPI_KEYS = {
        "public_key": "pub_test_gm7Ldcm8Yjb7NDUcGb4qUtw8oc4amknZ",
        "private_key": "prv_test_CShsLexdDRid3YWHu9veCF5uWwmftTXm",
        "events_key": "test_events_cninvxlQ6psdViLH7UIZ92mm1ocPKnzL",
        "integrity_key": "test_integrity_ckeo8TwWVz22ciSYgkz41f4xMSfTTfx3"  # Agregado
    }
    LOTTERY_API_KEY = '47SFw0COzXcwePfecOUwWUXe9BrZhg'

    # Ejecutar pruebas
    tester = CompleteIntegrationTest(BASE_URL, WOMPI_KEYS, LOTTERY_API_KEY)
    results = tester.run_all_tests()

    # Guardar resultados
    with open('integration_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\n=== Resumen de Pruebas ===")
    print(f"Total de pruebas: {results['summary']['total']}")
    print(f"Pruebas exitosas: {results['summary']['passed']}")
    print(f"Pruebas fallidas: {results['summary']['failed']}")
    print("\nResultados detallados guardados en 'integration_test_results.json'")


if __name__ == "__main__":
    main()
