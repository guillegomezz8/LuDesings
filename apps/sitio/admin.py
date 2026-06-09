from django.contrib import admin
from .models import EntradaBlog, Peticion, SobreMiContenido

@admin.register(Peticion)
class PeticionAdmin(admin.ModelAdmin):
    list_display = ('asunto', 'nombre_cliente', 'email', 'tipo_prenda', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'tipo_prenda', 'fecha_creacion')
    search_fields = ('asunto', 'nombre_cliente', 'email', 'peticion')
    readonly_fields = ('fecha_creacion',)
    fieldsets = (
        ('Cliente', {
            'fields': ('usuario', 'nombre_cliente', 'email', 'telefono')
        }),
        ('Diseño solicitado', {
            'fields': ('asunto', 'tipo_prenda', 'talla_aproximada', 'presupuesto', 'fecha_evento', 'peticion')
        }),
        ('Gestión', {
            'fields': ('estado', 'fecha_creacion')
        }),
    )


@admin.register(SobreMiContenido)
class SobreMiContenidoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'actualizado')
    readonly_fields = ('actualizado',)
    fieldsets = (
        ('Contenido', {
            'fields': ('titulo', 'texto', 'imagen')
        }),
        ('Redes sociales', {
            'fields': ('instagram_url', 'tiktok_url', 'twitter_url')
        }),
        ('Fechas', {
            'fields': ('actualizado',)
        }),
    )


@admin.register(EntradaBlog)
class EntradaBlogAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'publicado', 'fecha_publicacion', 'actualizado')
    list_filter = ('publicado', 'fecha_publicacion')
    search_fields = ('titulo', 'entradilla', 'contenido')
    prepopulated_fields = {'slug': ('titulo',)}
    readonly_fields = ('actualizado',)
    fieldsets = (
        ('Entrada', {
            'fields': ('titulo', 'slug', 'entradilla', 'contenido', 'imagen')
        }),
        ('Publicación', {
            'fields': ('publicado', 'fecha_publicacion', 'actualizado')
        }),
    )
