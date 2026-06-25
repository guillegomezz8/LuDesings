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
            'nombre_cliente': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': '¿Cómo te llamas?', 'autocomplete': 'name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'nombre@correo.com', 'autocomplete': 'email'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Número de contacto', 'autocomplete': 'tel'}),
            'tipo_prenda': forms.Select(attrs={'class': 'form-control form-control-lg'}),
            'talla_aproximada': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Ej. M, 38 o todavía no lo sé'}),
            'presupuesto': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Cantidad aproximada en euros', 'step': '0.01', 'min': '0'}),
            'fecha_evento': forms.DateInput(attrs={'class': 'form-control form-control-lg', 'type': 'date'}),
            'asunto': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Ej. vestido para una boda de tarde'}),
            'peticion': forms.Textarea(attrs={'class': 'form-control form-control-lg', 'rows': 5, 'placeholder': 'Háblanos de colores, estilo, ocasión, referencias, ajustes o cualquier detalle importante'}),
        }
