from django.contrib import admin
from django.urls import path
from . import views


urlpatterns = [
    path('', views.diseños, name='diseños'),
    path('crear/', views.crear_diseño, name='crear')
]