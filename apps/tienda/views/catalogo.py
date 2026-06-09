from urllib.parse import quote

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.cuentas.decorators import staff_required

from ..forms import DiseñoForm
from ..models import DisenoLike, Diseño, Imagen

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

    return render(request, 'tienda/lista.html',{
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

    return render(request, 'tienda/crear.html', {'form': form, 'referer': referer})

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
    return render(request, 'tienda/editar.html', {'form': form, 'diseño': diseño})


def detalle_diseño(request,pk):
    diseño = get_object_or_404(Diseño.objects.prefetch_related('stocks_talla'), pk=pk)
    imagenes = diseño.todas_las_imagenes()
    stock_tallas = diseño.stocks_talla.filter(disponible=True, stock__gt=0).order_by('talla')
    ha_dado_like = request.user.is_authenticated and DisenoLike.objects.filter(usuario=request.user, diseño=diseño).exists()
    return render(request, 'tienda/detalle.html',{
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
