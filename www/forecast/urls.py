from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # table and chart data to load by AJAX
    path('chart/data/',views.ChartData.as_view(), name='getdata_json'),

    # : /prediccion/
    path('', views.IndexView.as_view(), name ='forecast'),
    path('prediccion/', views.IndexView.as_view(), name ='forecast'),
    path('prediccion/<int:pk>/', views.ForecastDetailView.as_view(), name ='forecast'),

    # : /curvas/
    path('curvas/', views.CurvesView.as_view(), name='curve-list'),
    path('curvas/crear/', views.CurveCreateView.as_view(),name='curve-create'),
    path('curvas/<int:pk>/', views.CurveDetailView.as_view(), name='curve-detail'),
    path('curvas/<int:pk>/actualizar/', views.CurveUpdateView.as_view(), name='curve-update'),
    path('curvas/<int:pk>/borrar/', views.CurveDeleteView.as_view(), name='curve-delete'),
    
    # : /caudalimetros/
    path('caudalimetros/', views.FlowmeterView.as_view(), name='flowmeter-list'),
    path('caudalimetros/crear/', views.FlowmeterCreateView.as_view(),name='flowmeter-create'),
    path('caudalimetros/<int:pk>/', views.FlowmeterDetailView.as_view(), name='flowmeter-detail'),
    path('caudalimetros/<int:pk>/actualizar/', views.FlowmeterUpdateView.as_view(), name='flowmeter-update'),
    path('caudalimetros/<int:pk>/borrar/', views.FlowmeterDeleteView.as_view(), name='flowmeter-delete'),

    # : /senales/
    path('senales/', views.SignalView.as_view(), name='signal-list'),
    path('senales/crear/', views.SignalCreateView.as_view(),name='signal-create'),
    path('senales/<int:pk>/', views.SignalDetailView.as_view(), name='signal-detail'),
    path('senales/<int:pk>/actualizar/', views.SignalUpdateView.as_view(), name='signal-update'),
    path('senales/<int:pk>/borrar/', views.SignalDeleteView.as_view(), name='signal-delete'),
    
    # : /lectura/
    path('lectura/', views.LectureView.as_view(), name='lecture'),

    # : /consumo/
    path('consumo/', views.ConsumeView.as_view(), name='consume-list'),
    path('consumo/crear/', views.ConsumeCreateView.as_view(),name='consume-create'),
    path('consumo/<int:pk>/', views.ConsumeDetailView.as_view(), name='consume-detail'),
    path('consumo/<int:pk>/actualizar/', views.ConsumeUpdateView.as_view(), name='consume-update'),
    path('consumo/<int:pk>/borrar/', views.ConsumeDeleteView.as_view(), name='consume-delete'),

    # : /modelos/
    path('modelos/', views.ModelMlView.as_view(), name='models'),
    
    # : /avisos/
    path('avisos/', views.WarningView.as_view(), name='warning-list'),
    path('avisos/<int:pk>/', views.WarningDetailView.as_view(), name='warning-detail'),
    path('avisos/<int:pk>/actualizar/', views.WarningUpdateView.as_view(), name='warning-update'),
    path('avisos/<int:pk>/borrar/', views.WarningDeleteView.as_view(), name='warning-delete'),

    path('logout/',views.logout, name="logout"),
    path('signout-callback-oidc/',views.IndexView.as_view(), name ='forecast'),

    # handle favico error
    path('favicon.ico',RedirectView.as_view(url='/static/images/favicon.png')),
]



