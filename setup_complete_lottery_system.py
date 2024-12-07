import os
from decimal import Decimal
from datetime import datetime, time

from django.db import transaction
from django.core.management.base import BaseCommand
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.lottery.models.lottery import Lottery
from apps.lottery.models.prize import Prize
from apps.lottery.models.prize_plan import PrizePlan
from apps.lottery.models.prize_type import PrizeType


class Command(BaseCommand):
    help = 'Configura el sistema completo de loterías con todos sus planes de premios'

    def handle(self, *args, **options):
        try:
            self.stdout.write("Iniciando configuración del sistema de loterías...")
            with transaction.atomic():
                success = setup_complete_lottery_system()
            self.stdout.write(self.style.SUCCESS('Sistema de loterías configurado exitosamente'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))


def setup_complete_lottery_system():
    """Script principal de configuración del sistema completo de loterías"""
    cleanup_existing_data()
    prize_types = create_base_prize_types()
    
    # Configurar cada lotería con su plan de premios completo
    configurar_bogota(prize_types)
    configurar_boyaca(prize_types)
    configurar_cauca(prize_types)
    configurar_cruz_roja(prize_types)
    configurar_cundinamarca(prize_types)
    configurar_huila(prize_types)
    configurar_risaralda(prize_types)
    configurar_manizales(prize_types)
    configurar_medellin(prize_types)
    configurar_meta(prize_types)
    configurar_quindio(prize_types)
    configurar_santander(prize_types)
    configurar_tolima(prize_types)
    configurar_valle(prize_types)
    configurar_extra_colombia(prize_types)
    
    return True


def cleanup_existing_data():
    """Limpia todos los datos existentes del sistema"""
    print("Limpiando datos existentes...")
    PrizeType.objects.all().delete()
    Lottery.objects.all().delete()
    PrizePlan.objects.all().delete()
    Prize.objects.all().delete()


def create_base_prize_types():
    """Crea y retorna diccionario con todos los tipos de premios necesarios"""
    print("Creando tipos de premios base...")
    types = {
        'MAJOR': PrizeType.objects.create(
            name='Premio Mayor',
            code='MAJOR',
            requires_series=True,
            requires_exact_match=True,
            match_rules={'type': 'exact', 'positions': 'all'},
            description='Premio principal de la lotería'
        ),
        'SECO': PrizeType.objects.create(
            name='Premio Seco',
            code='SECO',
            requires_series=True,
            requires_exact_match=True,
            description='Premio fijo garantizado'
        ),
        'SPECIAL': PrizeType.objects.create(
            name='Premio Especial',
            code='SPECIAL',
            requires_series=True,
            is_special=True,
            description='Premio con características especiales'
        ),
        'APPROX_SAME_SERIES': PrizeType.objects.create(
            name='Aproximación Misma Serie',
            code='APPROX_SAME_SERIES',
            requires_series=True,
            description='Aproximación en la misma serie del premio mayor'
        ),
        'APPROX_DIFF_SERIES': PrizeType.objects.create(
            name='Aproximación Diferente Serie',
            code='APPROX_DIFF_SERIES',
            requires_series=False,
            description='Aproximación en diferente serie del premio mayor'
        ),
        'FIRST_THREE': PrizeType.objects.create(
            name='Tres Primeras',
            code='FIRST_THREE',
            match_rules={'positions': [0,1,2]},
            description='Coincidencia en las tres primeras cifras'
        ),
        'LAST_THREE': PrizeType.objects.create(
            name='Tres Últimas',
            code='LAST_THREE',
            match_rules={'positions': [-3,-2,-1]},
            description='Coincidencia en las tres últimas cifras'
        ),
        'FIRST_TWO': PrizeType.objects.create(
            name='Dos Primeras',
            code='FIRST_TWO',
            match_rules={'positions': [0,1]},
            description='Coincidencia en las dos primeras cifras'
        ),
        'LAST_TWO': PrizeType.objects.create(
            name='Dos Últimas',
            code='LAST_TWO',
            match_rules={'positions': [-2,-1]},
            description='Coincidencia en las dos últimas cifras'
        ),
        'FIRST_TWO_LAST': PrizeType.objects.create(
            name='Dos Primeras y Última',
            code='FIRST_TWO_LAST',
            match_rules={'positions': [0,1,-1]},
            description='Coincidencia en las dos primeras y última cifra'
        ),
        'FIRST_LAST_TWO': PrizeType.objects.create(
            name='Primera y Dos Últimas',
            code='FIRST_LAST_TWO',
            match_rules={'positions': [0,-2,-1]},
            description='Coincidencia en la primera y las dos últimas cifras'
        ),
        'TWO_CENTER': PrizeType.objects.create(
            name='Dos del Centro',
            code='TWO_CENTER',
            match_rules={'positions': [1,2]},
            description='Coincidencia en las dos cifras centrales'
        ),
        'LAST_DIGIT': PrizeType.objects.create(
            name='Última Cifra',
            code='LAST_DIGIT',
            match_rules={'positions': [-1]},
            description='Coincidencia en la última cifra'
        ),
        'SERIES': PrizeType.objects.create(
            name='Serie',
            code='SERIES',
            requires_series=True,
            description='Premio por coincidencia en la serie'
        ),
        'INVERTED': PrizeType.objects.create(
            name='Mayor Invertido',
            code='INVERTED',
            requires_series=True,
            description='Premio por coincidencia con el número mayor invertido'
        ),
        'COMBINADO': PrizeType.objects.create(
            name='Combinado',
            code='COMBINADO',
            requires_series=True,
            description='Premio por coincidencia en cualquier orden'
        ),
        'ANTERIOR': PrizeType.objects.create(
            name='Número Anterior',
            code='ANTERIOR',
            requires_series=True,
            description='Premio al número anterior del mayor'
        ),
        'POSTERIOR': PrizeType.objects.create(
            name='Número Posterior',
            code='POSTERIOR',
            requires_series=True,
            description='Premio al número posterior del mayor'
        )
    }
    
    return types

