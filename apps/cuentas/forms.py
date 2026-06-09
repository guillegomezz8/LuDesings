from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import PerfilCliente


class RegistroUsuarioForm(UserCreationForm):
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce tu correo electrónico'})
    )
    first_name = forms.CharField(
        label='Nombre',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce tu nombre'})
    )
    telefono = forms.CharField(
        label='Teléfono',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce tu teléfono'})
    )
    direccion = forms.CharField(
        label='Dirección',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce tu dirección'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'email', 'password1', 'password2']
        labels = {
            'username': 'Usuario',
            'password1': 'Contraseña',
            'password2': 'Repite la contraseña',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce tu usuario'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Repite la contraseña'
        self.fields['password1'].widget.attrs.update({'class': 'form-control form-control-lg', 'placeholder': 'Introduce tu contraseña'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control form-control-lg', 'placeholder': 'Repite tu contraseña'})
        self.fields['username'].help_text = ''
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return email


class PerfilClienteForm(forms.ModelForm):
    class Meta:
        model = PerfilCliente
        fields = ['telefono', 'direccion', 'ciudad', 'codigo_postal']
        labels = {
            'telefono': 'Teléfono',
            'direccion': 'Dirección',
            'ciudad': 'Ciudad',
            'codigo_postal': 'Código postal',
        }
        widgets = {
            'telefono': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce tu teléfono'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce tu dirección'}),
            'ciudad': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce tu ciudad'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Introduce tu código postal'}),
        }
