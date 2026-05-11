from django.contrib import admin
from django.utils import timezone
from .models import DisenoLike, Diseño, Imagen, LineaPedido, Pedido, StockTalla

admin.site.site_header = 'LuJapon | Administración'
admin.site.site_title = 'LuJapon Admin'
admin.site.index_title = 'Panel de gestión'


class StockTallaInline(admin.TabularInline):
    model = StockTalla
    extra = 1
    fields = ('talla', 'stock', 'disponible')
    show_change_link = True


class LineaPedidoInline(admin.TabularInline):
    model = LineaPedido
    extra = 0
    can_delete = False
    readonly_fields = ('diseño', 'nombre_producto', 'talla', 'cantidad', 'precio_unitario', 'subtotal')
    fields = ('diseño', 'nombre_producto', 'talla', 'cantidad', 'precio_unitario', 'subtotal')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Diseño)
class DiseñoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'modo_stock_admin', 'stock_total_admin', 'disponible', 'fecha_subida')
    list_editable = ('disponible',)
    list_filter = ('categoria', 'disponible', 'fecha_subida')
    search_fields = ('nombre', 'descripccion')
    filter_horizontal = ('imagenes_adicionales',)
    inlines = (StockTallaInline,)
    date_hierarchy = 'fecha_subida'
    list_per_page = 25
    fieldsets = (
        ('Información principal', {
            'fields': ('nombre', 'descripccion', 'categoria', 'precio', 'talla')
        }),
        ('Venta y stock', {
            'fields': ('stock', 'disponible', 'stock_total_admin', 'popularidad')
        }),
        ('Imágenes', {
            'fields': ('imagen_principal', 'imagenes_adicionales')
        }),
        ('Fechas', {
            'fields': ('fecha_subida',)
        }),
    )
    readonly_fields = ('fecha_subida', 'popularidad', 'stock_total_admin')

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('stocks_talla')

    @admin.display(description='Tallaje')
    def modo_stock_admin(self, obj):
        return 'Varias tallas' if obj.tiene_stock_por_talla else 'Talla única'

    @admin.display(description='Stock total')
    def stock_total_admin(self, obj):
        return obj.stock_total


@admin.register(Imagen)
class ImagenAdmin(admin.ModelAdmin):
    list_display = ('imagen', 'diseño')
    search_fields = ('imagen',)


@admin.register(StockTalla)
class StockTallaAdmin(admin.ModelAdmin):
    list_display = ('diseño', 'talla', 'stock', 'disponible')
    list_filter = ('disponible', 'talla')
    search_fields = ('diseño__nombre', 'talla')
    list_select_related = ('diseño',)


@admin.register(DisenoLike)
class DisenoLikeAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'diseño', 'creado')
    list_filter = ('creado',)
    search_fields = ('usuario__username', 'diseño__nombre')
    readonly_fields = ('creado',)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre_cliente', 'email', 'estado', 'estado_pago', 'total', 'fecha_creacion')
    list_filter = ('estado', 'estado_pago', 'fecha_creacion')
    search_fields = ('nombre_cliente', 'email', 'telefono', 'direccion', 'stripe_checkout_session_id', 'stripe_payment_intent_id')
    date_hierarchy = 'fecha_creacion'
    list_per_page = 25
    list_select_related = ('usuario',)
    actions = ('marcar_como_preparando', 'marcar_como_enviado', 'marcar_como_completado')
    readonly_fields = (
        'total',
        'stripe_checkout_session_id',
        'stripe_payment_intent_id',
        'access_token',
        'fecha_pago',
        'fecha_creacion',
        'fecha_actualizacion',
    )
    inlines = (LineaPedidoInline,)
    fieldsets = (
        ('Cliente', {
            'fields': ('usuario', 'nombre_cliente', 'email', 'telefono')
        }),
        ('Entrega', {
            'fields': ('direccion', 'ciudad', 'codigo_postal', 'notas')
        }),
        ('Estado', {
            'fields': ('estado', 'estado_pago', 'total')
        }),
        ('Stripe y acceso', {
            'fields': ('stripe_checkout_session_id', 'stripe_payment_intent_id', 'access_token')
        }),
        ('Fechas', {
            'fields': ('fecha_pago', 'fecha_creacion', 'fecha_actualizacion')
        }),
    )

    def _actualizar_estado_pagados(self, request, queryset, estado, etiqueta):
        actualizados = queryset.filter(estado_pago='pagado').update(
            estado=estado,
            fecha_actualizacion=timezone.now(),
        )
        self.message_user(request, f'{actualizados} pedidos pagados marcados como {etiqueta}.')

    @admin.action(description='Marcar pedidos pagados como preparando')
    def marcar_como_preparando(self, request, queryset):
        self._actualizar_estado_pagados(request, queryset, 'preparando', 'preparando')

    @admin.action(description='Marcar pedidos pagados como enviados')
    def marcar_como_enviado(self, request, queryset):
        self._actualizar_estado_pagados(request, queryset, 'enviado', 'enviados')

    @admin.action(description='Marcar pedidos pagados como completados')
    def marcar_como_completado(self, request, queryset):
        self._actualizar_estado_pagados(request, queryset, 'completado', 'completados')


@admin.register(LineaPedido)
class LineaPedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'nombre_producto', 'talla', 'cantidad', 'precio_unitario', 'subtotal')
    list_filter = ('talla',)
    search_fields = ('nombre_producto', 'pedido__nombre_cliente', 'pedido__email')
    readonly_fields = ('pedido', 'diseño', 'nombre_producto', 'talla', 'cantidad', 'precio_unitario', 'subtotal')
    list_select_related = ('pedido', 'diseño')
