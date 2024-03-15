from django.db import models

class Imagen(models.Model):
    imagen = models.ImageField(upload_to='images/')

class Diseño(models.Model):
    nombre = models.CharField(max_length=50)
    descripccion = models.CharField(max_length=120, blank=True)
    imagen_principal = models.ImageField(upload_to='images/',blank=True, null=True)
    imagenes_adicionales = models.ManyToManyField(Imagen, related_name='imagenes_adicionales_de', blank=True)
    
    def __str__(self):
        return self.nombre



