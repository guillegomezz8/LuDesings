from django.shortcuts import render, redirect
from .models import Diseño
from .forms import DiseñoForm

# Create your views here.
def diseños(request):
    diseños = Diseño.objects.all()
    return render(request, 'diseños.html',{'diseños': diseños})

def crear_diseño(request):
    if request.method == 'POST':
        form = DiseñoForm(request.POST, request.FILES)
        if form.is_valid():
            diseño = form.save()
            return redirect('detalle_diseño', pk=diseño.pk)  # Redirigir a la vista de detalle del diseño recién creado
    else:
        form = DiseñoForm()
    return render(request, 'diseñoForm.html', {'form': form})