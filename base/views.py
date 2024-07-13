from django.shortcuts import render, redirect, get_object_or_404
from .forms import PeticionesForm
from django.contrib.auth.decorators import user_passes_test
from .models import Peticion
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

# Create your views here.
def es_administrador(user):
    return user.is_authenticated and user.is_staff

def base(request):
    return render(request, 'base.html')

def sobreMi(request):
    return render(request, 'sobreMi.html')

def peticionesForm(request):

    if request.method == 'POST':
        form = PeticionesForm(request.POST)
        if form.is_valid():
            asunto = form.cleaned_data['asunto']
            email = form.cleaned_data['email']
            peticion = form.cleaned_data['peticion']

            peticion = Peticion.objects.create(asunto=asunto,email=email,peticion=peticion)
        
            return redirect('sobreMi')
    else:
        form = PeticionesForm()
    
    referer = request.META.get('HTTP_REFERER', '/')

    return render(request, 'peticionesForm.html', {'form': form,'referer': referer})

@user_passes_test(es_administrador)
def dashboard(request):
    peticiones = Peticion.objects.all()
    usuarios = User.objects.all()
    return render(request, 'dashboard.html', {'peticiones': peticiones, 'usuarios': usuarios})


@user_passes_test(es_administrador)
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
        return redirect('dashboard')
    return render(request, 'peticionesDetalles.html', {'peticion': peticion})