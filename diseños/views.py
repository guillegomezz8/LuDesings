from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import quote

import stripe
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import DiseñoForm, PedidoForm
from .models import DisenoLike, Diseño, Imagen, LineaPedido, Pedido, StockTalla
from usuarios.decorators import staff_required

CARRITO_SESSION_KEY = 'carrito'


def _obtener_carrito(request):
    return request.session.get(CARRITO_SESSION_KEY, {})


def _guardar_carrito(request, carrito):
    request.session[CARRITO_SESSION_KEY] = carrito
    request.session.modified = True


def _parsear_clave_carrito(clave):
    diseño_id, separador, talla = str(clave).partition(':')
    try:
        return int(diseño_id), talla if separador else ''
    except (TypeError, ValueError):
        return None, ''


def _clave_carrito(diseño, talla=''):
    if diseño.tiene_stock_por_talla and talla:
        return f'{diseño.id}:{talla}'
    return str(diseño.id)


def _stock_talla_disponible(diseño, talla):
    if not diseño.tiene_stock_por_talla:
        return None
    if not talla:
        return None
    return diseño.stocks_talla.filter(talla=talla, disponible=True, stock__gt=0).first()


def _sincronizar_disponibilidad_producto(producto):
    if producto.tiene_stock_por_talla:
        quedan_tallas = producto.stocks_talla.filter(disponible=True, stock__gt=0).exists()
        if not quedan_tallas and producto.disponible:
            producto.disponible = False
            producto.save(update_fields=['disponible'])


def _carrito_items(request):
    carrito = _obtener_carrito(request)
    ids = []
    for clave in carrito.keys():
        diseño_id, _ = _parsear_clave_carrito(clave)
        if diseño_id:
            ids.append(diseño_id)

    diseños_por_id = {
        diseño.id: diseño
        for diseño in Diseño.objects.prefetch_related('stocks_talla').filter(id__in=ids)
    }
    items = []
    total = 0
    carrito_limpio = {}

    for clave, datos in carrito.items():
        diseño_pk, talla_clave = _parsear_clave_carrito(clave)
        if not diseño_pk:
            continue

        diseño = diseños_por_id.get(diseño_pk)
        if not diseño:
            continue

        if not diseño.esta_disponible:
            continue

        if not isinstance(datos, dict):
            datos = {}
        try:
            cantidad = max(1, int(datos.get('cantidad', 1)))
        except (AttributeError, TypeError, ValueError):
            cantidad = 1
        talla = (datos.get('talla') or talla_clave or diseño.talla).strip()
        variante_talla = _stock_talla_disponible(diseño, talla)
        max_stock = variante_talla.stock if variante_talla else diseño.stock

        if diseño.tiene_stock_por_talla and not variante_talla:
            continue

        cantidad = min(cantidad, max_stock)
        subtotal = diseño.precio * cantidad
        total += subtotal
        clave_limpia = _clave_carrito(diseño, talla)
        tallas_disponibles = [
            stock for stock in diseño.stocks_talla.all()
            if stock.disponible and stock.stock > 0
        ] if diseño.tiene_stock_por_talla else []
        carrito_limpio[clave_limpia] = {'cantidad': cantidad, 'talla': talla}
        items.append({
            'key': clave_limpia,
            'diseño': diseño,
            'cantidad': cantidad,
            'talla': talla,
            'tallas_disponibles': tallas_disponibles,
            'max_stock': max_stock,
            'subtotal': subtotal,
        })

    if carrito_limpio != carrito:
        _guardar_carrito(request, carrito_limpio)

    return items, total


def _cantidad_post(request, defecto=1):
    try:
        return max(1, int(request.POST.get('cantidad', defecto)))
    except (TypeError, ValueError):
        return defecto


def _absolute_url(request, url_name, **kwargs):
    return request.build_absolute_uri(reverse(url_name, kwargs=kwargs))


