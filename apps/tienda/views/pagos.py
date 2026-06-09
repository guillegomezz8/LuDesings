from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

import stripe
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.cuentas.decorators import staff_required

from ..forms import PedidoForm
from ..models import Diseño, LineaPedido, Pedido, StockTalla
from .carrito import (
    _carrito_items,
    _es_admin_request,
    _guardar_carrito,
    _sincronizar_disponibilidad_producto,
)


def _absolute_url(request, url_name, **kwargs):
    return request.build_absolute_uri(reverse(url_name, kwargs=kwargs))


def _precio_en_centimos(precio):
    centimos = (precio * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return int(centimos)


def _fecha_expiracion_checkout():
    minutos = getattr(settings, 'STRIPE_CHECKOUT_EXPIRES_MINUTES', 30)
    segundos = min(max(int(minutos) * 60 + 30, 1800), 86340)
    return timezone.now() + timedelta(seconds=segundos)


def _line_items_stripe(pedido):
    line_items = []
    for linea in pedido.lineas.all():
        nombre = linea.nombre_producto
        if linea.talla:
            nombre = f'{nombre} - Talla {linea.talla}'
        line_items.append({
            'price_data': {
                'currency': settings.STRIPE_CURRENCY,
                'product_data': {'name': nombre},
                'unit_amount': _precio_en_centimos(linea.precio_unitario),
            },
            'quantity': linea.cantidad,
        })
    return line_items


def _crear_pedido_desde_carrito(request, form, items, total):
    del total  # El total se recalcula con precios bloqueados para evitar datos obsoletos.

    with transaction.atomic():
        productos = Diseño.objects.select_for_update().filter(
            id__in=[item['diseño'].id for item in items]
        )
        productos_por_id = {producto.id: producto for producto in productos}
        reservas = []
        total_revisado = Decimal('0')

        for item in items:
            producto = productos_por_id.get(item['diseño'].id)
            if not producto or not producto.disponible:
                raise ValueError('Una de las prendas del carrito ya no está disponible.')

            variante = None
            if producto.stocks_talla.exists():
                variante = StockTalla.objects.select_for_update().filter(
                    diseño=producto,
                    talla__iexact=item['talla'],
                    disponible=True,
                    stock__gt=0,
                ).first()
                if not variante:
                    raise ValueError(
                        f'La talla {item["talla"]} de {producto.nombre} ya no está disponible.'
                    )
                if item['cantidad'] > variante.stock:
                    raise ValueError(
                        f'No hay stock suficiente de {producto.nombre} en talla {variante.talla}.'
                    )
                item['talla'] = variante.talla
            elif item['cantidad'] > producto.stock:
                raise ValueError(f'No hay stock suficiente de {producto.nombre}.')

            if producto.precio <= 0:
                raise ValueError(f'{producto.nombre} no tiene un precio válido para pagar online.')

            total_revisado += producto.precio * item['cantidad']
            reservas.append((item, producto, variante))

        pedido = form.save(commit=False)
        if request.user.is_authenticated:
            pedido.usuario = request.user
        pedido.total = total_revisado
        pedido.estado = 'pendiente_pago'
        pedido.estado_pago = 'pendiente'
        pedido.stock_reservado = True
        pedido.fecha_expiracion_pago = _fecha_expiracion_checkout()
        pedido.save()

        for item, producto, variante in reservas:
            LineaPedido.objects.create(
                pedido=pedido,
                diseño=producto,
                nombre_producto=producto.nombre,
                talla=item['talla'],
                cantidad=item['cantidad'],
                precio_unitario=producto.precio,
            )

            if variante:
                variante.stock -= item['cantidad']
                variante.disponible = variante.stock > 0
                variante.save(update_fields=['stock', 'disponible'])
                _sincronizar_disponibilidad_producto(producto)
            else:
                producto.stock -= item['cantidad']
                producto.disponible = producto.stock > 0
                producto.save(update_fields=['stock', 'disponible'])

    return pedido


def _crear_stripe_checkout_session(request, pedido):
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError('Stripe no está configurado. Falta STRIPE_SECRET_KEY.')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    success_url = request.build_absolute_uri(
        reverse('stripe_success') + '?session_id={CHECKOUT_SESSION_ID}'
    )
    cancel_url = (
        _absolute_url(request, 'stripe_cancel', pk=pedido.pk)
        + f'?token={pedido.access_token}'
    )
    parametros = {
        'mode': 'payment',
        'customer_email': pedido.email,
        'client_reference_id': str(pedido.pk),
        'line_items': _line_items_stripe(pedido),
        'success_url': success_url,
        'cancel_url': cancel_url,
        'expires_at': int(pedido.fecha_expiracion_pago.timestamp()),
        'locale': 'es',
        'metadata': {'pedido_id': str(pedido.pk)},
        'payment_intent_data': {'metadata': {'pedido_id': str(pedido.pk)}},
    }

    session = stripe.checkout.Session.create(
        **parametros,
        idempotency_key=f'pedido-{pedido.pk}-checkout',
    )
    pedido.stripe_checkout_session_id = session.id
    pedido.save(update_fields=['stripe_checkout_session_id', 'fecha_actualizacion'])
    return session


def _liberar_reserva_pedido(pedido, marcar_fallido=True):
    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
        if pedido.estado_pago != 'pendiente':
            return pedido

        if pedido.stock_reservado:
            for linea in pedido.lineas.select_related('diseño'):
                producto = linea.diseño
                if not producto:
                    continue

                producto = Diseño.objects.select_for_update().get(pk=producto.pk)
                if producto.stocks_talla.exists():
                    variante = StockTalla.objects.select_for_update().filter(
                        diseño=producto,
                        talla__iexact=linea.talla,
                    ).first()
                    if variante:
                        variante.stock += linea.cantidad
                        variante.disponible = True
                        variante.save(update_fields=['stock', 'disponible'])
                        if not producto.disponible:
                            producto.disponible = True
                            producto.save(update_fields=['disponible'])
                else:
                    producto.stock += linea.cantidad
                    producto.disponible = True
                    producto.save(update_fields=['stock', 'disponible'])

        pedido.stock_reservado = False
        pedido.estado = 'cancelado'
        if marcar_fallido:
            pedido.estado_pago = 'fallido'
        pedido.save(update_fields=[
            'stock_reservado',
            'estado',
            'estado_pago',
            'fecha_actualizacion',
        ])
        return pedido


def _marcar_pago_con_incidencia(pedido, payment_intent_id):
    pedido.stock_reservado = False
    pedido.estado_pago = 'pagado'
    pedido.estado = 'incidencia'
    pedido.stripe_payment_intent_id = payment_intent_id or pedido.stripe_payment_intent_id
    pedido.fecha_pago = timezone.now()
    pedido.save(update_fields=[
        'stock_reservado',
        'estado_pago',
        'estado',
        'stripe_payment_intent_id',
        'fecha_pago',
        'fecha_actualizacion',
    ])
    return pedido


def _confirmar_pago_pedido(pedido, stripe_session_id='', payment_intent_id=''):
    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
        if pedido.estado_pago == 'pagado':
            return pedido

        # Los pedidos nuevos ya tienen el stock descontado como reserva.
        if not pedido.stock_reservado:
            lineas_bloqueadas = []
            for linea in pedido.lineas.select_related('diseño'):
                producto = linea.diseño
                if not producto:
                    continue

                producto = Diseño.objects.select_for_update().get(pk=producto.pk)
                variante = None
                if producto.stocks_talla.exists():
                    variante = StockTalla.objects.select_for_update().filter(
                        diseño=producto,
                        talla__iexact=linea.talla,
                        disponible=True,
                    ).first()
                    if not variante or linea.cantidad > variante.stock:
                        return _marcar_pago_con_incidencia(pedido, payment_intent_id)
                elif not producto.disponible or linea.cantidad > producto.stock:
                    return _marcar_pago_con_incidencia(pedido, payment_intent_id)
                lineas_bloqueadas.append((linea, producto, variante))

            for linea, producto, variante in lineas_bloqueadas:
                if variante:
                    variante.stock -= linea.cantidad
                    variante.disponible = variante.stock > 0
                    variante.save(update_fields=['stock', 'disponible'])
                    _sincronizar_disponibilidad_producto(producto)
                else:
                    producto.stock -= linea.cantidad
                    producto.disponible = producto.stock > 0
                    producto.save(update_fields=['stock', 'disponible'])

        pedido.stock_reservado = False
        pedido.estado_pago = 'pagado'
        pedido.estado = 'confirmado'
        if stripe_session_id:
            pedido.stripe_checkout_session_id = stripe_session_id
        if payment_intent_id:
            pedido.stripe_payment_intent_id = payment_intent_id
        pedido.fecha_pago = timezone.now()
        pedido.save(update_fields=[
            'stock_reservado',
            'estado_pago',
            'estado',
            'stripe_checkout_session_id',
            'stripe_payment_intent_id',
            'fecha_pago',
            'fecha_actualizacion',
        ])
        return pedido


def _sesion_coincide_con_pedido(session, pedido):
    moneda = session.get('currency')
    if moneda and moneda.lower() != settings.STRIPE_CURRENCY.lower():
        return False

    total_centimos = session.get('amount_total')
    if total_centimos is not None and total_centimos != _precio_en_centimos(pedido.total):
        return False
    return True


def checkout(request):
    if _es_admin_request(request):
        return redirect('dashboard')

    items, total = _carrito_items(request)
    if not items:
        messages.error(request, 'Tu carrito está vacío.')
        return redirect('diseños')

    initial = {}
    if request.user.is_authenticated:
        perfil = getattr(request.user, 'perfil_cliente', None)
        initial = {
            'nombre_cliente': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
            'telefono': getattr(perfil, 'telefono', ''),
            'direccion': getattr(perfil, 'direccion', ''),
            'ciudad': getattr(perfil, 'ciudad', ''),
            'codigo_postal': getattr(perfil, 'codigo_postal', ''),
        }

    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            if not settings.STRIPE_SECRET_KEY:
                messages.error(
                    request,
                    'Stripe no está configurado. Añade STRIPE_SECRET_KEY para activar pagos.',
                )
                return redirect('checkout')
            pedido = None
            try:
                pedido = _crear_pedido_desde_carrito(request, form, items, total)
                session = _crear_stripe_checkout_session(request, pedido)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('carrito')
            except Exception as exc:
                if pedido:
                    _liberar_reserva_pedido(pedido)
                messages.error(request, f'No se pudo iniciar el pago con Stripe: {exc}')
                return redirect('checkout')

            request.session['ultimo_pedido_id'] = pedido.pk
            return redirect(session.url)
    else:
        form = PedidoForm(initial=initial)

    return render(request, 'tienda/checkout.html', {
        'form': form,
        'items': items,
        'total': total,
        'stripe_configurado': bool(settings.STRIPE_SECRET_KEY),
        'reserva_minutos': settings.STRIPE_CHECKOUT_EXPIRES_MINUTES,
    })


def stripe_success(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        messages.error(request, 'No se ha podido confirmar el pago.')
        return redirect('diseños')

    if not settings.STRIPE_SECRET_KEY:
        messages.error(request, 'Stripe no está configurado.')
        return redirect('diseños')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception as exc:
        messages.error(request, f'No se ha podido verificar el pago: {exc}')
        return redirect('diseños')

    pedido = get_object_or_404(Pedido, stripe_checkout_session_id=session.id)
    request.session['ultimo_pedido_id'] = pedido.pk

    if not _sesion_coincide_con_pedido(session, pedido):
        messages.error(request, 'Los datos devueltos por Stripe no coinciden con el pedido.')
    elif session.payment_status == 'paid':
        _confirmar_pago_pedido(
            pedido,
            stripe_session_id=session.id,
            payment_intent_id=session.get('payment_intent') or '',
        )
        _guardar_carrito(request, {})
        messages.success(request, 'Pago confirmado. Tu pedido ya está registrado.')
    else:
        messages.warning(request, 'Stripe todavía está procesando el pago.')

    detalle_url = f"{reverse('pedido_detalle', kwargs={'pk': pedido.pk})}?token={pedido.access_token}"
    return redirect(detalle_url)


def stripe_cancel(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    token = request.GET.get('token')
    puede_ver = (
        request.session.get('ultimo_pedido_id') == pedido.pk
        or (token and token == str(pedido.access_token))
        or (request.user.is_authenticated and pedido.usuario_id == request.user.id)
    )
    if puede_ver and pedido.estado_pago == 'pendiente':
        _liberar_reserva_pedido(pedido)
        messages.warning(
            request,
            'Pago cancelado. Hemos liberado el stock y tu carrito sigue disponible.',
        )
    return redirect('carrito')


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    session = event.get('data', {}).get('object', {})
    pedido_id = session.get('metadata', {}).get('pedido_id')
    if not pedido_id:
        return HttpResponse(status=200)

    try:
        pedido = Pedido.objects.get(pk=pedido_id)
    except Pedido.DoesNotExist:
        return HttpResponse(status=200)

    if event['type'] in [
        'checkout.session.completed',
        'checkout.session.async_payment_succeeded',
    ]:
        if session.get('payment_status') == 'paid' and _sesion_coincide_con_pedido(session, pedido):
            _confirmar_pago_pedido(
                pedido,
                stripe_session_id=session.get('id', ''),
                payment_intent_id=session.get('payment_intent') or '',
            )
    elif event['type'] in [
        'checkout.session.expired',
        'checkout.session.async_payment_failed',
    ]:
        _liberar_reserva_pedido(pedido)

    return HttpResponse(status=200)


def pedido_detalle(request, pk):
    pedido = get_object_or_404(Pedido.objects.prefetch_related('lineas'), pk=pk)
    token = request.GET.get('token')
    puede_ver = (
        request.session.get('ultimo_pedido_id') == pedido.pk
        or (token and token == str(pedido.access_token))
        or request.user.is_staff
        or (request.user.is_authenticated and pedido.usuario_id == request.user.id)
    )
    if not puede_ver:
        if request.user.is_authenticated:
            raise PermissionDenied
        messages.error(request, 'Inicia sesión o usa el enlace seguro del pedido para verlo.')
        return redirect('login')

    return render(request, 'tienda/pedido_detalle.html', {'pedido': pedido})


@staff_required
@require_POST
def actualizar_estado_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    estado = request.POST.get('estado')
    estados_validos = [opcion[0] for opcion in Pedido.ESTADOS]

    if estado in estados_validos:
        if (
            pedido.estado_pago != 'pagado'
            and estado in ['confirmado', 'preparando', 'enviado', 'completado']
        ):
            messages.error(
                request,
                'No se puede avanzar un pedido que todavía no está pagado.',
            )
            return redirect('dashboard')
        pedido.estado = estado
        pedido.save(update_fields=['estado', 'fecha_actualizacion'])
        messages.success(request, f'Pedido #{pedido.pk} actualizado.')

    return redirect('dashboard')
