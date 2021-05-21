from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404, HttpResponseRedirect, JsonResponse
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.utils import timezone
from django.contrib import auth

from .models import Forecast, Curve, Flowmeter, Lecture, ModelMl, Warning, Consume,Warning, Signal
from .forms import CurveForm, FlowmeterForm, SignalForm, WarningForm,ConsumeForm

# for chart view
from rest_framework.views import APIView
from rest_framework.response import Response

from datetime import timedelta
import requests 
from itertools import chain
import pytz
import os

import logging


def get_user_info(self):

    if 'cps-forecast-role' in self.request.session['user']:
        role = self.request.session['user']['cps-forecast-role']
    else: 
        role = "not-admin"

    return { 'name': self.request.session['user']['name'], 
            'role': role }

def logout(request):
    """
    Removes the authenticated user's ID from the request and flushes their
    session data.
    """
    # Dispatch the signal before the user is logged out so the receivers have a
    # chance to find out *who* logged out.
    token = request.session.get('token', None)
    idtoken = token['id_token']

    # defining a params dict for the parameters to be sent to the API 
    URL = (os.environ["ID_SERVER_URL"] +"/connect/endsession") 
    PARAMS = {'id_token_hint':idtoken, "post_logout_redirect_uri": os.environ["APP_URL"]+'/signout-callback-oidc',} 
    
    # sending get request and saving the response as response object 
    request_endsession = requests.get(url = URL, params = PARAMS) 
    redirect_uri = request_endsession.url

    auth.logout(request)

    return redirect(redirect_uri) 

# method for all Views
def get_warnings_info():

    from_date = timezone.now().replace(second=0,microsecond=0)

    warnings = Warning.objects.filter(
        active = True,
        sample_datetime__lte = from_date, 
        sample_datetime__gte =from_date-timedelta(hours=24)
    ).count()
   
    return warnings

class IndexView(generic.ListView):
    template_name = 'forecast/index.html'
    context_object_name = 'response'
    

    def get_queryset(self):
        """
        Return the curves.
        """

        # curvas 
        curves = Curve.objects.all()

        warnings = get_warnings_info()
        
        return   {
                  'user': get_user_info(self),
                  'curves': curves,
                  'warnings': warnings,
                  }

class ForecastDetailView(generic.ListView):
    template_name = 'forecast/forecast_detail.html'
    context_object_name = 'response'

    def get_queryset(self):
        """
        Return the last 24h forecast (not including all week).
        """
        data_forecast = []
        data_consume = []
        pk_ = self.kwargs.get("pk")
        curve = get_object_or_404(Curve, pk=pk_)
        from_date = timezone.now().replace(second=0,microsecond=0)

        # datos de la tabla forecast ( predicción del consumo)
        forecast_set= Forecast.objects.filter(
            fk_curve = pk_,
            sample_datetime__lte = from_date + timedelta(minutes= 30), 
            sample_datetime__gte =from_date-timedelta(hours=24)
        ).order_by('-sample_datetime')

        # curvas 
        curves = Curve.objects.all()
        warnings = get_warnings_info()
        return   {
                  'user': get_user_info(self),
                  'curve': curve,  
                  'curves': curves,
                  'forecast_set':forecast_set,
                  'warnings': warnings,
                  }


class CurvesView(generic.ListView):

    template_name = 'forecast/curves.html'
    context_object_name = 'response'

    def get_queryset(self):

        return   {
                  'user': get_user_info(self),
                  'set_curves': Curve.objects.all(),  
                  'warnings': get_warnings_info(),
                  }

