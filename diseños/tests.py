from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

from .models import DisenoLike, Diseño, LineaPedido, Pedido, StockTalla


class FakeStripeSession(dict):
    def __getattr__(self, item):
        return self[item]


class LikesDiseñoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cliente', password='pass12345')
        self.diseño = Diseño.objects.create(nombre='Vestido Test', descripccion='Prenda de prueba')

    def test_like_requiere_usuario_autenticado(self):
        response = self.client.post(reverse('like_diseno', args=[self.diseño.id]))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(DisenoLike.objects.count(), 0)
        self.diseño.refresh_from_db()
        self.assertEqual(self.diseño.popularidad, 0)

    def test_like_de_cliente_registrado_se_puede_activar_y_quitar(self):
        self.client.login(username='cliente', password='pass12345')

        response = self.client.post(reverse('like_diseno', args=[self.diseño.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['liked'])
        self.assertEqual(response.json()['popularidad'], 1)
        self.assertEqual(DisenoLike.objects.count(), 1)

        response = self.client.post(reverse('like_diseno', args=[self.diseño.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['liked'])
        self.assertEqual(response.json()['popularidad'], 0)
        self.assertEqual(DisenoLike.objects.count(), 0)


class GestionStockDiseñoTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='pass12345', is_staff=True)
        self.client.login(username='admin', password='pass12345')

    def test_crear_prenda_con_stock_por_tallas(self):
        response = self.client.post(reverse('crear'), {
            'nombre': 'Vestido por tallas',
            'descripccion': 'Prenda con varias tallas',
            'categoria': 'vestido',
            'precio': '80.00',
            'modo_stock': 'multiple',
            'talla': '',
            'stock': '',
            'stock_por_tallas': 'S: 2\nM: 0\nL: 4',
            'disponible': 'on',
        })

        self.assertRedirects(response, reverse('diseños'))
        diseño = Diseño.objects.get(nombre='Vestido por tallas')
        self.assertEqual(diseño.stock, 0)
        self.assertEqual(diseño.talla, '')
        self.assertTrue(diseño.disponible)
        self.assertEqual(diseño.stock_total, 6)
        self.assertEqual(
            list(diseño.stocks_talla.order_by('talla').values_list('talla', 'stock', 'disponible')),
            [('L', 4, True), ('M', 0, False), ('S', 2, True)],
        )

    def test_editar_prenda_a_talla_unica_elimina_stock_por_tallas(self):
        diseño = Diseño.objects.create(
            nombre='Vestido convertible',
            descripccion='Prenda editable',
            categoria='vestido',
            precio=80,
            stock=0,
            disponible=True,
        )
        StockTalla.objects.create(diseño=diseño, talla='S', stock=2)

        response = self.client.post(reverse('editar_diseño', args=[diseño.pk]), {
            'nombre': 'Vestido convertible',
            'descripccion': 'Prenda editable',
            'categoria': 'vestido',
            'precio': '80.00',
            'modo_stock': 'unica',
            'talla': 'Única',
            'stock': '5',
            'stock_por_tallas': '',
            'disponible': 'on',
        })

        self.assertRedirects(response, reverse('diseños'))
        diseño.refresh_from_db()
        self.assertEqual(diseño.stock, 5)
        self.assertEqual(diseño.talla, 'Única')
        self.assertFalse(diseño.stocks_talla.exists())


class CarritoPedidoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cliente', password='pass12345')
        self.diseño = Diseño.objects.create(nombre='Traje Test', descripccion='Prenda de prueba', precio=50, stock=2, disponible=True)

    def test_visitante_puede_anadir_al_carrito(self):
        response = self.client.post(reverse('agregar_al_carrito', args=[self.diseño.id]), {
            'talla': 'M',
            'cantidad': 1,
            'next': reverse('carrito'),
        })

        self.assertRedirects(response, reverse('carrito'))
        self.assertEqual(self.client.session['carrito'][str(self.diseño.id)]['cantidad'], 1)

    def test_stock_por_talla_requiere_talla_para_anadir(self):
        StockTalla.objects.create(diseño=self.diseño, talla='S', stock=1)

        response = self.client.post(reverse('agregar_al_carrito', args=[self.diseño.id]), {
            'cantidad': 1,
            'next': reverse('detalle_diseño', args=[self.diseño.id]),
        })

        self.assertRedirects(response, reverse('detalle_diseño', args=[self.diseño.id]))
        self.assertNotIn('carrito', self.client.session)

    def test_carrito_separa_la_misma_prenda_por_tallas(self):
        StockTalla.objects.create(diseño=self.diseño, talla='S', stock=2)
        StockTalla.objects.create(diseño=self.diseño, talla='M', stock=3)

        self.client.post(reverse('agregar_al_carrito', args=[self.diseño.id]), {
            'talla': 'S',
            'cantidad': 1,
            'next': reverse('carrito'),
        })
        self.client.post(reverse('agregar_al_carrito', args=[self.diseño.id]), {
            'talla': 'M',
            'cantidad': 1,
            'next': reverse('carrito'),
        })

        carrito = self.client.session['carrito']
        self.assertEqual(carrito[f'{self.diseño.id}:S']['cantidad'], 1)
        self.assertEqual(carrito[f'{self.diseño.id}:M']['cantidad'], 1)

    @override_settings(STRIPE_SECRET_KEY='sk_test_fake', STRIPE_CURRENCY='eur')
    @patch('diseños.views.stripe.checkout.Session.create')
    def test_checkout_crea_pedido_y_redirige_a_stripe(self, stripe_create):
        stripe_create.return_value = FakeStripeSession(id='cs_test_123', url='https://checkout.stripe.test/pay')
        self.client.post(reverse('agregar_al_carrito', args=[self.diseño.id]), {
            'talla': 'M',
            'cantidad': 1,
            'next': reverse('carrito'),
        })

        response = self.client.post(reverse('checkout'), {
            'nombre_cliente': 'Cliente Invitado',
            'email': 'cliente@example.com',
            'telefono': '600000000',
            'direccion': 'Calle Test 1',
            'ciudad': 'Madrid',
            'codigo_postal': '28001',
            'notas': '',
        })

        pedido = Pedido.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://checkout.stripe.test/pay')
        self.assertEqual(pedido.estado, 'pendiente_pago')
        self.assertEqual(pedido.estado_pago, 'pendiente')
        self.assertEqual(pedido.stripe_checkout_session_id, 'cs_test_123')
        self.assertEqual(LineaPedido.objects.filter(pedido=pedido, diseño=self.diseño).count(), 1)
        self.diseño.refresh_from_db()
        self.assertEqual(self.diseño.stock, 2)

    @override_settings(STRIPE_SECRET_KEY='sk_test_fake')
    @patch('diseños.views.stripe.checkout.Session.retrieve')
    def test_stripe_success_confirma_pedido_y_descuenta_stock(self, stripe_retrieve):
        pedido = Pedido.objects.create(
            nombre_cliente='Cliente Invitado',
            email='cliente@example.com',
            direccion='Calle Test 1',
            ciudad='Madrid',
            codigo_postal='28001',
            total=50,
            stripe_checkout_session_id='cs_test_123',
        )
        LineaPedido.objects.create(
            pedido=pedido,
            diseño=self.diseño,
            nombre_producto=self.diseño.nombre,
            talla='M',
            cantidad=1,
            precio_unitario=self.diseño.precio,
        )
        session = self.client.session
        session['ultimo_pedido_id'] = pedido.pk
        session.save()
        stripe_retrieve.return_value = FakeStripeSession(
            id='cs_test_123',
            payment_status='paid',
            payment_intent='pi_test_123',
        )

        response = self.client.get(reverse('stripe_success'), {'session_id': 'cs_test_123'})

        self.assertEqual(response.status_code, 302)
        redirect = urlparse(response['Location'])
        self.assertEqual(redirect.path, reverse('pedido_detalle', args=[pedido.pk]))
        self.assertEqual(parse_qs(redirect.query)['token'][0], str(pedido.access_token))
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'confirmado')
        self.assertEqual(pedido.estado_pago, 'pagado')
        self.assertEqual(pedido.stripe_payment_intent_id, 'pi_test_123')
        self.diseño.refresh_from_db()
        self.assertEqual(self.diseño.stock, 1)

    @override_settings(STRIPE_SECRET_KEY='sk_test_fake')
    @patch('diseños.views.stripe.checkout.Session.retrieve')
    def test_stripe_success_descuenta_stock_de_la_talla(self, stripe_retrieve):
        stock_s = StockTalla.objects.create(diseño=self.diseño, talla='S', stock=2)
        stock_m = StockTalla.objects.create(diseño=self.diseño, talla='M', stock=4)
        pedido = Pedido.objects.create(
            nombre_cliente='Cliente Invitado',
            email='cliente@example.com',
            direccion='Calle Test 1',
            ciudad='Madrid',
            codigo_postal='28001',
            total=50,
            stripe_checkout_session_id='cs_test_talla',
        )
        LineaPedido.objects.create(
            pedido=pedido,
            diseño=self.diseño,
            nombre_producto=self.diseño.nombre,
            talla='S',
            cantidad=1,
            precio_unitario=self.diseño.precio,
        )
        session = self.client.session
        session['ultimo_pedido_id'] = pedido.pk
        session.save()
        stripe_retrieve.return_value = FakeStripeSession(
            id='cs_test_talla',
            payment_status='paid',
            payment_intent='pi_test_talla',
        )

        response = self.client.get(reverse('stripe_success'), {'session_id': 'cs_test_talla'})

        self.assertEqual(response.status_code, 302)
        stock_s.refresh_from_db()
        stock_m.refresh_from_db()
        self.assertEqual(stock_s.stock, 1)
        self.assertEqual(stock_m.stock, 4)

    def test_pedido_invitado_requiere_sesion_o_token(self):
        pedido = Pedido.objects.create(
            nombre_cliente='Cliente Invitado',
            email='cliente@example.com',
            direccion='Calle Test 1',
            ciudad='Madrid',
            codigo_postal='28001',
            total=50,
        )

        response = self.client.get(reverse('pedido_detalle', args=[pedido.pk]))
        self.assertRedirects(response, reverse('login'))

        response = self.client.get(reverse('pedido_detalle', args=[pedido.pk]), {'token': str(pedido.access_token)})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pedido #')

    def test_cliente_no_puede_ver_pedido_de_otro_cliente(self):
        otro = User.objects.create_user(username='otro', password='pass12345')
        pedido = Pedido.objects.create(
            usuario=otro,
            nombre_cliente='Otro Cliente',
            email='otro@example.com',
            direccion='Calle Test 2',
            ciudad='Madrid',
            codigo_postal='28002',
            total=50,
        )
        self.client.login(username='cliente', password='pass12345')

        response = self.client.get(reverse('pedido_detalle', args=[pedido.pk]))

        self.assertEqual(response.status_code, 403)

    def test_admin_no_puede_avanzar_pedido_sin_pago(self):
        admin = User.objects.create_user(username='admin', password='pass12345', is_staff=True)
        pedido = Pedido.objects.create(
            nombre_cliente='Cliente Invitado',
            email='cliente@example.com',
            direccion='Calle Test 1',
            ciudad='Madrid',
            codigo_postal='28001',
            total=50,
            estado_pago='pendiente',
        )
        self.client.login(username='admin', password='pass12345')

        response = self.client.post(reverse('actualizar_estado_pedido', args=[pedido.pk]), {'estado': 'enviado'})

        self.assertRedirects(response, reverse('dashboard'))
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'pendiente_pago')
