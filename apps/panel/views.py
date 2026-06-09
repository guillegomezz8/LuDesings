from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import OperationalError, ProgrammingError
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from apps.cuentas.decorators import staff_required
from apps.sitio.models import EntradaBlog, Peticion, SobreMiContenido
from apps.tienda.models import Pedido


@staff_required
def dashboard(request):
    peticiones = Peticion.objects.select_related('usuario').order_by('-fecha_creacion')
    usuarios = User.objects.filter(is_staff=False).order_by('username')
    administradores = User.objects.filter(is_staff=True).order_by('username')
    pedidos = (
        Pedido.objects.select_related('usuario')
        .prefetch_related('lineas')
        .order_by('-fecha_creacion')
    )
    contenido_sobre_mi = SobreMiContenido.objects.order_by('-actualizado').first()
    try:
        entradas_blog = EntradaBlog.objects.all()[:5]
    except (OperationalError, ProgrammingError):
        entradas_blog = []

    return render(request, 'panel/dashboard.html', {
        'peticiones': peticiones,
        'usuarios': usuarios,
        'administradores': administradores,
        'pedidos': pedidos,
        'estados_pedido': Pedido.ESTADOS,
        'contenido_sobre_mi': contenido_sobre_mi,
        'entradas_blog': entradas_blog,
    })


@staff_required
def peticion_detalle(request, pk):
    peticion = get_object_or_404(Peticion, pk=pk)

    if request.method == 'POST':
        respuesta = request.POST.get('respuesta')
        message = render_to_string(
            'panel/email/respuesta_peticion.txt',
            {'respuesta': respuesta},
        )
        send_mail(
            'Petición LuJapon',
            message,
            settings.EMAIL_HOST_USER,
            [peticion.email],
            fail_silently=False,
        )
        peticion.estado = 'respondida'
        peticion.save(update_fields=['estado'])
        return redirect('dashboard')

    return render(request, 'panel/peticion_detalle.html', {'peticion': peticion})
