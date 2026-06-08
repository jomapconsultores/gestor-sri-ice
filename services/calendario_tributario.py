"""
Calendario tributario SRI (Ecuador).

La fecha máxima de declaración de impuestos depende del NOVENO dígito del RUC.
Estas son las fechas de las declaraciones MENSUALES (IVA - Formulario 104,
Retenciones en la fuente - Formulario 103, ICE - Formulario 113), que se
presentan en el mes siguiente al período declarado.

Tabla oficial (9no dígito -> día máximo):
    1 -> 10      6 -> 20
    2 -> 12      7 -> 22
    3 -> 14      8 -> 24
    4 -> 16      9 -> 26
    5 -> 18      0 -> 28

Nota: si el día cae en fin de semana o feriado, el SRI lo traslada al
siguiente día hábil. Aquí se devuelve la fecha base (el usuario solo pidió
la fecha según el dígito).
"""
from datetime import date

# 9no dígito del RUC -> día máximo de declaración mensual
DIA_POR_DIGITO = {
    1: 10, 2: 12, 3: 14, 4: 16, 5: 18,
    6: 20, 7: 22, 8: 24, 9: 26, 0: 28,
}

MESES_ES = [
    '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]


def noveno_digito(ruc):
    """Devuelve el noveno dígito del RUC como entero, o None si el RUC no es válido."""
    if not ruc:
        return None
    ruc = str(ruc).strip()
    if len(ruc) < 9 or not ruc.isdigit():
        return None
    return int(ruc[8])


def dia_declaracion(ruc):
    """Día máximo (1-28) de declaración mensual según el 9no dígito del RUC. None si inválido."""
    digito = noveno_digito(ruc)
    if digito is None:
        return None
    return DIA_POR_DIGITO.get(digito)


def proxima_fecha_declaracion(ruc, hoy=None):
    """
    Próxima fecha concreta de declaración mensual a partir de 'hoy'.
    Devuelve un objeto date, o None si el RUC es inválido.
    """
    dia = dia_declaracion(ruc)
    if dia is None:
        return None
    if hoy is None:
        hoy = date.today()
    # Próxima ocurrencia del día (este mes si aún no pasa, si no el mes siguiente)
    anio, mes = hoy.year, hoy.month
    if hoy.day > dia:
        mes += 1
        if mes > 12:
            mes = 1
            anio += 1
    return date(anio, mes, dia)


def info_declaracion(ruc, hoy=None):
    """
    Resumen listo para mostrar en plantillas.
    Retorna dict con: valido, digito, dia, proxima_fecha, proxima_fecha_texto.
    """
    digito = noveno_digito(ruc)
    dia = DIA_POR_DIGITO.get(digito) if digito is not None else None
    if dia is None:
        return {
            'valido': False,
            'digito': digito,
            'dia': None,
            'proxima_fecha': None,
            'proxima_fecha_texto': None,
        }
    fecha = proxima_fecha_declaracion(ruc, hoy=hoy)
    return {
        'valido': True,
        'digito': digito,
        'dia': dia,
        'proxima_fecha': fecha,
        'proxima_fecha_texto': f'{fecha.day} de {MESES_ES[fecha.month]} de {fecha.year}',
    }
