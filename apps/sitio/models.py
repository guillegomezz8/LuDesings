from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils import timezone

class Peticion(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('respondida', 'Respondida'),
        ('cerrada', 'Cerrada'),
    ]
    TIPOS_PRENDA = [
        ('vestido', 'Vestido'),
        ('traje', 'Traje'),
        ('camiseta', 'Camiseta'),
        ('conjunto', 'Conjunto'),
        ('otro', 'Otro'),
    ]
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='usuario registrado', related_name='peticiones', on_delete=models.SET_NULL, null=True, blank=True)
    nombre_cliente = models.CharField('nombre del cliente', max_length=100, blank=True)
    telefono = models.CharField('teléfono', max_length=20, blank=True)
    asunto = models.TextField('idea principal', max_length=60)
    email = models.EmailField('correo electrónico')
    tipo_prenda = models.CharField('tipo de prenda', max_length=30, choices=TIPOS_PRENDA, default='vestido')
    talla_aproximada = models.CharField('talla aproximada', max_length=30, blank=True)
    presupuesto = models.DecimalField('presupuesto orientativo', max_digits=8, decimal_places=2, null=True, blank=True)
    fecha_evento = models.DateField('fecha del evento', null=True, blank=True)
    peticion = models.TextField('detalles del diseño', max_length=500)
    estado = models.CharField('estado', max_length=20, choices=ESTADOS, default='pendiente')
    fecha_creacion = models.DateTimeField('fecha de creación', default=timezone.now)

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'solicitud a medida'
        verbose_name_plural = 'solicitudes a medida'

    def __str__(self):
        return self.asunto

class SobreMiContenido(models.Model):
    titulo = models.CharField('título', max_length=80, default='¿Quién Soy?')
    texto = models.TextField('texto', max_length=2500)
    imagen = models.ImageField('imagen', upload_to='sobre-mi/', blank=True, null=True)
    instagram_url = models.URLField('URL de Instagram', blank=True)
    tiktok_url = models.URLField('URL de TikTok', blank=True)
    twitter_url = models.URLField('URL de Twitter', blank=True)
    actualizado = models.DateTimeField('última actualización', auto_now=True)

    class Meta:
        verbose_name = 'contenido de Sobre mí'
        verbose_name_plural = 'contenido de Sobre mí'

    def __str__(self):
        return self.titulo

class EntradaBlog(models.Model):
    titulo = models.CharField('título', max_length=120)
    slug = models.SlugField('slug', max_length=140, unique=True, blank=True)
    entradilla = models.TextField('entradilla', max_length=300, blank=True)
    contenido = models.TextField('contenido', max_length=4000)
    imagen = models.ImageField('imagen', upload_to='blog/', blank=True, null=True)
    publicado = models.BooleanField('publicado', default=True)
    fecha_publicacion = models.DateTimeField('fecha de publicación', default=timezone.now)
    actualizado = models.DateTimeField('última actualización', auto_now=True)

    class Meta:
        ordering = ['-fecha_publicacion']
        verbose_name = 'Entrada de blog'
        verbose_name_plural = 'Entradas de blog'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.titulo)
            slug = base_slug
            contador = 2
            while EntradaBlog.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{contador}'
                contador += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.titulo