class CurveDetailView(generic.DetailView):
    template_name = 'forecast/curve_detail.html'

    def get_context_data(self, **kwargs):
        context = super(CurveDetailView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user': get_user_info(self),}
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return  get_object_or_404(Curve, pk = pk_)

class CurveCreateView(generic.CreateView):
    model = Curve
    form_class = CurveForm
    template_name = 'forecast/curve_form.html'

    def get_context_data(self, **kwargs):
        context = super(CurveCreateView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user': get_user_info(self),}
        return context

    def form_valid(self, form):
        return super().form_valid(form)

class CurveUpdateView(generic.UpdateView):
    model = Curve
    form_class = CurveForm
    template_name = 'forecast/curve_form.html'
    queryset = Curve.objects.all()

    def get_context_data(self, **kwargs):
        context = super(CurveUpdateView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user':get_user_info(self)}
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Curve, pk = pk_)

    def form_valid(self, form):
        return super().form_valid(form)

class CurveDeleteView(generic.DeleteView):
    template_name = 'forecast/curve_delete.html'

    def get_context_data(self, **kwargs):
        context = super(CurveDeleteView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user': get_user_info(self),}
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Curve, pk = pk_)

    def get_success_url(self):
        return reverse('curve-list')


class FlowmeterView(generic.ListView):
    template_name = 'forecast/flowmeters.html'
    context_object_name = 'set_flowmeter'

    def get_context_data(self, **kwargs):
        context = super(FlowmeterView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info(),'user': get_user_info(self) }
        return context

    def get_queryset(self):
        """
        Get all flowmeters
        """
        return Flowmeter.objects.all()

class FlowmeterDetailView(generic.DetailView):
    template_name = 'forecast/flowmeter_detail.html'

    def get_context_data(self, **kwargs):
        context = super(FlowmeterDetailView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info(),'user': get_user_info(self), }
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Flowmeter, pk = pk_)

class FlowmeterCreateView(generic.CreateView):
    model = Flowmeter
    form_class = FlowmeterForm
    template_name = 'forecast/flowmeter_form.html'
    queryset = Flowmeter.objects.all()

    def get_context_data(self, **kwargs):
        context = super(FlowmeterCreateView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user': get_user_info(self),}
        return context

    def form_valid(self, form):
        return super().form_valid(form)

class FlowmeterUpdateView(generic.UpdateView):
    model = Flowmeter
    form_class = FlowmeterForm
    template_name = 'forecast/flowmeter_form.html'
    queryset = Flowmeter.objects.all()

    def get_context_data(self, **kwargs):
        context = super(FlowmeterUpdateView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info(),'user': get_user_info(self), }
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Flowmeter, pk = pk_)

    def form_valid(self, form):
        return super().form_valid(form)

class FlowmeterDeleteView(generic.DeleteView):
    template_name = 'forecast/flowmeter_delete.html'

    def get_context_data(self, **kwargs):
        context = super(FlowmeterDeleteView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user': get_user_info(self),}
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Flowmeter, pk = pk_)

    def get_success_url(self):
        return reverse('flowmeter-list')


class SignalView(generic.ListView):
    template_name = 'forecast/signals.html'
    context_object_name = 'set_signal'

    def get_context_data(self, **kwargs):
        context = super(SignalView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user': get_user_info(self),}
        return context

    def get_queryset(self):
        """
        Get all signals
        """
        return Signal.objects.all()

class SignalCreateView(generic.CreateView):
    model = Signal
    form_class = SignalForm
    template_name = 'forecast/signal_form.html'
    queryset = Signal.objects.all()

    def get_context_data(self, **kwargs):
        context = super(SignalCreateView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info(),'user': get_user_info(self), }
        return context

    def form_valid(self, form):
        return super().form_valid(form)

class SignalDetailView(generic.DetailView):
    template_name = 'forecast/signal_detail.html'

    def get_context_data(self, **kwargs):
        context = super(SignalDetailView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info(),'user': get_user_info(self), }
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Signal, pk = pk_)

class SignalUpdateView(generic.UpdateView):
    model = Signal
    form_class = SignalForm
    template_name = 'forecast/signal_form.html'
    queryset = Signal.objects.all()

    def get_context_data(self, **kwargs):
        context = super(SignalUpdateView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info(),'user': get_user_info(self), }
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Signal, pk = pk_)

    def form_valid(self, form):
        return super().form_valid(form)

class SignalDeleteView(generic.DeleteView):
    template_name = 'forecast/signal_delete.html'

    def get_context_data(self, **kwargs):
        context = super(SignalDeleteView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info(),'user': get_user_info(self), }
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Signal, pk = pk_)

    def get_success_url(self):
        return reverse('signal-list')


