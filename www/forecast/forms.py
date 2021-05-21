from django import forms
from .models import Curve, Flowmeter, Signal, Consume, Warning
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.utils.html import format_html

class CurveForm(forms.ModelForm):
    class Meta:
        model = Curve
        fields = ['name','limit',]
        labels = {
            'name': 'Nombre',
            'limit': 'Limite'
        }
    # place for model validation
   
class FlowmeterForm(forms.ModelForm):
    class Meta:
        model = Flowmeter
        fields = ['name', 'curves']
        labels = {
            'name': 'Nombre',
            'curves': 'Curvas'
        }
     
    # place for model validation


class SignalForm(forms.ModelForm):
    class Meta:
        model = Signal
        fields = ['tagname', 'fk_flowmeter','fk_tipo',]
        labels = {
            'tagname': 'Nombre',
            'fk_flowmeter': 'Cudalímetro',
            'fk_tipo': 'Tipo',
        }
    # place for model validation

class WarningForm(forms.ModelForm):

    error_css_class = 'error'

    disabled_fields = ['sample_datetime', 'text']

    class Meta:
        model = Warning
        fields = ['text', 'sample_datetime','active']
        labels = {
            'text': 'Contenido',
            'sample_datetime': 'Fecha y hora del aviso',
            'active': 'Activo',
        }

    def __init__(self, *args, **kwargs):
        super(WarningForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            for field in self.disabled_fields:
                self.fields[field].disabled = True
        else:
            #self.fields['reviewed'].disabled = True
            pass

class ConsumeForm(forms.ModelForm):

    disabled_fields = ['sample_datetime', 'fk_curve']

    class Meta:
        model = Consume
      
        fields = ['sample_value','sample_datetime','fk_curve']
        labels = {
            'sample_value': 'Consumo en 10 minutos',
            'sample_datetime': 'Fecha y hora del consumo (YYYY-MM-DD HH:mm)',
            'fk_curve': 'Curva de demanda',
        }
        
    def clean(self):
        cleaned_data = self.cleaned_data
        try:
            consume_selected = Consume.objects.get(sample_datetime=cleaned_data['sample_datetime'], fk_curve=cleaned_data['fk_curve'])
        except Consume.DoesNotExist:
            pass
        else:
            message = format_html('Registro con un consumo para esta fecha y hora ya existe para la curva seleccionada. Pincha <a href="/consumo/%s">aquí</a> para ver el registro'% str(consume_selected.pk))
            raise ValidationError(message)

        # Always return cleaned_data
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super(ConsumeForm, self).__init__(*args, **kwargs)

       
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            for field in self.disabled_fields:
                self.fields[field].disabled = True
        else:
            #self.fields['reviewed'].disabled = True
            pass
  