from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import PerfilCliente


class RegistroClienteTests(TestCase):
    def test_registro_crea_usuario_y_perfil_cliente(self):
        response = self.client.post(reverse('registro'), {
            'username': 'cliente',
            'first_name': 'Cliente',
            'email': 'cliente@example.com',
            'telefono': '600000000',
            'direccion': 'Calle Test 1',
            'password1': 'pass12345cliente',
            'password2': 'pass12345cliente',
        })

        self.assertRedirects(response, reverse('cuenta'))
        user = User.objects.get(username='cliente')
        perfil = PerfilCliente.objects.get(usuario=user)
        self.assertEqual(perfil.telefono, '600000000')
        self.assertEqual(perfil.direccion, 'Calle Test 1')

    def test_login_no_redirige_a_url_externa(self):
        User.objects.create_user(username='cliente', password='pass12345')

        response = self.client.post(f"{reverse('login')}?next=https://evil.test", {
            'username': 'cliente',
            'password': 'pass12345',
        })

        self.assertRedirects(response, reverse('diseños'))

    def test_admin_logueado_no_accede_a_cuenta_cliente(self):
        User.objects.create_user(username='admin', password='pass12345', is_staff=True)
        self.client.login(username='admin', password='pass12345')

        response = self.client.get(reverse('cuenta'))

        self.assertRedirects(response, reverse('dashboard'))
