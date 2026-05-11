from django.contrib import admin
from django.urls import path
from .views import *


urlpatterns = [
    path('', diseños, name='diseños'),
    path('crear/', crear_diseño, name='crear'),
    path('borrar_diseño/<int:pk>/', borrar_diseño, name='borrar_diseño'),
    path('editar_diseño/<int:pk>/', editar_diseño, name='editar_diseño'),
    path('<int:pk>/', detalle_diseño, name='detalle_diseño'),
    path('like/<int:diseno_id>/', like_diseno, name='like_diseno'),
    path('carrito/', carrito, name='carrito'),
    path('carrito/agregar/<int:pk>/', agregar_al_carrito, name='agregar_al_carrito'),
    path('carrito/actualizar/<int:pk>/', actualizar_carrito, name='actualizar_carrito'),
    path('checkout/', checkout, name='checkout'),
    path('stripe/success/', stripe_success, name='stripe_success'),
    path('stripe/cancel/<int:pk>/', stripe_cancel, name='stripe_cancel'),
    path('stripe/webhook/', stripe_webhook, name='stripe_webhook'),
    path('pedido/<int:pk>/', pedido_detalle, name='pedido_detalle'),
    path('pedido/<int:pk>/estado/', actualizar_estado_pedido, name='actualizar_estado_pedido'),
]
