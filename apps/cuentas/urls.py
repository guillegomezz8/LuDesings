from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.custom_login, name='login'),
    path('registro/', views.registro, name='registro'),
    path('cuenta/', views.cuenta, name='cuenta'),
    path('pedidos/', views.pedidos_usuario, name='pedidos_usuario'),
    path('logout/', views.logout_view, name='logout'),
]
