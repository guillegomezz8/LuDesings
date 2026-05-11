from django.conf import settings
from django.db import models

class PerfilCliente(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name='usuario', related_name='perfil_cliente', on_delete=models.CASCADE)
    telefono = models.CharField('teléfono', max_length=20, blank=True)
    direccion = models.CharField('dirección', max_length=150, blank=True)
    ciudad = models.CharField('ciudad', max_length=80, blank=True)
    codigo_postal = models.CharField('código postal', max_length=12, blank=True)
    fecha_creacion = models.DateTimeField('fecha de creación', auto_now_add=True)

    class Meta:
        verbose_name = 'perfil de cliente'
        verbose_name_plural = 'perfiles de cliente'

    def __str__(self):
        return f'Perfil de {self.usuario.username}'


