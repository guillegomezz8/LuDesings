from django.db import models

# Create your models here.
class Peticion(models.Model):
    
    asunto = models.TextField(max_length=30)
    email = models.EmailField()
    peticion = models.TextField(max_length=500)

    def __str__(self):
        return self.asunto