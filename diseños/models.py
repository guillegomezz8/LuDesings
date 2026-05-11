import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

class Diseño(models.Model):
    CATEGORIAS = [
        ('prenda', 'Prenda'),
        ('vestido', 'Vestido'),
        ('traje', 'Traje'),
        ('camiseta', 'Camiseta'),
        ('a_medida', 'A medida'),
    ]

    nombre = models.CharField('nombre', max_length=50)
    descripccion = models.CharField('descripción', max_length=120, blank=True)
    imagen_principal = models.ImageField('imagen principal', upload_to='images/',blank=True, null=True)
    imagenes_adicionales = models.ManyToManyField('Imagen', verbose_name='imágenes adicionales', related_name='imagenes_adicionales_de', blank=True)
    fecha_subida = models.DateTimeField('fecha de subida', default=timezone.now)
    popularidad = models.IntegerField('popularidad', default=0)
    categoria = models.CharField('categoría', max_length=30, choices=CATEGORIAS, default='prenda')
    precio = models.DecimalField('precio', max_digits=8, decimal_places=2, default=49.99)
    talla = models.CharField('talla', max_length=30, blank=True)
    stock = models.PositiveIntegerField('stock', default=1)
    disponible = models.BooleanField('disponible', default=True)

    class Meta:
        ordering = ['-fecha_subida']
        verbose_name = 'diseño'
        verbose_name_plural = 'diseños'
    
    def __str__(self):
        return self.nombre

    def todas_las_imagenes(self):
        imagenes = []
        if self.imagen_principal:
            imagenes.append(self.imagen_principal)
        imagenes.extend([imagen.imagen for imagen in self.imagenes_adicionales.all()])
        return imagenes

    @property
    def tiene_stock_por_talla(self):
        stocks_prefetch = getattr(self, '_prefetched_objects_cache', {}).get('stocks_talla')
        if stocks_prefetch is not None:
            return bool(stocks_prefetch)
        return self.stocks_talla.exists()

    @property
    def stock_total(self):
        stocks_prefetch = getattr(self, '_prefetched_objects_cache', {}).get('stocks_talla')
        if stocks_prefetch is not None:
            total = sum(stock.stock for stock in stocks_prefetch if stock.disponible)
            return total if stocks_prefetch else self.stock

        if self.tiene_stock_por_talla:
            return sum(stock.stock for stock in self.stocks_talla.filter(disponible=True))
        return self.stock

    @property
    def esta_disponible(self):
        return self.disponible and self.stock_total > 0


class StockTalla(models.Model):
    diseño = models.ForeignKey(Diseño, verbose_name='diseño', related_name='stocks_talla', on_delete=models.CASCADE)
    talla = models.CharField('talla', max_length=30)
    stock = models.PositiveIntegerField('stock', default=0)
    disponible = models.BooleanField('disponible', default=True)

    class Meta:
        ordering = ['talla']
        verbose_name = 'stock por talla'
        verbose_name_plural = 'stock por talla'
        constraints = [
            models.UniqueConstraint(fields=['diseño', 'talla'], name='stock_unico_por_diseno_talla')
        ]

    def __str__(self):
        return f'{self.diseño} - {self.talla}: {self.stock}'
    
class Imagen(models.Model):
    imagen = models.ImageField('imagen', upload_to='images/')
    diseño = models.ForeignKey(Diseño, verbose_name='diseño', related_name='diseño_imagenes', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = 'imagen'
        verbose_name_plural = 'imágenes'

    def __str__(self):
        return self.imagen.url

class DisenoLike(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='usuario', related_name='likes_disenos', on_delete=models.CASCADE)
    diseño = models.ForeignKey(Diseño, verbose_name='diseño', related_name='likes', on_delete=models.CASCADE)
    creado = models.DateTimeField('fecha de creación', auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'diseño'], name='like_unico_por_usuario_diseno')
        ]
        ordering = ['-creado']
        verbose_name = 'favorito'
        verbose_name_plural = 'favoritos'

    def __str__(self):
        return f'{self.usuario} - {self.diseño}'

class Pedido(models.Model):
    ESTADOS = [
        ('pendiente_pago', 'Pendiente de pago'),
        ('confirmado', 'Confirmado'),
        ('preparando', 'Preparando'),
        ('enviado', 'Enviado'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
        ('incidencia', 'Incidencia'),
    ]
    ESTADOS_PAGO = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('fallido', 'Fallido'),
        ('reembolsado', 'Reembolsado'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='usuario registrado', related_name='pedidos', on_delete=models.SET_NULL, null=True, blank=True)
    nombre_cliente = models.CharField('nombre del cliente', max_length=100)
    email = models.EmailField('correo electrónico')
    telefono = models.CharField('teléfono', max_length=20, blank=True)
    direccion = models.CharField('dirección', max_length=150)
    ciudad = models.CharField('ciudad', max_length=80)
    codigo_postal = models.CharField('código postal', max_length=12)
    notas = models.TextField('notas del pedido', max_length=500, blank=True)
    estado = models.CharField('estado del pedido', max_length=20, choices=ESTADOS, default='pendiente_pago')
    estado_pago = models.CharField('estado del pago', max_length=20, choices=ESTADOS_PAGO, default='pendiente')
    total = models.DecimalField('total', max_digits=10, decimal_places=2, default=0)
    stripe_checkout_session_id = models.CharField('ID de sesión de Stripe', max_length=255, blank=True, null=True, unique=True)
    stripe_payment_intent_id = models.CharField('ID de pago de Stripe', max_length=255, blank=True)
    access_token = models.UUIDField('token de acceso', default=uuid.uuid4, editable=False, unique=True)
    fecha_pago = models.DateTimeField('fecha de pago', null=True, blank=True)
    fecha_creacion = models.DateTimeField('fecha de creación', auto_now_add=True)
    fecha_actualizacion = models.DateTimeField('última actualización', auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'pedido'
        verbose_name_plural = 'pedidos'

    def __str__(self):
        return f'Pedido #{self.pk} - {self.nombre_cliente}'

class LineaPedido(models.Model):
    pedido = models.ForeignKey(Pedido, verbose_name='pedido', related_name='lineas', on_delete=models.CASCADE)
    diseño = models.ForeignKey(Diseño, verbose_name='diseño', related_name='lineas_pedido', on_delete=models.SET_NULL, null=True, blank=True)
    nombre_producto = models.CharField('nombre del producto', max_length=80)
    talla = models.CharField('talla', max_length=30, blank=True)
    cantidad = models.PositiveIntegerField('cantidad', default=1)
    precio_unitario = models.DecimalField('precio unitario', max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = 'línea de pedido'
        verbose_name_plural = 'líneas de pedido'

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f'{self.nombre_producto} x {self.cantidad}'