class LectureView(generic.ListView):
    template_name = 'forecast/lecture.html'
    context_object_name = 'set_lecture'

    def get_context_data(self, **kwargs):
        context = super(LectureView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info(),'user': get_user_info(self), }
        return context

    def get_queryset(self):
        """
        Get all lecture from the las 24 hours
        """
        from_date = timezone.now().replace(second=0,microsecond=0)

        return Lecture.objects.all().filter(
                                                sample_datetime__lte = from_date + timedelta(minutes= 30), 
                                                sample_datetime__gte =from_date-timedelta(hours=24)
                                            ).order_by('-sample_datetime')

class ConsumeView(generic.ListView):

    template_name = 'forecast/consume.html'
    context_object_name = 'response'

    def get_queryset(self):
        from_date = timezone.now().replace(second=0,microsecond=0)
        return   {
                  'user': get_user_info(self),
                  'set_consumo': Consume.objects.all().filter(
                                                sample_datetime__lte = from_date + timedelta(minutes= 30), 
                                                sample_datetime__gte =from_date-timedelta(hours=24)
                                            ).order_by('-sample_datetime'),  
                  'warnings': get_warnings_info(),
                  }

class ConsumeDetailView(generic.DetailView):
    template_name = 'forecast/consume_detail.html'

    def get_context_data(self, **kwargs):
        context = super(ConsumeDetailView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user':get_user_info(self),}
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return  get_object_or_404(Consume, pk = pk_)

class ConsumeCreateView(generic.CreateView):
    model = Consume
    form_class = ConsumeForm
    template_name = 'forecast/consume_form.html'

    def get_context_data(self, **kwargs):
        context = super(ConsumeCreateView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user': get_user_info(self),}
        return context

    def form_valid(self, form):
        return super().form_valid(form)

class ConsumeUpdateView(generic.UpdateView):
    model = Consume
    form_class = ConsumeForm
    template_name = 'forecast/consume_form.html'
    queryset = Consume.objects.all()

    def get_context_data(self, **kwargs):
        context = super(ConsumeUpdateView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user': get_user_info(self),}
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Consume, pk = pk_)

    def form_valid(self, form):
        return super().form_valid(form)

class ConsumeDeleteView(generic.DeleteView):
    template_name = 'forecast/consume_delete.html'

    def get_context_data(self, **kwargs):
        context = super(ConsumeDeleteView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user': get_user_info(self),}
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Consume, pk = pk_)

    def get_success_url(self):
        return reverse('consume-list')



class ModelMlView(generic.ListView):
    template_name = 'forecast/models.html'
    context_object_name = 'set_models'

    def get_context_data(self, **kwargs):
        context = super(ModelMlView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user': get_user_info(self),}
        return context

    def get_queryset(self):
        """
        Get all models
        """
        return { 'title': 'Modelos','models': ModelMl.objects.all() }


class WarningView(generic.ListView):
    template_name = 'forecast/warnings.html'
    context_object_name = 'set_warnings'

    def get_context_data(self, **kwargs):
        context = super(WarningView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info() ,'user':get_user_info(self),}
        return context

    def get_queryset(self):
        """
        Get all warnings 24 h
        """
        from_date = timezone.now()#.replace(hour=0,minute=0,second=0,microsecond=0)

        limit_warnings = Warning.objects.filter(
            sample_datetime__lte = from_date, 
            sample_datetime__gte =from_date-timedelta(hours=24)
        ).order_by('-sample_datetime')
    
        return { 'title': 'Advertencias','user': get_user_info(self),
        'warnings': limit_warnings}

class WarningDetailView(generic.DetailView):
    template_name = 'forecast/warning_detail.html'

    def get_context_data(self, **kwargs):
        context = super(WarningDetailView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info(),'user': get_user_info(self), }
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Warning, pk = pk_)

class WarningDeleteView(generic.DeleteView):
    template_name = 'forecast/warning_delete.html'

    def get_context_data(self, **kwargs):
        context = super(WarningDeleteView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info(),'user': get_user_info(self), }
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Warning, pk = pk_)

    def get_success_url(self):
        return reverse('warning-list')

class WarningUpdateView(generic.UpdateView):
    model = Warning
    form_class = WarningForm
    template_name = 'forecast/warning_form.html'
    queryset = Warning.objects.all()

    def get_context_data(self, **kwargs):
        context = super(WarningUpdateView, self).get_context_data(**kwargs)
        context['response'] = {'warnings': get_warnings_info(),'user': get_user_info(self) }
        return context

    def get_object(self):
        pk_ = self.kwargs.get("pk")
        return get_object_or_404(Warning, pk = pk_)

    def form_valid(self, form):
        return super().form_valid(form)



class ChartData(APIView):
    """
    Data for forecast/cosume Chart.

    * Requires token authentication.
    * Only admin users are able to access this view.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request, format=None):

        from_date = timezone.now().replace(second=0,microsecond=0)
   
        ajaxid = request.GET['ajaxid'] if request.GET.get('ajaxid')  else 1
        """ FOR GRAPH"""

        # datos de la tabla forecast ( predicción del consumo)
        forecast_set= Forecast.objects.filter(
            fk_curve = ajaxid,
            sample_datetime__lte = from_date + timedelta(minutes= 30), 
            sample_datetime__gte =from_date-timedelta(hours=24)).order_by('-sample_datetime')

        # datos de la tabla consume ( consumo real )
        consume_set= Consume.objects.filter(
            fk_curve = ajaxid,
            sample_datetime__lte = from_date,
            sample_datetime__gte = from_date - timedelta(hours=24)
        ).order_by('-sample_datetime')

        # preparación de la eje X del grafico
        labels =  [register.sample_datetime.isoformat() for register in forecast_set ]
        data_forecast = [round(register.sample_value,2) for register in forecast_set ]
        data_consume = [ { 'x': register.sample_datetime.isoformat(), 'y': round(register.sample_value,2) } for register in consume_set]

        # leer el limite de la curva
        curve = get_object_or_404(Curve, pk=ajaxid)
        data_limit = [ { 'x': register.sample_datetime.isoformat(), 'y': round(register.sample_value,2)+curve.limit } for register in forecast_set]
        

        # preparacion de los datos para la tabla
         
        # fechas disponibles
        dates_consume_set = [ i.sample_datetime for i in consume_set]
     
        dates_forecast_set = [ i.sample_datetime for i in forecast_set]
    
        all_dates = list(set(dates_consume_set+dates_forecast_set))
        all_dates.sort(reverse = True)
        
        def find_value(dateTime,data_set):
            object_final = data_set.filter(sample_datetime = dateTime)
            valor_final = round(object_final[0].sample_value,2) if object_final else "-"
            return valor_final
        
        def get_diff(dateTime,forecast_set,consume_set):
            consume_value = find_value(dateTime,consume_set)
            forecast_value = find_value(dateTime,forecast_set)
            if consume_value =="-" or forecast_value =="-":
                return "-"
            else: 
                return round(forecast_value -consume_value ,2 )

        forecast_table_values = [ find_value(dateTime,forecast_set) for dateTime in all_dates]
        consume_table_values = [ find_value(dateTime,consume_set) for dateTime in all_dates]
        diff_table_values = [get_diff(_,forecast_set,consume_set) for _ in all_dates ]

        data_table =  [  [
                            i+1, # Nº
                            curve.name, # Curva
                            timezone.localtime(all_dates[i], pytz.timezone('Europe/Madrid')).strftime("%Y-%m-%d %H:%M"), # Datetime 
                            forecast_table_values[i], # Caudal Predicción- Red Neuronal
                            consume_table_values[i], # Caudal Real
                            diff_table_values[i] # Diferencia
                        ]
                         for i in range(len(all_dates))
                    ]
  
        """DATA TO SEND """
        data = {
            "labels": labels,
            'user': get_user_info(self),
            "default": {
                "id": [i+i for i in range(len(consume_set))],
                "data_forecast": data_forecast,
                "data_consume": data_consume,
                "data_limit": data_limit,
                "data_table": data_table,
            },
        }

        return Response(data)

