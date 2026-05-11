from django import forms
from .models import Peticion

class PeticionesForm(forms.ModelForm):
    
    class Meta:
        model = Peticion
        fields = [
            'nombre_cliente',
            'email',
            'telefono',
            'tipo_prenda',
            'talla_aproximada',
            'presupuesto',
            'fecha_evento',
            'asunto',
            'peticion',
        ]
        labels = {
            'nombre_cliente': 'Nombre',
            'email': 'Correo electrónico',
            'telefono': 'Teléfono',
            'tipo_prenda': 'Tipo de prenda',
            'talla_aproximada': 'Talla aproximada',
            'presupuesto': 'Presupuesto orientativo',
            'fecha_evento': 'Fecha del evento',
            'asunto': 'Idea principal',
            'peticion': 'Detalles del diseño'
        }
        widgets = {
            'nombre_cliente': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Tu nombre'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce el correo electrónico'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Teléfono de contacto'}),
            'tipo_prenda': forms.Select(attrs={'class': 'form-control form-control-lg'}),
            'talla_aproximada': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Ej: S, M, L, 38, a medida...'}),
            'presupuesto': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Presupuesto aproximado', 'step': '0.01', 'min': '0'}),
            'fecha_evento': forms.DateInput(attrs={'class': 'form-control form-control-lg', 'type': 'date'}),
            'asunto': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Ej: vestido para feria, traje para gala...'}),
            'peticion': forms.Textarea(attrs={'class': 'form-control form-control-lg', 'rows': 5, 'placeholder': 'Cuéntanos colores, estilo, ocasión, medidas, referencias o cualquier detalle importante'}),
        }
