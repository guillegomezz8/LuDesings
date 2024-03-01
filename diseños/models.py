from django.db import models

# Create your models here.
class Imagen(models.Model):
    image = models.ImageField(upload_to='images/')

class Diseño(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=120)
    imagenes = models.ManyToManyField(Imagen)