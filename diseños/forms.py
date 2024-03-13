from django import forms
from .models import Diseño

class DiseñoForm(forms.ModelForm):
    class Meta:
        model = Diseño
        fields = ['nombre', 'descripccion', 'imagen_principal', 'imagenes_adicionales']
        labels = {
            'nombre': 'Nombre:',
            'descripccion': 'Descripción:',
            'imagen_principal': 'Imagen principal:',
            'imagenes_adicionales': 'Imágenes adicionales:'
        }
        label_suffix = ''
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control form-control-lg ', 'placeholder': 'Introduce el nombre'}),
            'descripccion': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce la descripción'}),
            'imagen_principal': forms.FileInput(attrs={'class': 'form-control form-control-lg', 'accept': 'image/*'}),
            'imagenes_adicionales': forms.ClearableFileInput(attrs={'class': 'form-control form-control-lg', 'multiple': True, 'accept': 'image/*'}),
        }
