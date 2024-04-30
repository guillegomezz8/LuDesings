from django import forms
from .models import Peticion

class PeticionesForm(forms.ModelForm):
    
    class Meta:
        model = Peticion
        fields = ['asunto','email','peticion']
        labels = {
            'asunto': 'Asunto',
            'email': 'Correo Electronico',
            'peticion': 'Peticion'
        }
        widgets = {
            'asunto': forms.TextInput(attrs={'class': 'form-control form-control-lg ', 'placeholder': 'Introduce el asunto'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce el correo electronico'}),
            'peticion': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce la peticion'}),
        }
