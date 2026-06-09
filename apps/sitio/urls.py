from django.urls import path

from . import views

urlpatterns = [
    path('', views.sobreMi, name='sobreMi'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blog_detalle, name='blog_detalle'),
    path('diseno-a-medida/', views.peticionesForm, name='diseño_a_medida'),
    path('peticiones/', views.peticionesForm, name='peticionesForm'),
]