def configurar_bogota(prize_types):
    """Configura Lotería de Bogotá con plan de premios completo"""
    print("Configurando Lotería de Bogotá...")
    
    # Crear lotería
    bogota = Lottery.objects.create(
        name='Lotería de Bogotá',
        code='BOGOTA',
        draw_day='THURSDAY',
        draw_time=time(22, 30),
        fraction_count=3,
        fraction_price=Decimal('6000'),
        major_prize_amount=Decimal('14000000000'),
        min_bet_amount=Decimal('6000'),
        max_bet_amount=Decimal('14000000000'),
        is_active=True
    )

    # Crear plan de premios
    bogota_plan = PrizePlan.objects.create(
        lottery=bogota,
        name='Plan de Premios 2023-2024',
        start_date='2023-12-14',
        sorteo_number='2720',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=bogota_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('14000000000'),
        fraction_amount=Decimal('3098666667'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_bogota = [
        ('Mega Gordo', Decimal('500000000'), Decimal('110666667'), 1),
        ('Super Gordo', Decimal('250000000'), Decimal('55333333'), 1),
        ('Premios millonarios', Decimal('50000000'), Decimal('11066667'), 5),
        ('Premios millonarios', Decimal('20000000'), Decimal('4426667'), 8),
        ('Premios millonarios', Decimal('10000000'), Decimal('2213333'), 10),
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_bogota, 2):
        Prize.objects.create(
            prize_plan=bogota_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximaciones diferente serie
    aprox_diff_serie_bogota = [
        ('Mayor diferente serie', Decimal('8674800'), 449),
        ('Secos diferente serie', Decimal('21687'), 11225),
        ('Tres primeras', Decimal('65060'), 4041),
        ('Tres últimas', Decimal('65060'), 4041),
        ('Dos primeras', Decimal('43373'), 40410),
        ('Dos últimas', Decimal('43373'), 40410),
        ('Última', Decimal('21687'), 400059)
    ]

    for name, amount, qty in aprox_diff_serie_bogota:
        Prize.objects.create(
            prize_plan=bogota_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

    # Aproximaciones misma serie
    aprox_misma_serie_bogota = [
        ('Tres primeras', Decimal('10843500'), 9),
        ('Tres últimas', Decimal('10843500'), 9),
        ('Dos primeras', Decimal('1301220'), 90),
        ('Dos últimas', Decimal('1301220'), 90),
        ('Última', Decimal('65060'), 891),
        ('Serie Mayor', Decimal('21687'), 8910)
    ]

    for name, amount, qty in aprox_misma_serie_bogota:
        Prize.objects.create(
            prize_plan=bogota_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

def configurar_boyaca(prize_types):
    """Configura Lotería de Boyacá con plan de premios completo"""
    print("Configurando Lotería de Boyacá...")
    
    boyaca = Lottery.objects.create(
        name='Lotería de Boyacá',
        code='BOYACA',
        draw_day='SATURDAY',
        draw_time=time(22, 30),
        fraction_count=4,
        fraction_price=Decimal('5000'),
        major_prize_amount=Decimal('15000000000'),
        min_bet_amount=Decimal('5000'),
        max_bet_amount=Decimal('15000000000'),
        is_active=True
    )

    boyaca_plan = PrizePlan.objects.create(
        lottery=boyaca,
        name='Plan de Premios 2024',
        start_date='2024-04-06',
        sorteo_number='4514',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=boyaca_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('15000000000'),
        fraction_amount=Decimal('2490000000'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_boyaca = [
        ('Premio Fortuna', Decimal('1000000000'), Decimal('166000000'), 1),
        ('Premio Alegría', Decimal('400000000'), Decimal('66400000'), 1),
        ('Premio Ilusión', Decimal('300000000'), Decimal('49800000'), 1),
        ('Premio Esperanza', Decimal('100000000'), Decimal('16600000'), 1),
        ('Premio Berraquera', Decimal('50000000'), Decimal('8300000'), 4),
        ('Premio Optimismo', Decimal('20000000'), Decimal('3320000'), 15),
        ('Premio Valentía', Decimal('10000000'), Decimal('2075000'), 36)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_boyaca, 2):
        Prize.objects.create(
            prize_plan=boyaca_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximaciones diferente serie
    aprox_diff_serie_boyaca = [
        ('Mayor en diferente serie', Decimal('4000000'), 469),
        ('Tres primeras', Decimal('72289'), 4221),
        ('Tres últimas', Decimal('72289'), 4221),
        ('Dos primeras', Decimal('48193'), 42210),
        ('Dos últimas', Decimal('48193'), 42210),
        ('Última', Decimal('24096'), 417879)
    ]

    for name, amount, qty in aprox_diff_serie_boyaca:
        Prize.objects.create(
            prize_plan=boyaca_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/4,
            quantity=qty
        )

    # Aproximaciones con serie
    aprox_serie_boyaca = [
        ('Tres primeras', Decimal('20000000'), 9),
        ('Tres últimas', Decimal('20000000'), 9),
        ('Dos primeras', Decimal('8000000'), 90),
        ('Dos últimas', Decimal('8000000'), 90),
        ('Última', Decimal('712074'), 891),
        ('Serie del premio mayor', Decimal('24096'), 8910)
    ]

    for name, amount, qty in aprox_serie_boyaca:
        Prize.objects.create(
            prize_plan=boyaca_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/4,
            quantity=qty
        )

    # Secos en diferente serie
    Prize.objects.create(
        prize_plan=boyaca_plan,
        prize_type=prize_types['APPROX_DIFF_SERIES'],
        name='Secos en el mismo orden en diferente serie',
        amount=Decimal('24096'),
        fraction_amount=Decimal('5000'),
        quantity=27671
    )

def configurar_cauca(prize_types):
    """Configura Lotería del Cauca con plan de premios completo"""
    print("Configurando Lotería del Cauca...")
    
    cauca = Lottery.objects.create(
        name='Lotería del Cauca',
        code='CAUCA',
        draw_day='SATURDAY',
        draw_time=time(22, 30),
        fraction_count=4,
        fraction_price=Decimal('4000'),
        major_prize_amount=Decimal('5555000000'),
        min_bet_amount=Decimal('4000'),
        max_bet_amount=Decimal('5555000000'),
        is_active=True
    )

    cauca_plan = PrizePlan.objects.create(
        lottery=cauca,
        name='Plan de Premios 2023',
        start_date='2023-07-08',
        sorteo_number='2462',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=cauca_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('5555000000'),
        fraction_amount=Decimal('922130000'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_cauca = [
        ('Primer seco', Decimal('200000000'), Decimal('33200000'), 1),
        ('Segundo seco', Decimal('100000000'), Decimal('16600000'), 1),
        ('Tercer seco', Decimal('100000000'), Decimal('16600000'), 1),
        ('Cuarto seco', Decimal('50000000'), Decimal('8300000'), 1),
        ('Quinto seco', Decimal('50000000'), Decimal('8300000'), 1),
        ('Sexto seco', Decimal('50000000'), Decimal('8300000'), 1),
        ('Secos 10 millones', Decimal('10000000'), Decimal('1660000'), 27)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_cauca, 2):
        Prize.objects.create(
            prize_plan=cauca_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximación al mayor con serie
    aprox_serie_cauca = [
        ('En cualquier orden', Decimal('3313253'), 23),
        ('Serie', Decimal('19277'), 8893),
        ('Última', Decimal('38554'), 887),
        ('Dos últimas', Decimal('361446'), 80),
        ('Dos primeras', Decimal('361446'), 80),
        ('Tres primeras', Decimal('7228916'), 9),
        ('Tres últimas', Decimal('7228916'), 9),
        ('Primera y dos últimas', Decimal('7228916'), 9),
        ('Dos primeras y última', Decimal('7228916'), 9)
    ]

    for name, amount, qty in aprox_serie_cauca:
        Prize.objects.create(
            prize_plan=cauca_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/4,
            quantity=qty
        )

    # Aproximaciones al mayor diferente
    aprox_diff_cauca = [
        ('Última cifra', Decimal('19277'), 195129),
        ('Dos últimas', Decimal('28916'), 17739),
        ('Dos primeras', Decimal('28916'), 17739),
        ('Tres primeras', Decimal('57831'), 1971),
        ('Tres últimas', Decimal('57831'), 1971),
        ('Dos primeras y última', Decimal('57831'), 1971),
        ('Primeras y dos últimas', Decimal('57831'), 1971),
        ('Cuatro cifras', Decimal('7228916'), 219),
        ('Secos en diferente serie', Decimal('38554'), 7227)
    ]

    for name, amount, qty in aprox_diff_cauca:
        Prize.objects.create(
            prize_plan=cauca_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/4,
            quantity=qty
        )

def configurar_cruz_roja(prize_types):
    """Configura Lotería de la Cruz Roja con plan de premios completo"""
    print("Configurando Lotería de la Cruz Roja...")
    
    cruz_roja = Lottery.objects.create(
        name='Lotería de la Cruz Roja',
        code='CRUZ_ROJA',
        draw_day='TUESDAY',
        draw_time=time(22, 30),
        fraction_count=3,
        fraction_price=Decimal('5000'),
        major_prize_amount=Decimal('7000000000'),
        min_bet_amount=Decimal('5000'),
        max_bet_amount=Decimal('7000000000'),
        is_active=True
    )

    cruz_roja_plan = PrizePlan.objects.create(
        lottery=cruz_roja,
        name='Plan de Premios 2024',
        start_date='2024-08-27',
        sorteo_number='3064',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=cruz_roja_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('7000000000'),
        fraction_amount=Decimal('4648000000'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_cruz_roja = [
        ('Seco', Decimal('200000000'), Decimal('132800000'), 1),
        ('Secos', Decimal('400000000'), Decimal('66400000'), 4),
        ('Secos', Decimal('300000000'), Decimal('19920000'), 10),
        ('Secos', Decimal('300000000'), Decimal('13280000'), 15),
        ('Secos', Decimal('200000000'), Decimal('6640000'), 20)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_cruz_roja, 2):
        Prize.objects.create(
            prize_plan=cruz_roja_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximaciones al mayor en la misma serie
    aprox_serie_cruz_roja = [
        ('Tres primeras', Decimal('8000000'), 9),
        ('Dos primeras y última', Decimal('8000000'), 9),
        ('Tres últimas', Decimal('8000000'), 9),
        ('Dos primeras', Decimal('1445783'), 81),
        ('Dos últimas', Decimal('1445783'), 90),
        ('Última', Decimal('144578'), 891)
    ]

    for name, amount, qty in aprox_serie_cruz_roja:
        Prize.objects.create(
            prize_plan=cruz_roja_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

    # Aproximaciones al mayor en diferente serie
    aprox_diff_cruz_roja = [
        ('Mayor diferente serie', Decimal('4066265'), 289),
        ('Tres primeras', Decimal('72289'), 2601),
        ('Tres últimas', Decimal('72289'), 2601),
        ('Dos primeras', Decimal('36145'), 23409),
        ('Dos últimas', Decimal('36145'), 26010),
        ('Última', Decimal('18072'), 257499),
        ('Seco', Decimal('18072'), 14450)
    ]

    for name, amount, qty in aprox_diff_cruz_roja:
        Prize.objects.create(
            prize_plan=cruz_roja_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

    # Aproximación a los secos en diferente serie
    Prize.objects.create(
        prize_plan=cruz_roja_plan,
        prize_type=prize_types['APPROX_DIFF_SERIES'],
        name='Secos diferente serie',
        amount=Decimal('4391566'),
        fraction_amount=Decimal('5000'),
        quantity=329460
    )

def configurar_cundinamarca(prize_types):
    """Configura Lotería de Cundinamarca con plan de premios completo"""
    print("Configurando Lotería de Cundinamarca...")
    
    cundinamarca = Lottery.objects.create(
        name='Lotería de Cundinamarca',
        code='CUNDINAMARCA',
        draw_day='MONDAY',
        draw_time=time(22, 30),
        fraction_count=3,
        fraction_price=Decimal('5000'),
        major_prize_amount=Decimal('6000000000'),
        min_bet_amount=Decimal('5000'),
        max_bet_amount=Decimal('6000000000'),
        is_active=True
    )

    cundinamarca_plan = PrizePlan.objects.create(
        lottery=cundinamarca,
        name='Plan de Premios 2023',
        start_date='2023-08-28',
        sorteo_number='4661',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=cundinamarca_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('6000000000'),
        fraction_amount=Decimal('1328000000'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_cundinamarca = [
        ('Mega Seco', Decimal('300000000'), Decimal('66400000'), 1),
        ('Super Tunjo', Decimal('100000000'), Decimal('22133333'), 1),
        ('Seco de 20 Millones', Decimal('20000000'), Decimal('4426667'), 5),
        ('Seco de 10 Millones', Decimal('10000000'), Decimal('2213333'), 15),
        ('Seco de 6 Millones', Decimal('6000000'), Decimal('1660000'), 32)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_cundinamarca, 2):
        Prize.objects.create(
            prize_plan=cundinamarca_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximaciones misma serie
    aprox_serie_cundinamarca = [
        ('Última cifra con serie', Decimal('216867'), 891),
        ('Dos primeras cifras con serie', Decimal('1807229'), 81),
        ('Dos últimas cifras con serie', Decimal('1807229'), 90),
        ('Dos primeras cifras y última cifra con serie', Decimal('18072289'), 9),
        ('Tres primeras cifras con serie', Decimal('18072289'), 9),
        ('Tres últimas cifras con serie', Decimal('18072289'), 9),
        ('Mayor en cualquier orden en las serie', Decimal('27108434'), 23)
    ]

    for name, amount, qty in aprox_serie_cundinamarca:
        Prize.objects.create(
            prize_plan=cundinamarca_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

    # Aproximaciones diferente serie
    aprox_diff_cundinamarca = [
        ('Última cifra sin serie', Decimal('18072'), 266409),
        ('Premio Mayor sin serie', Decimal('3614458'), 299),
        ('Dos primeras cifras sin serie', Decimal('21687'), 24219),
        ('Dos últimas cifras sin serie', Decimal('21687'), 26910),
        ('Tres primeras cifras sin serie', Decimal('180723'), 2691),
        ('Tres últimas cifras sin serie', Decimal('180723'), 2691),
        ('Serie del mayor', Decimal('180723'), 2691),
        ('Secos en diferente serie', Decimal('36145'), 6877),
        ('Mayor en cualquier orden sin serie', Decimal('28916'), 8887),
        ('Dos primeras y última cifra sin serie', Decimal('36145'), 16146)
    ]

    for name, amount, qty in aprox_diff_cundinamarca:
        Prize.objects.create(
            prize_plan=cundinamarca_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

def configurar_huila(prize_types):
    """Configura Lotería del Huila con plan de premios completo"""
    print("Configurando Lotería del Huila...")
    
    huila = Lottery.objects.create(
        name='Lotería del Huila',
        code='HUILA',
        draw_day='TUESDAY',
        draw_time=time(22, 30),
        fraction_count=3,
        fraction_price=Decimal('4000'),
        major_prize_amount=Decimal('2000000000'),
        min_bet_amount=Decimal('4000'),
        max_bet_amount=Decimal('2000000000'),
        is_active=True
    )

    huila_plan = PrizePlan.objects.create(
        lottery=huila,
        name='Plan de Premios 2024',
        start_date='2024-07-09',
        sorteo_number='4659',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=huila_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('2000000000'),
        fraction_amount=Decimal('442666667'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_huila = [
        ('Seco de 150 millones', Decimal('150000000'), Decimal('33200000'), 1),
        ('Seco de 100 millones', Decimal('100000000'), Decimal('22133333'), 5),
        ('Seco de 30 millones', Decimal('30000000'), Decimal('6640000'), 10),
        ('Seco de 15 millones', Decimal('15000000'), Decimal('3320000'), 10),
        ('Ganafijo sin serie', Decimal('2530120'), Decimal('700000'), 200)
    ]

    # Aproximaciones diferente serie
    aprox_diff_serie_huila = [
        ('El Super Opita', Decimal('2674699'), 199),
        ('Dos primeras', Decimal('32530'), 16119),
        ('Dos últimas', Decimal('32530'), 16119),
        ('Tres primeras', Decimal('43373'), 1791),
        ('Tres últimas', Decimal('43373'), 1791),
        ('Primera y dos últimas', Decimal('43373'), 1791),
        ('Dos primeras y última', Decimal('43373'), 1791),
        ('Última cifra', Decimal('14458'), 177309),
        ('Premios secos sin serie', Decimal('72289'), 5174)
    ]

    for name, amount, qty in aprox_diff_serie_huila:
        Prize.objects.create(
            prize_plan=huila_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

    # Aproximaciones con serie
    aprox_serie_huila = [
        ('Tres primeras', Decimal('14909639'), 7),
        ('Tres últimas', Decimal('11295181'), 9),
        ('Primera y dos últimas', Decimal('11295181'), 9),
        ('Dos primeras y última', Decimal('11295181'), 9),
        ('Dos primeras', Decimal('2710843'), 81),
        ('Dos últimas', Decimal('2710843'), 81),
        ('Última', Decimal('144578'), 891),
        ('Anterior al mayor', Decimal('32981928'), 1),
        ('Posterior al mayor', Decimal('32981928'), 1),
        ('COMBINADO OPITA(MAYOR EN CUALQUIER ORDEN)', Decimal('5421687'), 23)
    ]

    for name, amount, qty in aprox_serie_huila:
        Prize.objects.create(
            prize_plan=huila_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

def configurar_risaralda(prize_types):
    """Configura Lotería de Risaralda con plan de premios completo"""
    print("Configurando Lotería de Risaralda...")
    
    risaralda = Lottery.objects.create(
        name='Lotería de Risaralda',
        code='RISARALDA',
        draw_day='FRIDAY',
        draw_time=time(22, 30),
        fraction_count=3,
        fraction_price=Decimal('3000'),
        major_prize_amount=Decimal('1400000000'),
        min_bet_amount=Decimal('3000'),
        max_bet_amount=Decimal('1400000000'),
        is_active=True
    )

    risaralda_plan = PrizePlan.objects.create(
        lottery=risaralda,
        name='Plan de Premios 2021',
        start_date='2021-11-12',
        sorteo_number='2717',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=risaralda_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('1400000000'),
        fraction_amount=Decimal('309866666.67'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_risaralda = [
        ('Seco compra auto', Decimal('45000000'), Decimal('9960000'), 1),
        ('Secos pal negocio', Decimal('40000000'), Decimal('8853333.33'), 2),
        ('Super Secos Cafetero', Decimal('35000000'), Decimal('7746666.67'), 3),
        ('Secos pa´ la beca', Decimal('30000000'), Decimal('6640000'), 4),
        ('Secos de lujo', Decimal('25000000'), Decimal('5533333.33'), 5),
        ('Secos de paseo', Decimal('20000000'), Decimal('4426666.67'), 12)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_risaralda, 2):
        Prize.objects.create(
            prize_plan=risaralda_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Premio Especial La Escalera Millonaria
    Prize.objects.create(
        prize_plan=risaralda_plan,
        prize_type=prize_types['SPECIAL'],
        name='Premio Especial La Escalera Millonaria',
        amount=Decimal('45000000'),
        fraction_amount=Decimal('9960000'),
        quantity=1,
        order=1
    )

    # Aproximaciones a la Escalera Millonaria
    aprox_escalera = [
        ('Premios al acierto de las cuatro cifras en cualquier orden', Decimal('1927710.84'), 23),
        ('Premios al acierto de las cuatro cifras del número inferior', Decimal('2000000'), 500),
        ('Premios al acierto de las cuatro cifras del número principal', Decimal('54216.87'), 199)
    ]

    for name, amount, qty in aprox_escalera:
        Prize.objects.create(
            prize_plan=risaralda_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

    # Derivados del Mayor con Serie
    derivados_mayor_serie = [
        ('Mayor en cualquier orden', Decimal('1734939.76'), 22),
        ('Mayor invertido', Decimal('40000000'), 1),
        ('Chance Matecaña tres primeras', Decimal('18072289.16'), 9),
        ('Chance Matecaña tres últimas', Decimal('18072289.16'), 9),
        ('Dos primeras y última', Decimal('2385542.17'), 9),
        ('Primera y dos últimas', Decimal('2385542.17'), 9),
        ('Dos primeras cifras', Decimal('180722.89'), 80),
        ('Dos últimas cifras', Decimal('180722.89'), 80),
        ('Premios a la última cifra', Decimal('18072.29'), 887)
    ]

    for name, amount, qty in derivados_mayor_serie:
        Prize.objects.create(
            prize_plan=risaralda_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

    # Aproximaciones al Mayor y Secos en Diferente Serie
    aprox_mayor_diff_serie = [
        ('Premios al mayor', Decimal('2096385.54'), 199),
        ('Premios al mayor invertido', Decimal('1337349.40'), 199),
        ('Premios a las dos primeras y última', Decimal('18072.29'), 1791),
        ('Premios a la primera y dos últimas', Decimal('18072.29'), 1791),
        ('Premios a las tres primeras', Decimal('18072.29'), 1791),
        ('Premios a las tres últimas', Decimal('18072.29'), 1791),
        ('Premios a las dos primeras', Decimal('14457.83'), 16119),
        ('Premios a las dos últimas', Decimal('14457.83'), 16119),
        ('Premios a la última cifra', Decimal('10843.37'), 177309),
        ('Premios a los secos', Decimal('54216.87'), 5373)
    ]

    for name, amount, qty in aprox_mayor_diff_serie:
        Prize.objects.create(
            prize_plan=risaralda_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

def configurar_manizales(prize_types):
    """Configura Lotería de Manizales con plan de premios completo"""
    print("Configurando Lotería de Manizales...")
    
    manizales = Lottery.objects.create(
        name='Lotería de Manizales',
        code='MANIZALES',
        draw_day='WEDNESDAY',
        draw_time=time(22, 30),
        fraction_count=5,
        fraction_price=Decimal('2000'),
        major_prize_amount=Decimal('2200000000'),
        min_bet_amount=Decimal('2000'),
        max_bet_amount=Decimal('2200000000'),
        is_active=True
    )

    manizales_plan = PrizePlan.objects.create(
        lottery=manizales,
        name='Plan de Premios 2023',
        start_date='2023-12-06',
        sorteo_number='4828',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=manizales_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('2200000000'),
        fraction_amount=Decimal('1460800000'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_manizales = [
        ('Seco', Decimal('100000000'), Decimal('66400000'), 2),
        ('Seco', Decimal('80000000'), Decimal('53120000'), 5),
        ('Seco', Decimal('60000000'), Decimal('39840000'), 5),
        ('Seco', Decimal('30000000'), Decimal('19920000'), 10),
        ('Seco', Decimal('20000000'), Decimal('13280000'), 14)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_manizales, 2):
        Prize.objects.create(
            prize_plan=manizales_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximaciones al mayor en la misma serie
    aprox_serie_manizales = [
        ('Tres últimas', Decimal('25602410'), 9),
        ('Tres primeras', Decimal('25602410'), 9),
        ('Dos primeras y última', Decimal('25602410'), 9),
        ('Primera y dos últimas', Decimal('25602410'), 9),
        ('Dos últimas cifras', Decimal('4518072'), 80),
        ('Dos primeras cifras', Decimal('4518072'), 80),
        ('Última cifra', Decimal('216867'), 887),
        ('Mayor cualquier orden', Decimal('27108434'), 23)
    ]

    for name, amount, qty in aprox_serie_manizales:
        Prize.objects.create(
            prize_plan=manizales_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/5,
            quantity=qty
        )

    # Aproximaciones al mayor distinta serie
    aprox_diff_serie_manizales = [
        ('Mayor en otra serie', Decimal('3012048'), 349),
        ('Tres últimas', Decimal('96386'), 3141),
        ('Tres primeras', Decimal('96386'), 3141),
        ('Dos primeras y última', Decimal('36145'), 3141),
        ('Primera y dos últimas', Decimal('36145'), 3141),
        ('Dos últimas cifras', Decimal('18072'), 28269),
        ('Dos primeras cifras', Decimal('18072'), 28269),
        ('Última cifra', Decimal('12048'), 310959)
    ]

    for name, amount, qty in aprox_diff_serie_manizales:
        Prize.objects.create(
            prize_plan=manizales_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/5,
            quantity=qty
        )

    # Aproximaciones a los secos
    Prize.objects.create(
        prize_plan=manizales_plan,
        prize_type=prize_types['APPROX_DIFF_SERIES'],
        name='Secos en diferente serie',
        amount=Decimal('96385.54'),
        fraction_amount=Decimal('80000'),
        quantity=12564
    )

def configurar_medellin(prize_types):
    """Configura Lotería de Medellín con plan de premios completo"""
    print("Configurando Lotería de Medellín...")
    
    medellin = Lottery.objects.create(
        name='Lotería de Medellín',
        code='MEDELLIN',
        draw_day='FRIDAY',
        draw_time=time(22, 30),
        fraction_count=3,
        fraction_price=Decimal('7000'),
        major_prize_amount=Decimal('15000000000'),
        min_bet_amount=Decimal('7000'),
        max_bet_amount=Decimal('15000000000'),
        is_active=True
    )

    medellin_plan = PrizePlan.objects.create(
        lottery=medellin,
        name='Plan de Premios 2023',
        start_date='2023-10-13',
        sorteo_number='4700',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=medellin_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('15000000000'),
        fraction_amount=Decimal('3320000000'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_medellin = [
        ('Seco', Decimal('1000000000'), Decimal('221333333'), 1),
        ('Seco', Decimal('700000000'), Decimal('154933333'), 3),
        ('Seco', Decimal('100000000'), Decimal('22133333'), 5),
        ('Secos', Decimal('50000000'), Decimal('11066667'), 5),
        ('Secos', Decimal('20000000'), Decimal('4426667'), 10),
        ('Secos', Decimal('10000000'), Decimal('2213333'), 15)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_medellin, 2):
        Prize.objects.create(
            prize_plan=medellin_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximaciones con serie
    aprox_serie_medellin = [
        ('Tres primeras cifras', Decimal('24000000'), 9),
        ('Tres últimas cifras', Decimal('24000000'), 9),
        ('Dos primeras cifras', Decimal('9000000'), 90),
        ('Dos últimas cifras', Decimal('9000000'), 90),
        ('Última cifra', Decimal('387802'), 891),
        ('Serie del mayor', Decimal('25301'), 8910)
    ]

    for name, amount, qty in aprox_serie_medellin:
        Prize.objects.create(
            prize_plan=medellin_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

    # Aproximaciones sin serie
    aprox_diff_serie_medellin = [
        ('Mayor sin serie', Decimal('9000000'), 499),
        ('Tres primeras', Decimal('54217'), 4491),
        ('Tres últimas', Decimal('54217'), 4491),
        ('Dos primeras', Decimal('36145'), 44910),
        ('Dos últimas', Decimal('36145'), 44910),
        ('Última', Decimal('25301'), 444609),
        ('Secos sin serie', Decimal('36145'), 19461)
    ]

    for name, amount, qty in aprox_diff_serie_medellin:
        Prize.objects.create(
            prize_plan=medellin_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

def configurar_meta(prize_types):
    """Configura Lotería del Meta con plan de premios completo"""
    print("Configurando Lotería del Meta...")
    
    meta = Lottery.objects.create(
        name='Lotería del Meta',
        code='META',
        draw_day='WEDNESDAY',
        draw_time=time(22, 30),
        fraction_count=3,
        fraction_price=Decimal('3000'),
        major_prize_amount=Decimal('1500000000'),
        min_bet_amount=Decimal('3000'),
        max_bet_amount=Decimal('1500000000'),
        is_active=True
    )

    meta_plan = PrizePlan.objects.create(
        lottery=meta,
        name='Plan de Premios 2018',
        start_date='2018-09-05',
        sorteo_number='2904',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=meta_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('1500000000'),
        fraction_amount=Decimal('332000000'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_meta = [
        ('SECO DE $300 MILLONES', Decimal('300000000'), Decimal('66400000'), 1),
        ('SECO DE $100 MILLONES', Decimal('100000000'), Decimal('22133333.33'), 1),
        ('SECO DE $60 MILLONES', Decimal('60000000'), Decimal('13280000'), 2),
        ('SECO DE $30 MILLONES', Decimal('30000000'), Decimal('6640000'), 5),
        ('SECO DE $10 MILLONES', Decimal('10000000'), Decimal('2213333.33'), 7),
        ('SECO DE $6 MILLONES', Decimal('6000000'), Decimal('1328000'), 26)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_meta, 2):
        Prize.objects.create(
            prize_plan=meta_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximaciones al mayor misma serie
    aprox_serie_meta = [
        ('MAYOR INVERTIDO', Decimal('9000000'), 1),
        ('TRE PRIMERAS CIFRAS', Decimal('8000000'), 9),
        ('TRES ÚLTIMAS CIFRAS', Decimal('8000000'), 9),
        ('DOS PRIMERAS CIFRAS Y ÚLTIMA', Decimal('8000000'), 9),
        ('DOS ÚLTIMAS CIFRAS', Decimal('54217'), 90),
        ('DOS PRIMERAS CIFRAS', Decimal('54216.87'), 81),
        ('ÚLTIMA CIFRA', Decimal('27108.43'), 891)
    ]

    for name, amount, qty in aprox_serie_meta:
        Prize.objects.create(
            prize_plan=meta_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

    # Aproximaciones al mayor diferente serie
    aprox_diff_meta = [
        ('MAYOR EN DIFERENTE SERIE', Decimal('1445783'), 129),
        ('SECOS EN DIFERENTE SERIE', Decimal('21687'), 5418),
        ('MAYOR INVERTIDO EN DIFERENTE SERIE', Decimal('43373.13'), 129),
        ('TRES PRIMERAS CIFRAS DEL MAYOR', Decimal('32530.12'), 1161),
        ('DOS PRIMERAS CIFRAS Y ÚLTIMA', Decimal('32530.12'), 1161),
        ('TRES ÚLTIMAS CIFRAS DEL MAYOR', Decimal('32530.12'), 1161),
        ('DOS PRIMERAS CIFRAS', Decimal('16265.06'), 10449),
        ('DOS ÚLTIMAS CIFRAS DEL MAYOR', Decimal('16265.06'), 11610),
        ('ÚLTIMA CIFRA DEL MAYOR', Decimal('10843.37'), 114939)
    ]

    for name, amount, qty in aprox_diff_meta:
        Prize.objects.create(
            prize_plan=meta_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

def configurar_quindio(prize_types):
    """Configura Lotería del Quindío con plan de premios completo"""
    print("Configurando Lotería del Quindío...")
    
    quindio = Lottery.objects.create(
        name='Lotería del Quindío',
        code='QUINDIO',
        draw_day='THURSDAY',
        draw_time=time(22, 30),
        fraction_count=5,
        fraction_price=Decimal('2000'),
        major_prize_amount=Decimal('1800000000'),
        min_bet_amount=Decimal('2000'),
        max_bet_amount=Decimal('1800000000'),
        is_active=True
    )

    quindio_plan = PrizePlan.objects.create(
        lottery=quindio,
        name='Plan de Premios 2023',
        start_date='2023-04-13',
        sorteo_number='2856',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=quindio_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('1800000000'),
        fraction_amount=Decimal('1195200000'),
        quantity=1,
        order=1
    )

    # Secos y premios especiales
    premios_secos_quindio = [
        ('Seco de 150 millones', Decimal('150000000'), Decimal('99600000'), 1),
        ('Sueldazo cafetero 80 millones', Decimal('80000000'), Decimal('53120000'), 2),
        ('Seco de 50 millones', Decimal('50000000'), Decimal('33200000'), 3),
        ('Seco de 25 millones', Decimal('25000000'), Decimal('16600000'), 11),
        ('Seco de 10 millones', Decimal('10000000'), Decimal('6640000'), 15),
        ('Quindianito sin serie', Decimal('722892'), Decimal('600000'), 200)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_quindio, 2):
        Prize.objects.create(
            prize_plan=quindio_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximación con serie
    aprox_serie_quindio = [
        ('Mayor invertido', Decimal('13662651'), 1),
        ('3 Primeras cifras', Decimal('1566265'), 9),
        ('3 Últimas cifras', Decimal('1566265'), 9),
        ('Combinado con serie', Decimal('1566265'), 22),
        ('2 Últimas', Decimal('84337'), 89),
        ('2 Primeras', Decimal('84337'), 89),
        ('2 del Centro', Decimal('60241'), 80),
        ('Primera y Última', Decimal('60241'), 80),
        ('Última', Decimal('24096'), 807),
        ('Serie', Decimal('12048'), 8813)
    ]

    for name, amount, qty in aprox_serie_quindio:
        Prize.objects.create(
            prize_plan=quindio_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/5,
            quantity=qty
        )

    # Aproximaciones sin serie
    aprox_sin_serie_quindio = [
        ('Premio mayor', Decimal('1566265'), 199),
        ('Mayor Invertido', Decimal('1566265'), 199),
        ('Combinado sin serie', Decimal('72289'), 4378),
        ('3 Primeras cifras', Decimal('24096'), 1791),
        ('3 Últimas cifras', Decimal('24096'), 1791),
        ('2 Últimas', Decimal('18072'), 17711),
        ('2 Primeras', Decimal('18072'), 17711),
        ('2 del centro', Decimal('18072'), 15920),
        ('Primera y última', Decimal('18072'), 15920),
        ('Última', Decimal('12048'), 160593)
    ]

    for name, amount, qty in aprox_sin_serie_quindio:
        Prize.objects.create(
            prize_plan=quindio_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/5,
            quantity=qty
        )

def configurar_santander(prize_types):
    """Configura Lotería de Santander con plan de premios completo"""
    print("Configurando Lotería de Santander...")
    
    santander = Lottery.objects.create(
        name='Lotería de Santander',
        code='SANTANDER',
        draw_day='FRIDAY',
        draw_time=time(22, 30),
        fraction_count=3,
        fraction_price=Decimal('6000'),
        major_prize_amount=Decimal('10000000000'),
        min_bet_amount=Decimal('6000'),
        max_bet_amount=Decimal('10000000000'),
        is_active=True
    )

    santander_plan = PrizePlan.objects.create(
        lottery=santander,
        name='Plan de Premios 2024',
        start_date='2024-01-05',
        sorteo_number='4947',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=santander_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('10000000000'),
        fraction_amount=Decimal('2213333333'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_santander = [
        ('Seco 1.000 millones', Decimal('1000000000'), Decimal('221333333'), 1),
        ('Seco 100 millones', Decimal('100000000'), Decimal('22133333'), 2),
        ('Seco 50 millones', Decimal('50000000'), Decimal('11066667'), 5),
        ('Seco 20 millones', Decimal('20000000'), Decimal('4426667'), 5),
        ('Seco 10 millones', Decimal('10000000'), Decimal('2213333'), 5),
        ('Seco 5 millones', Decimal('5000000'), Decimal('1383333'), 15)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_santander, 2):
        Prize.objects.create(
            prize_plan=santander_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximaciones al mayor con serie
    aprox_mayor_serie = [
        ('Tres primeras', Decimal('9000000'), 9),
        ('Tres últimas', Decimal('9000000'), 9),
        ('Dos primeras', Decimal('1084337'), 90),
        ('Dos últimas', Decimal('1084337'), 90),
        ('Última cifra', Decimal('108434'), 891),
        ('Mayor invertido', Decimal('10000000'), 1),
        ('Serie', Decimal('21687'), 8909)
    ]

    for name, amount, qty in aprox_mayor_serie:
        Prize.objects.create(
            prize_plan=santander_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

    # Aproximaciones mayor sin serie
    aprox_mayor_sin_serie = [
        ('Mayor en diferente serie', Decimal('5000000'), 379),
        ('Tres primeras', Decimal('216867'), 3411),
        ('Tres últimas', Decimal('216867'), 3411),
        ('Dos primeras', Decimal('36145'), 34110),
        ('Dos últimas', Decimal('36145'), 34110),
        ('Última cifra', Decimal('21687'), 337689),
        ('Mayor invertido', Decimal('5000000'), 379),
        ('Secos sin serie', Decimal('21687'), 12507)
    ]

    for name, amount, qty in aprox_mayor_sin_serie:
        Prize.objects.create(
            prize_plan=santander_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

def configurar_tolima(prize_types):
    """Configura Lotería del Tolima con plan de premios completo"""
    print("Configurando Lotería del Tolima...")
    
    tolima = Lottery.objects.create(
        name='Lotería del Tolima',
        code='TOLIMA',
        draw_day='MONDAY',
        draw_time=time(22, 30),
        fraction_count=3,
        fraction_price=Decimal('4000'),
        major_prize_amount=Decimal('3000000000'),
        min_bet_amount=Decimal('4000'),
        max_bet_amount=Decimal('3000000000'),
        is_active=True
    )

    tolima_plan = PrizePlan.objects.create(
        lottery=tolima,
        name='Plan de Premios 2023',
        start_date='2023-05-08',
        sorteo_number='4012',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=tolima_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('3000000000'),
        fraction_amount=Decimal('664000000'),
        quantity=1,
        order=1
    )

    # Secos y premios especiales
    premios_secos_tolima = [
        ('Bono "La casa de mis sueños"', Decimal('150000000'), Decimal('33200000'), 1),
        ('Bono "El carro de mis sueños"', Decimal('150000000'), Decimal('33200000'), 1),
        ('Secos Extrapijao', Decimal('100000000'), Decimal('22133333'), 1),
        ('Secos Mega Fortuna', Decimal('50000000'), Decimal('11066667'), 4),
        ('Secos Lotto Millonario', Decimal('8000000'), Decimal('1770667'), 15),
        ('Secos de Oro', Decimal('10000000'), Decimal('2213333'), 9),
        ('Quincenazo de la Tolima', Decimal('24000000'), Decimal('5312000'), 2),
        ('Secos revancha', Decimal('70000000'), Decimal('15493333'), 1)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_tolima, 2):
        Prize.objects.create(
            prize_plan=tolima_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximaciones con serie
    aprox_serie_tolima = [
        ('Mayor invertido', Decimal('80000000'), 1),
        ('Mayor en cualquier orden', Decimal('10210843.37'), 22),
        ('Tres primeras', Decimal('8000000'), 9),
        ('Tres últimas', Decimal('8000000'), 9),
        ('Última', Decimal('28915.53'), 887),
        ('Dos últimas', Decimal('759036.15'), 80),
        ('Dos primeras', Decimal('759036.15'), 80),
        ('Dos primeras y última', Decimal('2430000'), 9),
        ('Primera y dos últimas', Decimal('2430000'), 9)
    ]

    aprox_sin_serie_tolima = [
        ('Mayor en distinta serie', Decimal('3012048.19'), 199),
        ('Mayor invertido', Decimal('3012048.19'), 199),
        ('Dos primeras y última', Decimal('28915.66'), 1791),
        ('Primera y dos últimas', Decimal('28915.66'), 1791),
        ('Tres primeras', Decimal('43373.49'), 1791),
        ('Tres últimas', Decimal('43373.49'), 1791),
        ('Dos primeras', Decimal('25301.21'), 16119),
        ('Dos últimas', Decimal('25301.21'), 16119),
        ('Última', Decimal('14457.82'), 177309),
        ('Secos especiales', Decimal('28915.66'), 199),
        ('Secos sin series', Decimal('28915.66'), 6567)
    ]

    for name, amount, qty in aprox_sin_serie_tolima:
        Prize.objects.create(
            prize_plan=tolima_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

def configurar_valle(prize_types):
    """Configura Lotería del Valle con plan de premios completo"""
    print("Configurando Lotería del Valle...")
    
    valle = Lottery.objects.create(
        name='Lotería del Valle',
        code='VALLE',
        draw_day='WEDNESDAY',
        draw_time=time(22, 30),
        fraction_count=3,
        fraction_price=Decimal('5000'),
        major_prize_amount=Decimal('6000000000'),
        min_bet_amount=Decimal('5000'),
        max_bet_amount=Decimal('6000000000'),
        is_active=True
    )

    valle_plan = PrizePlan.objects.create(
        lottery=valle,
        name='Plan de Premios 2023',
        start_date='2023-06-07',
        sorteo_number='4695',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=valle_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('6000000000'),
        fraction_amount=Decimal('1328000000'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_valle = [
        ('Primer seco', Decimal('240000000'), Decimal('53120000'), 1),
        ('Segundo seco', Decimal('120000000'), Decimal('26560000'), 1),
        ('Tercer seco', Decimal('30000000'), Decimal('6640000'), 1),
        ('Cuarto seco', Decimal('30000000'), Decimal('6640000'), 1),
        ('Quinto seco', Decimal('30000000'), Decimal('6640000'), 1),
        ('Sexto seco', Decimal('15000000'), Decimal('3320000'), 1),
        ('Séptimo seco', Decimal('15000000'), Decimal('3320000'), 1),
        ('Secos 12 millones', Decimal('12000000'), Decimal('2656000'), 23)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_valle, 2):
        Prize.objects.create(
            prize_plan=valle_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximación al mayor con serie
    aprox_serie_valle = [
        ('Posterior', Decimal('5060241'), 1),
        ('Anterior', Decimal('5060241'), 1),
        ('Serie', Decimal('18072'), 8908),
        ('Última', Decimal('36145'), 891),
        ('Dos últimas', Decimal('722892'), 81),
        ('Dos primeras', Decimal('722892'), 81),
        ('Tres primeras', Decimal('7228916'), 9),
        ('Tres últimas', Decimal('7228916'), 9),
        ('Primera y dos últimas', Decimal('7228916'), 9),
        ('Dos primeras y última', Decimal('7228916'), 9)
    ]

    for name, amount, qty in aprox_serie_valle:
        Prize.objects.create(
            prize_plan=valle_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

    # Aproximaciones al mayor en diferente serie
    aprox_diff_valle = [
        ('Última', Decimal('18072'), 221859),
        ('Dos últimas', Decimal('36145'), 20169),
        ('Dos primeras', Decimal('36145'), 20169),
        ('Tres primeras', Decimal('54217'), 2241),
        ('Tres últimas', Decimal('54217'), 2241),
        ('Dos primeras y última', Decimal('54217'), 2241),
        ('Primera y dos últimas', Decimal('54217'), 2241),
        ('Cuatro cifras', Decimal('5783133'), 249),
        ('Secos en diferente serie', Decimal('36145'), 7470)
    ]

    for name, amount, qty in aprox_diff_valle:
        Prize.objects.create(
            prize_plan=valle_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount/3,
            quantity=qty
        )

def configurar_extra_colombia(prize_types):
    """Configura Sorteo Extraordinario de Colombia"""
    print("Configurando Sorteo Extraordinario de Colombia...")
    
    extra = Lottery.objects.create(
        name='Sorteo Extraordinario de Colombia',
        code='EXTRA',
        draw_day='SATURDAY',
        draw_time=time(22, 30),
        fraction_count=1,
        fraction_price=Decimal('16000'),
        major_prize_amount=Decimal('12000000000'),
        min_bet_amount=Decimal('16000'),
        max_bet_amount=Decimal('12000000000'),
        is_active=True
    )

    extra_plan = PrizePlan.objects.create(
        lottery=extra,
        name='Plan de Premios 2023',
        start_date='2023-12-30',
        sorteo_number='2222',
        is_active=True
    )

    # Premio Mayor
    Prize.objects.create(
        prize_plan=extra_plan,
        prize_type=prize_types['MAJOR'],
        amount=Decimal('12000000000'),
        fraction_amount=Decimal('7968000000'),
        quantity=1,
        order=1
    )

    # Secos
    premios_secos_extra = [
        ('1 seco de 300 millones', Decimal('300000000'), Decimal('199200000'), 1),
        ('1 seco de 200 millones', Decimal('200000000'), Decimal('132800000'), 1),
        ('1 seco de 100 millones', Decimal('100000000'), Decimal('66400000'), 1),
        ('2 seco de 50 millones', Decimal('50000000'), Decimal('33200000'), 2),
        ('10 seco de 20 millones', Decimal('20000000'), Decimal('13280000'), 10),
        ('25 seco de 10 millones', Decimal('10000000'), Decimal('6640000'), 25)
    ]

    for idx, (name, amount, fraction_amount, qty) in enumerate(premios_secos_extra, 2):
        Prize.objects.create(
            prize_plan=extra_plan,
            prize_type=prize_types['SECO'],
            name=name,
            amount=amount,
            fraction_amount=fraction_amount,
            quantity=qty,
            order=idx
        )

    # Aproximaciones con serie
    aprox_serie_extra = [
        ('Mayor invertido', Decimal('10000000'), 1),
        ('3 Primeras cifras', Decimal('2168674.70'), 9),
        ('3 Últimas cifras', Decimal('2168674.70'), 9),
        ('Dos primeras y última', Decimal('1445783.13'), 9),
        ('Primera y dos últimas', Decimal('1445783.13'), 9),
        ('Combinado con serie', Decimal('963855.42'), 22),
        ('2 Últimas', Decimal('542168.67'), 80),
        ('2 Primeras', Decimal('542168.67'), 80),
        ('2 del Centro', Decimal('361445.78'), 80),
        ('Última', Decimal('144578.31'), 887)
    ]

    for name, amount, qty in aprox_serie_extra:
        Prize.objects.create(
            prize_plan=extra_plan,
            prize_type=prize_types['APPROX_SAME_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount,  # Una sola fracción
            quantity=qty
        )

    # Otras aproximaciones
    aprox_otras_extra = [
        ('Secos en otras series', Decimal('24096.39'), 15960)
    ]

    for name, amount, qty in aprox_otras_extra:
        Prize.objects.create(
            prize_plan=extra_plan,
            prize_type=prize_types['APPROX_DIFF_SERIES'],
            name=name,
            amount=amount,
            fraction_amount=amount,  # Una sola fracción
            quantity=qty
        )

if __name__ == "__main__":
    setup_complete_lottery_system()
