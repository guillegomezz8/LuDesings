from django.contrib import admin
from django.urls import path
from .views import *


urlpatterns = [
    path('', diseños, name='diseños'),
    path('crear/', crear_diseño, name='crear'),
    path('borrar_diseño/<int:pk>/', borrar_diseño, name='borrar_diseño'),
    path('editar_diseño/<int:pk>/', editar_diseño, name='editar_diseño'),
    path('<int:pk>/', detalle_diseño, name='detalle_diseño')
]