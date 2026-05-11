from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from diseños.models import Diseño, LineaPedido, Pedido
from .models import EntradaBlog, Peticion, SobreMiContenido


class DashboardAdminTests(TestCase):
    def test_dashboard_renderiza_resumen_para_administrador(self):
        admin = User.objects.create_user(username='admin', password='pass12345', is_staff=True)
        cliente = User.objects.create_user(username='cliente', password='pass12345', email='cliente@example.com')
        diseño = Diseño.objects.create(nombre='Vestido Test', descripccion='Prenda de prueba')
        pedido = Pedido.objects.create(
            usuario=cliente,
            nombre_cliente='Cliente',
            email='cliente@example.com',
            direccion='Calle Test 1',
            ciudad='Madrid',
            codigo_postal='28001',
            total=25,
        )
        LineaPedido.objects.create(pedido=pedido, diseño=diseño, nombre_producto='Vestido Test', cantidad=1, precio_unitario=25)
        Peticion.objects.create(usuario=cliente, asunto='Consulta', email='cliente@example.com', peticion='Quiero información.')

        self.client.login(username='admin', password='pass12345')
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pedidos')
        self.assertContains(response, 'Vestido Test')

    def test_dashboard_rechaza_cliente_normal(self):
        User.objects.create_user(username='cliente', password='pass12345')
        self.client.login(username='cliente', password='pass12345')

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 403)

    def test_dashboard_anonimo_redirige_a_login(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response['Location'])


class ContenidoPublicoTests(TestCase):
    def test_sobre_mi_usa_contenido_editable(self):
        SobreMiContenido.objects.create(
            titulo='LuJapon editable',
            texto='Texto editable desde el panel de administración.',
        )

        response = self.client.get(reverse('sobreMi'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'LuJapon editable')
        self.assertContains(response, 'Texto editable desde el panel de administración.')

    def test_solicitud_a_medida_es_publica_y_guarda_campos(self):
        response = self.client.post(reverse('diseño_a_medida'), {
            'nombre_cliente': 'Cliente Invitada',
            'email': 'cliente@example.com',
            'telefono': '600000000',
            'tipo_prenda': 'vestido',
            'talla_aproximada': 'M',
            'presupuesto': '120.00',
            'fecha_evento': '2026-08-20',
            'asunto': 'Vestido para feria',
            'peticion': 'Quiero un vestido rojo con detalles dorados.',
        })

        self.assertRedirects(response, reverse('diseño_a_medida'))
        peticion = Peticion.objects.get(email='cliente@example.com')
        self.assertEqual(peticion.nombre_cliente, 'Cliente Invitada')
        self.assertEqual(peticion.tipo_prenda, 'vestido')
        self.assertEqual(str(peticion.presupuesto), '120.00')

    def test_blog_muestra_entradas_publicadas(self):
        entrada = EntradaBlog.objects.create(
            titulo='Tendencias de feria',
            slug='tendencias-feria',
            entradilla='Ideas para preparar tu prenda.',
            contenido='Contenido del blog.',
            publicado=True,
        )
        EntradaBlog.objects.create(
            titulo='Borrador privado',
            slug='borrador-privado',
            contenido='No debe salir.',
            publicado=False,
        )

        response = self.client.get(reverse('blog'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, entrada.titulo)
        self.assertNotContains(response, 'Borrador privado')

    def test_blog_detalle_publico(self):
        entrada = EntradaBlog.objects.create(
            titulo='Cómo cuidar una prenda',
            slug='como-cuidar-una-prenda',
            entradilla='Cuidados básicos.',
            contenido='Lavar con cuidado y guardar bien.',
            publicado=True,
        )

        response = self.client.get(reverse('blog_detalle', args=[entrada.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cómo cuidar una prenda')
