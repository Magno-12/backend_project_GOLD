import os
import django
from decimal import Decimal
from datetime import time

# Configure Django settings before any imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_GOLD.settings')
django.setup()

from apps.lottery.models.lottery import Lottery

def recreate_lotteries():
    """Script para recrear todas las loterías"""
    
    # Verificar si ya existen loterías
    existing_lotteries = Lottery.objects.all().count()
    if existing_lotteries > 0:
        print(f"Ya existen {existing_lotteries} loterías en la base de datos.")
        proceed = input("¿Desea continuar y crear nuevas loterías? (s/n): ")
        if proceed.lower() != 's':
            print("Operación cancelada.")
            return
    
    print("Creando loterías...")
    
    # Crear cada lotería con sus parámetros específicos
    lotteries = [
        {
            'name': 'Lotería de Bogotá',
            'code': 'BOGOTA',
            'draw_day': 'THURSDAY',
            'draw_time': time(22, 30),
            'fraction_count': 3,
            'fraction_price': Decimal('6000'),
            'major_prize_amount': Decimal('14000000000'),
            'min_bet_amount': Decimal('6000'),
            'max_bet_amount': Decimal('14000000000'),
            'max_fractions_per_bet': 3,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriadebogota.com/wp-content/uploads/2020/01/logo.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería de Boyacá',
            'code': 'BOYACA',
            'draw_day': 'SATURDAY',
            'draw_time': time(22, 30),
            'fraction_count': 4,
            'fraction_price': Decimal('5000'),
            'major_prize_amount': Decimal('15000000000'),
            'min_bet_amount': Decimal('5000'),
            'max_bet_amount': Decimal('15000000000'),
            'max_fractions_per_bet': 4,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriadeboyaca.gov.co/wp-content/uploads/2022/03/logo1.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería del Cauca',
            'code': 'CAUCA',
            'draw_day': 'SATURDAY',
            'draw_time': time(22, 30),
            'fraction_count': 4,
            'fraction_price': Decimal('4000'),
            'major_prize_amount': Decimal('8000000000'),
            'min_bet_amount': Decimal('4000'),
            'max_bet_amount': Decimal('8000000000'),
            'max_fractions_per_bet': 4,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriadelcauca.com.co/wp-content/uploads/2019/09/ldc-logo.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería de la Cruz Roja',
            'code': 'CRUZ_ROJA',
            'draw_day': 'TUESDAY',
            'draw_time': time(22, 30),
            'fraction_count': 3,
            'fraction_price': Decimal('5000'),
            'major_prize_amount': Decimal('7000000000'),
            'min_bet_amount': Decimal('5000'),
            'max_bet_amount': Decimal('7000000000'),
            'max_fractions_per_bet': 3,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.lotecruz.com.co/wp-content/uploads/2020/04/logo-loterias.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería de Cundinamarca',
            'code': 'CUNDINAMARCA',
            'draw_day': 'MONDAY',
            'draw_time': time(22, 30),
            'fraction_count': 3,
            'fraction_price': Decimal('5000'),
            'major_prize_amount': Decimal('6000000000'),
            'min_bet_amount': Decimal('5000'),
            'max_bet_amount': Decimal('6000000000'),
            'max_fractions_per_bet': 3,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriadecundinamarca.com.co/wp-content/uploads/2020/05/logo.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería del Huila',
            'code': 'HUILA',
            'draw_day': 'TUESDAY',
            'draw_time': time(22, 30),
            'fraction_count': 3,
            'fraction_price': Decimal('4000'),
            'major_prize_amount': Decimal('2000000000'),
            'min_bet_amount': Decimal('4000'),
            'max_bet_amount': Decimal('2000000000'),
            'max_fractions_per_bet': 3,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriadelhuila.com/images/logo-loteria-del-huila.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería de Risaralda',
            'code': 'RISARALDA',
            'draw_day': 'FRIDAY',
            'draw_time': time(22, 30),
            'fraction_count': 3,
            'fraction_price': Decimal('3000'),
            'major_prize_amount': Decimal('1400000000'),
            'min_bet_amount': Decimal('3000'),
            'max_bet_amount': Decimal('1400000000'),
            'max_fractions_per_bet': 3,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriaderisaralda.com/images/logos/logo-loteria-de-risaralda.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería de Manizales',
            'code': 'MANIZALES',
            'draw_day': 'WEDNESDAY',
            'draw_time': time(22, 30),
            'fraction_count': 5,
            'fraction_price': Decimal('2000'),
            'major_prize_amount': Decimal('2200000000'),
            'min_bet_amount': Decimal('2000'),
            'max_bet_amount': Decimal('2200000000'),
            'max_fractions_per_bet': 5,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriademanizales.com/wp-content/uploads/2020/01/logo.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería de Medellín',
            'code': 'MEDELLIN',
            'draw_day': 'FRIDAY',
            'draw_time': time(22, 30),
            'fraction_count': 3,
            'fraction_price': Decimal('7000'),
            'major_prize_amount': Decimal('15000000000'),
            'min_bet_amount': Decimal('7000'),
            'max_bet_amount': Decimal('15000000000'),
            'max_fractions_per_bet': 3,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriademedellin.com.co/sites/loteriademedellin/files/logo-footer.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería del Meta',
            'code': 'META',
            'draw_day': 'WEDNESDAY',
            'draw_time': time(22, 30),
            'fraction_count': 3,
            'fraction_price': Decimal('3000'),
            'major_prize_amount': Decimal('1500000000'),
            'min_bet_amount': Decimal('3000'),
            'max_bet_amount': Decimal('1500000000'),
            'max_fractions_per_bet': 3,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriadelmeta.gov.co/media/logo.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería del Quindío',
            'code': 'QUINDIO',
            'draw_day': 'THURSDAY',
            'draw_time': time(22, 30),
            'fraction_count': 5,
            'fraction_price': Decimal('2000'),
            'major_prize_amount': Decimal('1800000000'),
            'min_bet_amount': Decimal('2000'),
            'max_bet_amount': Decimal('1800000000'),
            'max_fractions_per_bet': 5,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriaquindio.com.co/wp-content/uploads/2020/02/logo.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería de Santander',
            'code': 'SANTANDER',
            'draw_day': 'FRIDAY',
            'draw_time': time(22, 30),
            'fraction_count': 3,
            'fraction_price': Decimal('6000'),
            'major_prize_amount': Decimal('10000000000'),
            'min_bet_amount': Decimal('6000'),
            'max_bet_amount': Decimal('10000000000'),
            'max_fractions_per_bet': 3,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriasantander.gov.co/wp-content/uploads/2020/03/logo.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería del Tolima',
            'code': 'TOLIMA',
            'draw_day': 'MONDAY',
            'draw_time': time(22, 30),
            'fraction_count': 3,
            'fraction_price': Decimal('4000'),
            'major_prize_amount': Decimal('3000000000'),
            'min_bet_amount': Decimal('4000'),
            'max_bet_amount': Decimal('3000000000'),
            'max_fractions_per_bet': 3,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriadeltolima.com/wp-content/uploads/2019/09/logo.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Lotería del Valle',
            'code': 'VALLE',
            'draw_day': 'WEDNESDAY',
            'draw_time': time(22, 30),
            'fraction_count': 3,
            'fraction_price': Decimal('5000'),
            'major_prize_amount': Decimal('6000000000'),
            'min_bet_amount': Decimal('5000'),
            'max_bet_amount': Decimal('6000000000'),
            'max_fractions_per_bet': 3,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.loteriadelvalle.com/wp-content/uploads/2020/02/logo.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        },
        {
            'name': 'Sorteo Extraordinario de Colombia',
            'code': 'EXTRA',
            'draw_day': 'SATURDAY',
            'draw_time': time(22, 30),
            'fraction_count': 1,
            'fraction_price': Decimal('16000'),
            'major_prize_amount': Decimal('12000000000'),
            'min_bet_amount': Decimal('16000'),
            'max_bet_amount': Decimal('12000000000'),
            'max_fractions_per_bet': 1,
            'number_range_start': '0000',
            'number_range_end': '9999',
            'logo_url': 'https://www.extradecolombia.com.co/wp-content/uploads/2021/01/logo.png',
            'available_series': ['000', '001', '002', '003', '004', '005']
        }
    ]
    
    created_count = 0
    for lottery_data in lotteries:
        try:
            Lottery.objects.create(
                name=lottery_data['name'],
                code=lottery_data['code'],
                draw_day=lottery_data['draw_day'],
                draw_time=lottery_data['draw_time'],
                fraction_count=lottery_data['fraction_count'],
                fraction_price=lottery_data['fraction_price'],
                major_prize_amount=lottery_data['major_prize_amount'],
                min_bet_amount=lottery_data['min_bet_amount'],
                max_bet_amount=lottery_data['max_bet_amount'],
                max_fractions_per_bet=lottery_data['max_fractions_per_bet'],
                number_range_start=lottery_data['number_range_start'],
                number_range_end=lottery_data['number_range_end'],
                logo_url=lottery_data['logo_url'],
                available_series=lottery_data['available_series'],
                is_active=True,
                requires_series=True,
                allow_duplicate_numbers=False
            )
            created_count += 1
            print(f"Creada: {lottery_data['name']}")
        except Exception as e:
            print(f"Error creando {lottery_data['name']}: {str(e)}")
    
    print(f"\nSe crearon {created_count} loterías exitosamente")

if __name__ == "__main__":
    print("Iniciando creación de loterías...")
    recreate_lotteries()