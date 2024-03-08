from django.shortcuts import render, redirect
from .models import Diseño,Imagen
from .forms import DiseñoForm

# Create your views here.
def diseños(request):
    diseños = Diseño.objects.all()
    return render(request, 'diseños.html',{'diseños': diseños})

def crear_diseño(request):
    form = DiseñoForm(request.POST, request.FILES)
    if request.method == 'POST':
        form = DiseñoForm(request.POST, request.FILES)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            descripcion = form.cleaned_data['descripccion']
            imagen_principal = form.cleaned_data['imagen_principal']
            imagenes_adicionales = request.FILES.getlist('imagenes_adicionales')

            # Guardar imagen principal
            imagen_principal_obj = Imagen.objects.create(imagen=imagen_principal)

            # Crear diseño
            diseño = Diseño.objects.create(nombre=nombre, descripccion=descripcion, imagen_principal=imagen_principal_obj)

            # Guardar imágenes adicionales
            for imagen_adicional in imagenes_adicionales:
                imagen_adicional_obj = Imagen.objects.create(imagen=imagen_adicional)
                diseño.imagenes_adicionales.add(imagen_adicional_obj)

            return redirect('diseños')  # Redirigir a la vista de detalle del diseño recién creado
    else:
        form = DiseñoForm()
    return render(request, 'diseñoForm.html', {'form': form})


