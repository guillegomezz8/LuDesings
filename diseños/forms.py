from django import forms
from .models import Diseño

class DiseñoForm(forms.ModelForm):
    class Meta:
        model = Diseño
        fields = ['nombre', 'descripccion', 'imagen_principal', 'imagenes_adicionales']
