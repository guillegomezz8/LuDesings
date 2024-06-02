from django import forms
from .models import Diseño

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        default_attrs = {'class': 'form-control form-control-lg', 'multiple': True, 'accept': 'image/*'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result

class DiseñoForm(forms.ModelForm):
    imagenes_adicionales = MultipleFileField(required=False)

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
            'nombre': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce el nombre'}),
            'descripccion': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce la descripción'}),
            'imagen_principal': forms.FileInput(attrs={'class': 'form-control form-control-lg', 'accept': 'image/*'}),
            'imagenes_adicionales': MultipleFileInput(attrs={'class': 'form-control form-control-lg', 'multiple': True, 'accept': 'image/*'}),
        }


