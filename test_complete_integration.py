import requests
import json
import uuid
import hashlib
import traceback
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

class CompleteIntegrationTest:
    def __init__(self, base_url: str, wompi_keys: Dict[str, str], lottery_api_key: str):
        self.base_url = base_url
        self.wompi_base_url = "https://sandbox.wompi.co/v1"
        self.wompi_keys = wompi_keys
        self.lottery_api_key = lottery_api_key
        self.access_token = None
        self.user_data = None
        self.user_id = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {"total": 0, "passed": 0, "failed": 0}
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
        headers = {'Content-Type': 'application/json'}
        if with_auth and self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        return headers

    def test_registration(self) -> bool:
        test_name = "User Registration"
        try:
            data = {
                "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
                "phone_number": f"+57{str(random.randint(3000000000, 3999999999))}",
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
            response_data = response.json()
            if success:
                self.user_data = data
                self.user_id = response_data.get('id')
            self._add_test_result(test_name, success, {
                "status_code": response.status_code,
                "response": response_data
            })
            return success
        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return False

    def test_login(self) -> bool:
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
            self._add_test_result(test_name, success, {
                "status_code": response.status_code,
                "response": response_data
            })
            return success
        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return False

    def test_get_profile(self) -> Dict:
        test_name = "Get Profile"
        try:
            response = requests.get(
                f"{self.base_url}/users/{self.user_id}/profile/",
                headers=self._get_headers()
            )
            success = response.status_code == 200
            response_data = response.json()
            self._add_test_result(test_name, success, {
                "status_code": response.status_code,
                "response": response_data
            })
            return response_data if success else None
        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def test_get_available_lotteries(self) -> List[Dict]:
        test_name = "Get Available Lotteries"
        try:
            response = requests.get(
                "https://lottery-results-api.onrender.com/results",
                headers={**self._get_headers(), 'x-api-key': self.lottery_api_key}
            )
            success = response.status_code == 200
            response_data = response.json()
            self._add_test_result(test_name, success, {
                "status_code": response.status_code,
                "response": response_data
            })
            return response_data if success and isinstance(response_data, list) else []
        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return []

    def test_transaction_history(self) -> Dict:
        test_name = "Transaction History"
        try:
            response = requests.get(
                f"{self.base_url}/payment/history/",
                headers=self._get_headers()
            )
            try:
                response_data = response.json() 
                success = response.status_code == 200
            except json.JSONDecodeError:
                print(f"Respuesta no JSON: {response.text}")
                success = False
                response_data = {"error": "Invalid JSON response"}
            
            self._add_test_result(test_name, success, {
                "status_code": response.status_code, 
                "response": response_data
            })
            return response_data if success else None
        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def test_place_bet(self, lottery_data: dict) -> Dict:
        test_name = "Place Bet"
        try:
            balance_response = requests.get(
                f"{self.base_url}/payment/balance/",
                headers=self._get_headers()
            )
            print(f"Saldo inicial: {balance_response.json() if balance_response.status_code == 200 else 'Error'}")
            
            if balance_response.status_code == 200:
                balance = float(balance_response.json().get('balance', '0'))
                if balance < 5000:
                    print(f"Saldo insuficiente ({balance}). Realizando recarga...")
                    payment = self.test_card_payment()
                    
                    if payment and payment.get('id'):
                        time.sleep(10)
                        transaction = self.verify_transaction(payment['id'])
                        if transaction and transaction.get('data', {}).get('status') == 'APPROVED':
                            time.sleep(5)
                            balance_response = requests.get(
                                f"{self.base_url}/payment/balance/",
                                headers=self._get_headers()
                            )
                            if balance_response.status_code == 200:
                                new_balance = float(balance_response.json().get('balance', '0'))
                                print(f"Nuevo saldo después de recarga: {new_balance}")
                                if new_balance < 5000:
                                    print("No se pudo recargar el saldo suficiente")
                                    return None
                        else:
                            print("El pago no fue aprobado")
                            return None
                    else:
                        print("Error realizando el pago")
                        return None

            data = {
                "lottery": lottery_data['nombre_loteria'],
                "number": "1234",
                "series": lottery_data['numero_serie'],
                "amount": 5000,
                "payment_type": "BALANCE",
                "draw_date": lottery_data['fecha']
            }
            print(f"Intentando realizar apuesta: {json.dumps(data, indent=2)}")
            
            response = requests.post(
                f"{self.base_url}/lottery/bets/",
                headers=self._get_headers(),
                json=data
            )
            print(f"Respuesta apuesta - Status: {response.status_code}")
            if response.status_code != 201:
                print(f"Error en apuesta: {response.text}")

            success = response.status_code == 201
            response_data = response.json()
            self._add_test_result(test_name, success, {
                "status_code": response.status_code,
                "response": response_data
            })
            return response_data if success else None
        except Exception as e:
            print(f"Error en apuesta: {str(e)}")
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def get_acceptance_token(self) -> Optional[str]:
        try:
            response = requests.get(
                f"{self.wompi_base_url}/merchants/{self.wompi_keys['public_key']}",
                headers={'Authorization': f'Bearer {self.wompi_keys["public_key"]}'}
            )
            response_data = response.json()
            return response_data.get('data', {}).get('presigned_acceptance', {}).get('acceptance_token')
        except Exception as e:
            print(f"❌ Error obteniendo acceptance token: {str(e)}")
            return None

    def generate_integrity_signature(self, reference: str, amount_in_cents: int) -> str:
        integrity_string = f"{reference}{amount_in_cents}COP{self.wompi_keys['integrity_key']}"
        m = hashlib.sha256()
        m.update(integrity_string.encode())
        return m.hexdigest()

    def test_card_payment(self) -> Dict:
        card_token = self.tokenize_test_card()
        if not card_token:
            return None
        transaction = self.create_card_transaction(card_token)
        if not transaction:
            return None
        return self.verify_transaction(transaction.get("id"))

    def test_nequi_payment(self) -> Dict:
        test_name = "Nequi Payment"
        try:
            phone = ''.join(filter(str.isdigit, self.user_data["phone_number"]))[-10:]
            reference = f"TEST-{uuid.uuid4().hex[:8]}"
            amount_in_cents = 5000000

            data = {
                "amount_in_cents": amount_in_cents,
                "currency": "COP",
                "customer_email": self.user_data["email"],
                "reference": reference,
                "payment_method": {
                    "type": "NEQUI",
                    "phone_number": phone,
                    "payment_description": "Test payment"
                },
                "customer_data": {
                    "phone_number": phone,
                    "full_name": f"{self.user_data['first_name']} {self.user_data['last_name']}"
                },
                "acceptance_token": self.get_acceptance_token(),
                "signature": self.generate_integrity_signature(reference, amount_in_cents)
            }
            print(f"Datos Nequi: {json.dumps(data, indent=2)}")
            
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
            print(f"Respuesta Nequi: {response.status_code}")
            print(f"Datos respuesta: {response_data}")
            
            self._add_test_result(test_name, success, {
                "status_code": response.status_code,
                "response": response_data
            })
            return response_data.get('data') if success else None
        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def test_pse_payment(self) -> Dict:
        test_name = "PSE Payment"
        try:
            reference = f"TEST-{uuid.uuid4().hex[:8]}"
            amount_in_cents = 5000000

            data = {
                "amount_in_cents": amount_in_cents,
                "currency": "COP",
                "customer_email": self.user_data["email"],
                "reference": reference,
                "payment_method": {
                    "type": "PSE",
                    "user_type": 0,
                    "user_legal_id_type": "CC",
                    "user_legal_id": self.user_data["identification"].replace('CC', ''),
                    "financial_institution_code": "1007",
                    "payment_description": "Test PSE payment"
                },
                "acceptance_token": self.get_acceptance_token(),
                "signature": self.generate_integrity_signature(reference, amount_in_cents)
            }

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
            
            self._add_test_result(test_name, success, {
                "status_code": response.status_code,
                "response": response_data
            })
            return response_data.get('data') if success else None
        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def test_bancolombia_transfer(self) -> Dict:
        test_name = "Bancolombia Transfer"
        try:
            reference = f"TEST-{uuid.uuid4().hex[:8]}"
            amount_in_cents = 5000000

            data = {
                "amount_in_cents": amount_in_cents,
                "currency": "COP",
                "customer_email": self.user_data["email"],
                "reference": reference,
                "payment_method": {
                    "type": "BANCOLOMBIA_TRANSFER",
                    "user_type": "PERSON",
                    "payment_description": "Test Bancolombia transfer"
                },
                "acceptance_token": self.get_acceptance_token(),
                "signature": self.generate_integrity_signature(reference, amount_in_cents)
            }

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
            
            self._add_test_result(test_name, success, {
                "status_code": response.status_code,
                "response": response_data
            })
            return response_data.get('data') if success else None
        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def test_check_balance(self) -> Dict:
       test_name = "Check Balance"
       try:
           response = requests.get(
               f"{self.base_url}/payment/balance/",
               headers=self._get_headers()
           )
           success = response.status_code == 200
           response_data = response.json()
           self._add_test_result(test_name, success, {
               "status_code": response.status_code,
               "response": response_data
           })
           return response_data if success else None
       except Exception as e:
           self._add_test_result(test_name, False, {"error": str(e)})
           return None

    def tokenize_test_card(self) -> str:
        test_name = "Card Tokenization"
        try:
            response = requests.post(
                f"{self.wompi_base_url}/tokens/cards",
                headers={'Authorization': f'Bearer {self.wompi_keys["public_key"]}'},
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
            self._add_test_result(test_name, success, {
                "status_code": response.status_code,
                "response": response_data
            })
            return response_data.get("data", {}).get("id") if success else None
        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def create_card_transaction(self, card_token: str) -> Dict:
        test_name = "Create Card Transaction"
        try:
            reference = f"TEST-{uuid.uuid4().hex[:8]}"
            amount_in_cents = 5000000
            data = {
                "amount_in_cents": amount_in_cents,
                "currency": "COP",
                "customer_email": self.user_data["email"],
                "reference": reference,
                "payment_method": {
                    "type": "CARD",
                    "token": card_token,
                    "installments": 1
                },
                "acceptance_token": self.get_acceptance_token(),
                "signature": self.generate_integrity_signature(reference, amount_in_cents)
            }
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
            self._add_test_result(test_name, success, {
                "status_code": response.status_code,
                "response": response_data
            })
            return response_data.get("data") if success else None
        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def verify_transaction(self, transaction_id: str) -> Dict:
        test_name = "Verify Transaction"
        try:
            response = requests.get(
                f"{self.wompi_base_url}/transactions/{transaction_id}",
                headers={'Authorization': f'Bearer {self.wompi_keys["private_key"]}'}
            )
            success = response.status_code == 200
            response_data = response.json()
            self._add_test_result(test_name, success, {
                "status_code": response.status_code,
                "response": response_data
            })
            return response_data if success else None
        except Exception as e:
            self._add_test_result(test_name, False, {"error": str(e)})
            return None

    def run_all_tests(self):
        print("\n=== Iniciando Pruebas de Integración Completas ===\n")

        # 1. Registro y Login
        if not self.test_registration():
            print("❌ Error en registro de usuario")
            return self.results
        print("✅ Registro exitoso")

        if not self.test_login():
            print("❌ Error en login")
            return self.results
        print("✅ Login exitoso")

        # 2. Verificación inicial
        print("\n=== Verificación Inicial ===")
        profile = self.test_get_profile()
        if not profile:
            print("❌ Error obteniendo perfil")
            return self.results
        print("✅ Perfil verificado")

        initial_balance = self.test_check_balance()
        if not initial_balance:
            print("❌ Error verificando saldo inicial")
            return self.results
        print("✅ Saldo inicial verificado")

        # 3. Pruebas de Pagos
        print("\n=== Pruebas de Métodos de Pago ===")
        print("\nPrueba de pago con tarjeta:")
        card_payment = self.test_card_payment()
        if not card_payment:
            print("❌ Error en pago con tarjeta")
        else:
            print("✅ Pago con tarjeta exitoso")

        print("\nPrueba de pago con Nequi:")
        nequi_payment = self.test_nequi_payment()
        if not nequi_payment:
            print("❌ Error en pago con Nequi")
        else:
            print("✅ Pago con Nequi exitoso")

        print("\nPrueba de pago con PSE:")
        pse_payment = self.test_pse_payment()
        if not pse_payment:
            print("❌ Error en pago con PSE")
        else:
            print("✅ Pago con PSE exitoso")

        print("\nPrueba de transferencia Bancolombia:")
        bancolombia_payment = self.test_bancolombia_transfer()
        if not bancolombia_payment:
            print("❌ Error en transferencia Bancolombia")
        else:
            print("✅ Transferencia Bancolombia exitosa")

        # 4. Verificación de saldo y transacciones
        print("\n=== Verificación de Transacciones y Saldo ===")
        updated_balance = self.test_check_balance()
        if not updated_balance:
            print("❌ Error verificando saldo actualizado")
        else:
            print("✅ Saldo actualizado verificado")

        history = self.test_transaction_history()
        if not history:
            print("❌ Error obteniendo historial")
        else:
            print("✅ Historial de transacciones verificado")

        # 5. Pruebas de Lotería
        print("\n=== Pruebas de Lotería ===")
        lotteries = self.test_get_available_lotteries()
        if not lotteries:
            print("❌ Error obteniendo loterías")
            return self.results
        print(f"✅ {len(lotteries)} loterías obtenidas")

        if lotteries:
            print("\nRealizando apuesta de prueba:")
            bet_result = self.test_place_bet(lotteries[0])
            if not bet_result:
                print("❌ Error en apuesta")
            else:
                print("✅ Apuesta realizada exitosamente")

        # 6. Verificación final
        print("\n=== Verificación Final ===")
        final_profile = self.test_get_profile()
        if not final_profile:
            print("❌ Error en verificación final")
        else:
            print("✅ Verificación final completada")

        print("\n=== Resumen de Pruebas ===")
        print(f"Total de pruebas: {self.results['summary']['total']}")
        print(f"Pruebas exitosas: {self.results['summary']['passed']}")
        print(f"Pruebas fallidas: {self.results['summary']['failed']}")

        return self.results


def main():
    BASE_URL = "http://localhost:8000/api"
    WOMPI_KEYS = {
        "public_key": "pub_test_gm7Ldcm8Yjb7NDUcGb4qUtw8oc4amknZ",
        "private_key": "prv_test_CShsLexdDRid3YWHu9veCF5uWwmftTXm",
        "events_key": "test_events_cninvxlQ6psdViLH7UIZ92mm1ocPKnzL",
        "integrity_key": "test_integrity_ckeo8TwWVz22ciSYgkz41f4xMSfTTfx3"
    }
    LOTTERY_API_KEY = '47SFw0COzXcwePfecOUwWUXe9BrZhg'

    tester = CompleteIntegrationTest(BASE_URL, WOMPI_KEYS, LOTTERY_API_KEY)
    results = tester.run_all_tests()

    filename = f'integration_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResultados detallados guardados en '{filename}'")


if __name__ == "__main__":
   main()
