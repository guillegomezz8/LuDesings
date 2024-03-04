from django.db import models

class Imagen(models.Model):
    image = models.ImageField(upload_to='images/')

class Diseño(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=120)
    imagen_principal = models.OneToOneField(Imagen, on_delete=models.CASCADE, related_name='imagen_principal_de',blank=True)
    imagenes_adicionales = models.ManyToManyField(Imagen, related_name='imagenes_adicionales_de')




