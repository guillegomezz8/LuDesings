from django.shortcuts import get_object_or_404, redirect, render
from django.db import OperationalError, ProgrammingError

from .forms import PeticionesForm
from .models import EntradaBlog, SobreMiContenido


def sobreMi(request):
    contenido = SobreMiContenido.objects.order_by('-actualizado').first()
    return render(request, 'sitio/sobre_mi.html', {'contenido_sobre_mi': contenido})

def peticionesForm(request):

    if request.method == 'POST':
        form = PeticionesForm(request.POST)
        if form.is_valid():
            peticion = form.save(commit=False)
            if request.user.is_authenticated:
                peticion.usuario = request.user
                if not peticion.nombre_cliente:
                    peticion.nombre_cliente = request.user.get_full_name() or request.user.username
            peticion.save()

            return redirect('diseño_a_medida')
    else:
        initial = {}
        if request.user.is_authenticated and request.user.email:
            initial['email'] = request.user.email
            initial['nombre_cliente'] = request.user.get_full_name() or request.user.username
            perfil = getattr(request.user, 'perfil_cliente', None)
            if perfil:
                initial['telefono'] = perfil.telefono
        form = PeticionesForm(initial=initial)

    referer = request.META.get('HTTP_REFERER', '/')

    return render(request, 'sitio/peticion_formulario.html', {
        'form': form,
        'referer': referer,
    })

def blog(request):
    try:
        entradas = EntradaBlog.objects.filter(publicado=True)
    except (OperationalError, ProgrammingError):
        entradas = []
    return render(request, 'sitio/blog.html', {'entradas': entradas})

def blog_detalle(request, slug):
    entradas = EntradaBlog.objects.all() if request.user.is_staff else EntradaBlog.objects.filter(publicado=True)
    entrada = get_object_or_404(entradas, slug=slug)
    recientes = EntradaBlog.objects.filter(publicado=True).exclude(pk=entrada.pk)[:3]
    return render(request, 'sitio/blog_detalle.html', {
        'entrada': entrada,
        'recientes': recientes,
    })
