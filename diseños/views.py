from django.shortcuts import render, redirect, get_object_or_404
from .models import Diseño,Imagen
from .forms import DiseñoForm

# Create your views here.
def diseños(request):
    diseños = Diseño.objects.all()
    return render(request, 'diseños.html',{'diseños': diseños})

def crear_diseño(request):
    if request.method == 'POST':
        form = DiseñoForm(request.POST, request.FILES)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            descripcion = form.cleaned_data['descripccion']
            imagen_principal = form.cleaned_data['imagen_principal']
            imagenes_adicionales = request.FILES.getlist('imagenes_adicionales')

            diseño = Diseño.objects.create(nombre=nombre, descripccion=descripcion, imagen_principal=imagen_principal)

            for imagen_adicional in imagenes_adicionales:
                imagen_adicional_obj = Imagen.objects.create(imagen=imagen_adicional)
                diseño.imagenes_adicionales.add(imagen_adicional_obj)

            return redirect('diseños')  
    else:
        form = DiseñoForm()
    return render(request, 'diseñoForm.html', {'form': form})

def borrar_diseño(request, pk):
    diseño = get_object_or_404(Diseño, pk=pk)
    if request.user.is_superuser:
        diseño.delete()
        return redirect('diseños')   
    else:
        return render(request, '403.html')



