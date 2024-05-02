from django.shortcuts import render, redirect
from .forms import PeticionesForm
from django.contrib.auth.decorators import user_passes_test
from .models import Peticion

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
    return render(request, 'peticionesForm.html', {'form': form})

@user_passes_test(es_administrador)
def peticionesList(request):
    peticiones = Peticion.objects.all()
    return render(request, 'peticionesList.html', {'peticones': peticiones})