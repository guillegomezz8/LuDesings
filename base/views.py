from django.shortcuts import render, redirect, get_object_or_404
from .forms import PeticionesForm
from .models import EntradaBlog, Peticion, SobreMiContenido
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.db import OperationalError, ProgrammingError
from django.template.loader import render_to_string
from diseños.models import Pedido
from usuarios.decorators import staff_required

def base(request):
    return render(request, 'base.html')

def sobreMi(request):
    contenido = SobreMiContenido.objects.order_by('-actualizado').first()
    return render(request, 'sobreMi.html', {'contenido_sobre_mi': contenido})

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

    return render(request, 'peticionesForm.html', {'form': form,'referer': referer})

def blog(request):
    try:
        entradas = EntradaBlog.objects.filter(publicado=True)
    except (OperationalError, ProgrammingError):
        entradas = []
    return render(request, 'blog.html', {'entradas': entradas})

def blog_detalle(request, slug):
    entradas = EntradaBlog.objects.all() if request.user.is_staff else EntradaBlog.objects.filter(publicado=True)
    entrada = get_object_or_404(entradas, slug=slug)
    recientes = EntradaBlog.objects.filter(publicado=True).exclude(pk=entrada.pk)[:3]
    return render(request, 'blogDetalle.html', {'entrada': entrada, 'recientes': recientes})

@staff_required
def dashboard(request):
    peticiones = Peticion.objects.select_related('usuario').all().order_by('-fecha_creacion')
    usuarios = User.objects.filter(is_staff=False).order_by('username')
    administradores = User.objects.filter(is_staff=True).order_by('username')
    pedidos = Pedido.objects.select_related('usuario').prefetch_related('lineas').all().order_by('-fecha_creacion')
    contenido_sobre_mi = SobreMiContenido.objects.order_by('-actualizado').first()
    try:
        entradas_blog = EntradaBlog.objects.all()[:5]
    except (OperationalError, ProgrammingError):
        entradas_blog = []
    return render(request, 'dashboard.html', {
        'peticiones': peticiones,
        'usuarios': usuarios,
        'administradores': administradores,
        'pedidos': pedidos,
        'estados_pedido': Pedido.ESTADOS,
        'contenido_sobre_mi': contenido_sobre_mi,
        'entradas_blog': entradas_blog,
    })


@staff_required
def peticionesDetalles(request, pk):
    peticion = get_object_or_404(Peticion, pk=pk)
    
    if request.method == 'POST':
        respuesta = request.POST.get('respuesta')
        subject = f'Peticion LuJapon'
        from_email = settings.EMAIL_HOST_USER
        message = render_to_string('email/respuestaPeticion.txt', {
            'respuesta': respuesta,
        })
        send_mail(subject, message, from_email, [peticion.email], fail_silently=False)
        peticion.estado = 'respondida'
        peticion.save(update_fields=['estado'])
        return redirect('dashboard')
    return render(request, 'peticionesDetalles.html', {'peticion': peticion})
