import datetime
from django.db import models
from django.utils import timezone
from django.urls import reverse
from .validators import *

class Curve(models.Model):
    name = models.CharField(max_length =200, unique=True)
    limit = models.FloatField()

    def get_other_warnings(self): 
        warning_objects = self.otherwarning_set.all().filter(active = True )
        return warning_objects

    def get_flowmeters(self): 
        flowmeters_objects = self.flowmeter_set.all()
        return flowmeters_objects

    def get_absolute_url(self):
        return reverse("curve-detail", kwargs={"pk": self.pk})

    def clean(self):
        self.name=' '.join(self.name.capitalize().split())

    def __str__(self):
        return self.name

class Type(models.Model):
    # tipo de la señal ( analogica/digital)
    name = models.CharField(max_length =200)

    def __str__(self):
        return self.name

class Flowmeter(models.Model):
    # nombres de las señales de Telemando
    name = models.CharField(max_length =200, unique=True)
    #fk_curve = models.ForeignKey(Curve, on_delete= models.CASCADE)
    curves = models.ManyToManyField(Curve)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("flowmeter-detail", kwargs={"pk": self.pk})

    def analog_signal(self):
        signal_query = self.signal_set.filter(fk_tipo=1)
        if  bool(signal_query):
            return signal_query.values("tagname")[0]["tagname"]
        else:
            return "ERROR: No existe señal analógica asociada"

    def digital_signal(self):
        signal_query = self.signal_set.filter(fk_tipo=2)
        if bool(signal_query):
            return signal_query.values("tagname")[0]["tagname"]
        else:
            return "No existe señal digital asociada"

    def clean(self):
        self.name=' '.join(self.name.capitalize().split())

class Signal(models.Model):
    # nombres de las señales de Telemando
    tagname = models.CharField(max_length =200, unique=True)
    fk_tipo = models.ForeignKey(Type,  on_delete= models.CASCADE)
    fk_flowmeter =  models.ForeignKey(Flowmeter,  on_delete= models.CASCADE)

    def __str__(self):
        return self.tagname

    def get_absolute_url(self):
        return reverse("signal-detail", kwargs={"pk": self.pk})
    
    def clean(self):
        self.tagname=' '.join(self.tagname.capitalize().split())

class Consume(models.Model):
    # demanda en tiempo real ( calculada a partir de los balances )
    sample_value = models.FloatField()
    sample_datetime = models.DateTimeField(
        validators= [validate_date_not_in_future,validate_date_10_minutes]
    )
    fk_curve = models.ForeignKey(Curve, on_delete= models.CASCADE)
    unique_together = ('sample_datetime', 'fk_curve')


    def get_forecast_sample_value(self): 
        forecast_object = self.fk_curve.forecast_set.all().filter(sample_datetime = self.sample_datetime )
        forecast_sample_value = forecast_object.values("sample_value")[0]["sample_value"] if forecast_object else None
        return forecast_sample_value 

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ["sample_datetime", "fk_curve"]
        else:
            return []
    
    def get_absolute_url(self):
        return "/consumo/"+str(self.id)


class Forecast(models.Model):
    # prediccion de la demanda 
    sample_value = models.FloatField()
    sample_datetime = models.DateTimeField()
    fk_curve = models.ForeignKey(Curve, on_delete= models.CASCADE)
    unique_together = ('sample_datetime', 'fk_curve')

    def get_diff(self): 
        consume_sample_value = self.get_consume_sample_value() 
        diff = consume_sample_value - self.sample_value if consume_sample_value else None
        return diff

    def get_consume_sample_value(self): 
        consume_object = self.fk_curve.consume_set.all().filter(sample_datetime = self.sample_datetime )
        consume_sample_value = consume_object.values("sample_value")[0]["sample_value"] if consume_object else None
        return consume_sample_value 

    # def is_for_24h(self):
    #     now = timezone.now()
    #     return now  <= self.sample_datetime <= now + datetime.timedelta(days=1)

    #def __str__(self):
    #    return self.sample_value

class Lecture(models.Model):
    # lectura del Octubre
    sample_value = models.FloatField()
    sample_datetime = models.DateTimeField(validators= [validate_date_not_in_future])
    fk_signal = models.ForeignKey(Signal, on_delete= models.CASCADE)


class ModelMl(models.Model):
    # modelos de aprendizaje automatico
    name = models.CharField(max_length =200, unique=True)
    error = models.FloatField() 

    def __str__(self):
        return self.name

    def clean(self):
        self.name=' '.join(self.name.capitalize().split())

class Warning(models.Model):
    # modelos de aprendizaje automatico
    text = models.CharField(max_length =200)
    sample_datetime = models.DateTimeField(validators= [validate_date_not_in_future])
    active = models.BooleanField(default=True)
    #fk_curve = models.ForeignKey(Curve, on_delete= models.CASCADE)
    fk_consume = models.ForeignKey(Consume, related_name='fk_consume', on_delete= models.CASCADE)

    
    def get_absolute_url(self):
        return reverse("warning-detail", kwargs={"pk": self.pk})

    def get_diff_value(self): 
        return  self.fk_consume.sample_value - self.get_forecast_sample_value() 

    def get_forecast_sample_value(self): 
        forecast_object = self.fk_consume.fk_curve.forecast_set.all().filter(sample_datetime = self.fk_consume.sample_datetime )
        forecast_sample_value = forecast_object.values("sample_value")[0]["sample_value"]
        return forecast_sample_value 

    #def __str__(self):
        #return self.name

