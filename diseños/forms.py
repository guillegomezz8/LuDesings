from django import forms
from .models import Diseño

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class DiseñoForm(forms.ModelForm):
    imagenes_adicionales = MultipleFileField(required=False)  # Asigna el campo con el nuevo widget

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
            # Ahora usamos el nuevo widget MultipleFileInput
            'imagenes_adicionales': MultipleFileInput(attrs={'class': 'form-control form-control-lg', 'accept': 'image/*'}),
        }
