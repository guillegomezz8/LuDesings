from django.contrib import admin
from .models import PerfilCliente


@admin.register(PerfilCliente)
class PerfilClienteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'telefono', 'ciudad', 'codigo_postal', 'fecha_creacion')
    search_fields = ('usuario__username', 'usuario__email', 'telefono', 'direccion', 'ciudad', 'codigo_postal')
    readonly_fields = ('fecha_creacion',)
    fieldsets = (
        ('Usuario', {
            'fields': ('usuario',)
        }),
        ('Contacto y entrega', {
            'fields': ('telefono', 'direccion', 'ciudad', 'codigo_postal')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion',)
        }),
    )
