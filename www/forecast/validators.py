from django.core.exceptions import ValidationError
from django.utils import timezone

def validate_date_not_in_future(value):
    if value > timezone.now():
        raise ValidationError('FECHA Y HORA SOBREPASAN EL '+timezone.now().strftime("%Y-%m-%d %H:%M"))

def validate_date_10_minutes(value):
    if value.minute % 10 != 0 and value.minute != 0:
        raise ValidationError('LOS MINUTOS DE HORA DEBEN SEGUIR EL INTERVALO DE 10 MINUTOS ')


