from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from ..models import Diseño

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
    return diseño.stocks_talla.filter(
        talla__iexact=talla,
        disponible=True,
        stock__gt=0,
    ).first()


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
        if variante_talla:
            talla = variante_talla.talla

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


def _es_admin_request(request):
    return request.user.is_authenticated and request.user.is_staff
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
        talla = variante_talla.talla
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
    if nueva_cantidad < item['cantidad'] + cantidad:
        messages.warning(request, f'Solo quedan {stock_disponible} unidades de esa talla.')
    else:
        messages.success(request, 'Prenda añadida al carrito.')
    return redirect(request.POST.get('next') or 'carrito')


def carrito(request):
    if _es_admin_request(request):
        return redirect('dashboard')

    items, total = _carrito_items(request)
    return render(request, 'tienda/carrito.html', {'items': items, 'total': total})


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
            talla = variante_talla.talla
            stock_disponible = variante_talla.stock
        else:
            talla = talla or diseño.talla
            stock_disponible = diseño.stock

        nueva_clave = _clave_carrito(diseño, talla)
        if nueva_clave != item_key:
            carrito.pop(item_key, None)
            cantidad += carrito.get(nueva_clave, {}).get('cantidad', 0)
        cantidad_limitada = min(cantidad, stock_disponible)
        carrito[nueva_clave] = {'cantidad': cantidad_limitada, 'talla': talla}
        if cantidad_limitada < cantidad:
            messages.warning(request, f'La cantidad se ha ajustado al stock disponible: {stock_disponible}.')

    _guardar_carrito(request, carrito)
    return redirect('carrito')
