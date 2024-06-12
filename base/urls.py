from django.contrib import admin
from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', views.sobreMi, name='sobreMi'),
    path('peticiones/', views.peticionesForm, name='peticionesForm'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('peticion/{$id}', views.peticionesDetalles, name ='peticionesDetalles')
]

urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)