def _precio_en_centimos(precio):
    centimos = (precio * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return int(centimos)


def _line_items_stripe(pedido):
    line_items = []
    for linea in pedido.lineas.all():
        nombre = linea.nombre_producto
        if linea.talla:
            nombre = f'{nombre} - Talla {linea.talla}'
        line_items.append({
            'price_data': {
                'currency': settings.STRIPE_CURRENCY,
                'product_data': {
                    'name': nombre,
                },
                'unit_amount': _precio_en_centimos(linea.precio_unitario),
            },
            'quantity': linea.cantidad,
        })
    return line_items


def _crear_pedido_desde_carrito(request, form, items, total):
    with transaction.atomic():
        productos = Diseño.objects.select_for_update().filter(id__in=[item['diseño'].id for item in items])
        productos_por_id = {producto.id: producto for producto in productos}

        for item in items:
            producto = productos_por_id.get(item['diseño'].id)
            if not producto:
                raise ValueError('Una de las prendas del carrito ya no está disponible.')

            if producto.stocks_talla.exists():
                variante = StockTalla.objects.select_for_update().filter(
                    diseño=producto,
                    talla=item['talla'],
                    disponible=True,
                ).first()
                if not variante:
                    raise ValueError(f'La talla {item["talla"]} de {producto.nombre} ya no está disponible.')
                if item['cantidad'] > variante.stock:
                    raise ValueError(f'No hay stock suficiente de {producto.nombre} en talla {item["talla"]}.')
            elif not producto.esta_disponible or item['cantidad'] > producto.stock:
                raise ValueError(f'No hay stock suficiente de {producto.nombre}.')

            if producto.precio <= 0:
                raise ValueError(f'{producto.nombre} no tiene un precio válido para pagar online.')

        pedido = form.save(commit=False)
        if request.user.is_authenticated:
            pedido.usuario = request.user
        pedido.total = total
        pedido.estado = 'pendiente_pago'
        pedido.estado_pago = 'pendiente'
        pedido.save()

        for item in items:
            producto = productos_por_id[item['diseño'].id]
            LineaPedido.objects.create(
                pedido=pedido,
                diseño=producto,
                nombre_producto=producto.nombre,
                talla=item['talla'],
                cantidad=item['cantidad'],
                precio_unitario=producto.precio,
            )

    return pedido


def _crear_stripe_checkout_session(request, pedido):
    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError('Stripe no está configurado. Falta STRIPE_SECRET_KEY.')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    success_url = request.build_absolute_uri(
        reverse('stripe_success') + '?session_id={CHECKOUT_SESSION_ID}'
    )
    cancel_url = _absolute_url(request, 'stripe_cancel', pk=pedido.pk)

    session = stripe.checkout.Session.create(
        mode='payment',
        payment_method_types=['card'],
        customer_email=pedido.email,
        client_reference_id=str(pedido.pk),
        line_items=_line_items_stripe(pedido),
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={'pedido_id': str(pedido.pk)},
        payment_intent_data={'metadata': {'pedido_id': str(pedido.pk)}},
    )
    pedido.stripe_checkout_session_id = session.id
    pedido.save(update_fields=['stripe_checkout_session_id', 'fecha_actualizacion'])
    return session


def _confirmar_pago_pedido(pedido, stripe_session_id='', payment_intent_id=''):
    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().prefetch_related('lineas__diseño').get(pk=pedido.pk)
        if pedido.estado_pago == 'pagado':
            return pedido

        for linea in pedido.lineas.select_related('diseño'):
            producto = linea.diseño
            if not producto:
                continue

            if producto.stocks_talla.exists():
                variante = StockTalla.objects.select_for_update().filter(
                    diseño=producto,
                    talla=linea.talla,
                    disponible=True,
                ).first()
                if not variante or linea.cantidad > variante.stock:
                    pedido.estado_pago = 'pagado'
                    pedido.estado = 'incidencia'
                    pedido.stripe_payment_intent_id = payment_intent_id or pedido.stripe_payment_intent_id
                    pedido.fecha_pago = timezone.now()
                    pedido.save(update_fields=['estado_pago', 'estado', 'stripe_payment_intent_id', 'fecha_pago', 'fecha_actualizacion'])
                    return pedido
            elif not producto.disponible or linea.cantidad > producto.stock:
                pedido.estado_pago = 'pagado'
                pedido.estado = 'incidencia'
                pedido.stripe_payment_intent_id = payment_intent_id or pedido.stripe_payment_intent_id
                pedido.fecha_pago = timezone.now()
                pedido.save(update_fields=['estado_pago', 'estado', 'stripe_payment_intent_id', 'fecha_pago', 'fecha_actualizacion'])
                return pedido

        for linea in pedido.lineas.select_related('diseño'):
            producto = linea.diseño
            if not producto:
                continue

            if producto.stocks_talla.exists():
                variante = StockTalla.objects.select_for_update().get(diseño=producto, talla=linea.talla)
                variante.stock -= linea.cantidad
                if variante.stock == 0:
                    variante.disponible = False
                variante.save(update_fields=['stock', 'disponible'])
                _sincronizar_disponibilidad_producto(producto)
            else:
                producto.stock -= linea.cantidad
                if producto.stock == 0:
                    producto.disponible = False
                producto.save(update_fields=['stock', 'disponible'])

        pedido.estado_pago = 'pagado'
        pedido.estado = 'confirmado'
        if stripe_session_id:
            pedido.stripe_checkout_session_id = stripe_session_id
        if payment_intent_id:
            pedido.stripe_payment_intent_id = payment_intent_id
        pedido.fecha_pago = timezone.now()
        pedido.save(update_fields=[
            'estado_pago',
            'estado',
            'stripe_checkout_session_id',
            'stripe_payment_intent_id',
            'fecha_pago',
            'fecha_actualizacion',
        ])
        return pedido

def _es_admin_request(request):
    return request.user.is_authenticated and request.user.is_staff

def diseños(request):
    orden = request.GET.get('orden', 'fecha_reciente')
    categoria = request.GET.get('categoria', '')
    busqueda = request.GET.get('q', '').strip()
    solo_disponibles = request.GET.get('disponibles') == '1'

    diseños = Diseño.objects.prefetch_related('stocks_talla').all()

    if busqueda:
        diseños = diseños.filter(Q(nombre__icontains=busqueda) | Q(descripccion__icontains=busqueda))

    if categoria:
        diseños = diseños.filter(categoria=categoria)

    if solo_disponibles:
        diseños = diseños.filter(
            Q(disponible=True, stock__gt=0) |
            Q(disponible=True, stocks_talla__disponible=True, stocks_talla__stock__gt=0)
        ).distinct()

    if orden == 'fecha_reciente':
        diseños = diseños.order_by('-fecha_subida')
    elif orden == 'fecha_antigua':
        diseños = diseños.order_by('fecha_subida')
    elif orden == 'popularidad':
        diseños = diseños.order_by('-popularidad')
    elif orden == 'precio_menor':
        diseños = diseños.order_by('precio')
    elif orden == 'precio_mayor':
        diseños = diseños.order_by('-precio')
    else:
        diseños = diseños.order_by('-fecha_subida')

    liked_ids = []
    if request.user.is_authenticated:
        liked_ids = list(DisenoLike.objects.filter(usuario=request.user).values_list('diseño_id', flat=True))

    return render(request, 'diseños.html',{
        'diseños': diseños,
        'orden': orden,
        'categoria': categoria,
        'categorias': Diseño.CATEGORIAS,
        'busqueda': busqueda,
        'solo_disponibles': solo_disponibles,
        'liked_ids': liked_ids,
    })

@staff_required
def crear_diseño(request):
    if request.method == 'POST':
        form = DiseñoForm(request.POST, request.FILES)
        if form.is_valid():
            diseño = form.save(commit=False)
            diseño.save()
            form.guardar_stock_tallas(diseño)

            for imagen_adicional in request.FILES.getlist('imagenes_adicionales'):
                imagen_adicional_obj = Imagen.objects.create(imagen=imagen_adicional)
                diseño.imagenes_adicionales.add(imagen_adicional_obj)

            return redirect('diseños')
    else:
        form = DiseñoForm()
    
    referer = request.META.get('HTTP_REFERER', '/')
    
    return render(request, 'diseñoCrear.html', {'form': form, 'referer': referer})

@staff_required
def borrar_diseño(request, pk):
    diseño = get_object_or_404(Diseño, pk=pk)
    if request.method == 'POST':
        diseño.delete()
    return redirect('diseños')   

@staff_required
def editar_diseño(request,pk):
    diseño = get_object_or_404(Diseño.objects.prefetch_related('stocks_talla'), pk=pk)
    if request.method == 'POST':
        form = DiseñoForm(request.POST, request.FILES, instance=diseño)
        if form.is_valid():
            diseño = form.save(commit=False)
            diseño.save()
            form.guardar_stock_tallas(diseño)

            imagenes_a_eliminar = request.POST.getlist('eliminar_imagenes')
            for imagen_id in imagenes_a_eliminar:
                imagen = Imagen.objects.get(pk=imagen_id)
                diseño.imagenes_adicionales.remove(imagen)
                imagen.delete()

            imagenes_adicionales = request.FILES.getlist('imagenes_adicionales')
            for imagen_adicional in imagenes_adicionales:
                imagen_adicional_obj = Imagen.objects.create(imagen=imagen_adicional)
                diseño.imagenes_adicionales.add(imagen_adicional_obj)

            return redirect('diseños')
    else:
        form = DiseñoForm(instance=diseño)
    return render(request, 'diseñoEditar.html', {'form': form, 'diseño': diseño})


def detalle_diseño(request,pk):
    diseño = get_object_or_404(Diseño.objects.prefetch_related('stocks_talla'), pk=pk)
    imagenes = diseño.todas_las_imagenes()
    stock_tallas = diseño.stocks_talla.filter(disponible=True, stock__gt=0).order_by('talla')
    ha_dado_like = request.user.is_authenticated and DisenoLike.objects.filter(usuario=request.user, diseño=diseño).exists()
    return render(request, 'diseñoDetalle.html',{
        'diseño': diseño,
        'imagenes': imagenes,
        'stock_tallas': stock_tallas,
        'ha_dado_like': ha_dado_like,
    })

@require_POST
def like_diseno(request, diseno_id):
    if not request.user.is_authenticated:
        next_url = quote(request.META.get('HTTP_REFERER', reverse('diseños')), safe='')
        return JsonResponse({'error': 'login_required', 'login_url': f"{reverse('login')}?next={next_url}"}, status=403)

    diseno = get_object_or_404(Diseño, id=diseno_id)
    like, creado = DisenoLike.objects.get_or_create(usuario=request.user, diseño=diseno)

    if creado:
        liked = True
    else:
        like.delete()
        liked = False

    diseno.popularidad = diseno.likes.count()
    diseno.save(update_fields=['popularidad'])

    return JsonResponse({'popularidad': diseno.popularidad, 'liked': liked})

@require_POST
def agregar_al_carrito(request, pk):
    if _es_admin_request(request):
        return redirect('dashboard')

    diseño = get_object_or_404(Diseño, pk=pk)

    if not diseño.esta_disponible:
        messages.error(request, 'Esta prenda no está disponible ahora mismo.')
        return redirect(request.POST.get('next') or 'diseños')

    cantidad = _cantidad_post(request)
    talla = (request.POST.get('talla') or '').strip()
    variante_talla = _stock_talla_disponible(diseño, talla)
    if diseño.tiene_stock_por_talla:
        if not variante_talla:
            messages.error(request, 'Elige una talla disponible antes de añadir la prenda.')
            return redirect(request.POST.get('next') or reverse('detalle_diseño', args=[diseño.pk]))
        stock_disponible = variante_talla.stock
    else:
        talla = talla or diseño.talla
        stock_disponible = diseño.stock

    carrito = _obtener_carrito(request)
    clave = _clave_carrito(diseño, talla)
    item = carrito.get(clave, {'cantidad': 0, 'talla': talla})
    nueva_cantidad = min(item['cantidad'] + cantidad, stock_disponible)
    carrito[clave] = {'cantidad': nueva_cantidad, 'talla': talla}
    _guardar_carrito(request, carrito)
    messages.success(request, 'Prenda añadida al carrito.')
    return redirect(request.POST.get('next') or 'carrito')


def carrito(request):
    if _es_admin_request(request):
        return redirect('dashboard')

    items, total = _carrito_items(request)
    return render(request, 'carrito.html', {'items': items, 'total': total})


@require_POST
def actualizar_carrito(request, pk):
    if _es_admin_request(request):
        return redirect('dashboard')

    carrito = _obtener_carrito(request)
    diseño = get_object_or_404(Diseño, pk=pk)
    accion = request.POST.get('accion')
    item_key = request.POST.get('item_key') or str(diseño.id)

    if accion == 'eliminar' or not diseño.esta_disponible:
        carrito.pop(item_key, None)
        if accion != 'eliminar':
            messages.error(request, 'Esta prenda ya no está disponible y se ha quitado del carrito.')
    else:
        cantidad = _cantidad_post(request)
        talla = (request.POST.get('talla') or '').strip()
        variante_talla = _stock_talla_disponible(diseño, talla)
        if diseño.tiene_stock_por_talla:
            if not variante_talla:
                messages.error(request, 'Esa talla ya no está disponible.')
                return redirect('carrito')
            stock_disponible = variante_talla.stock
        else:
            talla = talla or diseño.talla
            stock_disponible = diseño.stock

        cantidad = min(cantidad, stock_disponible)
        nueva_clave = _clave_carrito(diseño, talla)
        if nueva_clave != item_key:
            carrito.pop(item_key, None)
        carrito[nueva_clave] = {'cantidad': cantidad, 'talla': talla}

    _guardar_carrito(request, carrito)
    return redirect('carrito')


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
                messages.error(request, 'Stripe no está configurado. Añade STRIPE_SECRET_KEY para activar pagos.')
                return redirect('checkout')
            try:
                pedido = _crear_pedido_desde_carrito(request, form, items, total)
                session = _crear_stripe_checkout_session(request, pedido)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('carrito')
            except Exception as exc:
                if 'pedido' in locals():
                    pedido.estado = 'cancelado'
                    pedido.estado_pago = 'fallido'
                    pedido.save(update_fields=['estado', 'estado_pago', 'fecha_actualizacion'])
                messages.error(request, f'No se pudo iniciar el pago con Stripe: {exc}')
                return redirect('checkout')

            request.session['ultimo_pedido_id'] = pedido.pk
            return redirect(session.url)
    else:
        form = PedidoForm(initial=initial)

    return render(request, 'checkout.html', {
        'form': form,
        'items': items,
        'total': total,
        'stripe_configurado': bool(settings.STRIPE_SECRET_KEY),
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

    if session.payment_status == 'paid':
        _confirmar_pago_pedido(
            pedido,
            stripe_session_id=session.id,
            payment_intent_id=session.get('payment_intent') or '',
        )
        _guardar_carrito(request, {})
        messages.success(request, 'Pago confirmado. Tu pedido ya está registrado.')
    else:
        messages.error(request, 'El pago todavía no aparece como completado.')

    detalle_url = f"{reverse('pedido_detalle', kwargs={'pk': pedido.pk})}?token={pedido.access_token}"
    return redirect(detalle_url)


def stripe_cancel(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    puede_ver = request.session.get('ultimo_pedido_id') == pedido.pk or (
        request.user.is_authenticated and pedido.usuario_id == request.user.id
    )
    if puede_ver and pedido.estado_pago == 'pendiente':
        pedido.estado = 'cancelado'
        pedido.estado_pago = 'fallido'
        pedido.save(update_fields=['estado', 'estado_pago', 'fecha_actualizacion'])
        messages.error(request, 'Pago cancelado. El carrito sigue disponible para intentarlo de nuevo.')
    return redirect('carrito')


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    if not settings.STRIPE_WEBHOOK_SECRET:
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        pedido_id = session.get('metadata', {}).get('pedido_id')
        if pedido_id and session.get('payment_status') == 'paid':
            try:
                pedido = Pedido.objects.get(pk=pedido_id)
            except Pedido.DoesNotExist:
                return HttpResponse(status=200)
            _confirmar_pago_pedido(
                pedido,
                stripe_session_id=session.get('id', ''),
                payment_intent_id=session.get('payment_intent') or '',
            )
    elif event['type'] in ['checkout.session.expired', 'checkout.session.async_payment_failed']:
        session = event['data']['object']
        pedido_id = session.get('metadata', {}).get('pedido_id')
        if pedido_id:
            Pedido.objects.filter(pk=pedido_id, estado_pago='pendiente').update(
                estado='cancelado',
                estado_pago='fallido',
            )

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

    return render(request, 'pedidoDetalle.html', {'pedido': pedido})


@staff_required
@require_POST
def actualizar_estado_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    estado = request.POST.get('estado')
    estados_validos = [opcion[0] for opcion in Pedido.ESTADOS]

    if estado in estados_validos:
        if pedido.estado_pago != 'pagado' and estado in ['confirmado', 'preparando', 'enviado', 'completado']:
            messages.error(request, 'No se puede avanzar un pedido que todavía no está pagado.')
            return redirect('dashboard')
        pedido.estado = estado
        pedido.save(update_fields=['estado', 'fecha_actualizacion'])
        messages.success(request, f'Pedido #{pedido.pk} actualizado.')

    return redirect('dashboard')
