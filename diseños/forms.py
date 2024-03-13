from django import forms
from .models import Diseño, Imagen

class DiseñoForm(forms.ModelForm):
    class Meta:
        model = Diseño
        fields = ['nombre', 'descripccion', 'imagen_principal','imagenes_adicionales']

    imagen_principal = forms.FileField(
        label='Imagen principal',
        widget=forms.FileInput(attrs={'accept': 'image/*'})
    )

    imagenes_adicionales = forms.FileField(
        widget=forms.FileInput(attrs={'multiple': True, 'accept': 'image/*'}),
        label='Imágenes adicionales'
    )