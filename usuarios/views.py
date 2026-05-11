from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from diseños.models import DisenoLike, Pedido
from .forms import PerfilClienteForm, RegistroUsuarioForm
from .models import PerfilCliente

def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_staff:
                return redirect('dashboard')
            next_url = request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('diseños')
        else:
            messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
    return render(request, 'login.html')

def registro(request):
    if request.user.is_authenticated:
        return redirect('dashboard' if request.user.is_staff else 'cuenta')

    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save()
            PerfilCliente.objects.create(
                usuario=user,
                telefono=form.cleaned_data.get('telefono', ''),
                direccion=form.cleaned_data.get('direccion', ''),
            )
            login(request, user)
            messages.success(request, 'Cuenta creada correctamente.')
            return redirect('cuenta')
    else:
        form = RegistroUsuarioForm()

    return render(request, 'registro.html', {'form': form})

@login_required
def cuenta(request):
    if request.user.is_staff:
        return redirect('dashboard')

    perfil, _ = PerfilCliente.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        form = PerfilClienteForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tus datos se han actualizado.')
            return redirect('cuenta')
    else:
        form = PerfilClienteForm(instance=perfil)

    pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related('lineas').order_by('-fecha_creacion')
    likes = DisenoLike.objects.select_related('diseño').filter(usuario=request.user)

    return render(request, 'cuenta.html', {
        'form': form,
        'pedidos': pedidos,
        'likes': likes,
    })

@login_required
def pedidos_usuario(request):
    if request.user.is_staff:
        return redirect('dashboard')

    pedidos = Pedido.objects.filter(usuario=request.user).prefetch_related('lineas').order_by('-fecha_creacion')
    return render(request, 'pedidosUsuario.html', {'pedidos': pedidos})

def logout_view(request):
    logout(request)
    return redirect('diseños')
