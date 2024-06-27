from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseRedirect
from .models import Diseño,Imagen
from .forms import DiseñoForm
from django.http import JsonResponse

# Create your views here.
def es_administrador(user):
    return user.is_authenticated and user.is_staff

def diseños(request):
    orden = request.GET.get('orden', 'fecha_reciente')  # Valor por defecto es 'fecha_reciente'

    if orden == 'fecha_reciente':
        diseños = Diseño.objects.all().order_by('-fecha_subida')
    elif orden == 'fecha_antigua':
        diseños = Diseño.objects.all().order_by('fecha_subida')
    elif orden == 'popularidad':
        diseños = Diseño.objects.all().order_by('-popularidad')
    else:
        diseños = Diseño.objects.all().order_by('-fecha_subida')  # Valor por defecto

    return render(request, 'diseños.html',{'diseños': diseños, 'orden': orden})

@user_passes_test(es_administrador)
def crear_diseño(request):
    if request.method == 'POST':
        form = DiseñoForm(request.POST, request.FILES)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            descripcion = form.cleaned_data['descripccion']
            imagen_principal = form.cleaned_data['imagen_principal']
            imagenes_adicionales = form.cleaned_data['imagenes_adicionales']

            diseño = Diseño.objects.create(nombre=nombre, descripccion=descripcion, imagen_principal=imagen_principal)

            for imagen_adicional in imagenes_adicionales:
                imagen_adicional_obj = Imagen.objects.create(imagen=imagen_adicional)
                diseño.imagenes_adicionales.add(imagen_adicional_obj)

            return redirect('diseños')
    else:
        form = DiseñoForm()
    
    referer = request.META.get('HTTP_REFERER', '/')
    
    return render(request, 'diseñoCrear.html', {'form': form, 'referer': referer})

@user_passes_test(es_administrador)
def borrar_diseño(request, pk):
    diseño = get_object_or_404(Diseño, pk=pk)
    if request.user.is_superuser:
        diseño.delete()
        return redirect('diseños')   
    else:
        return render(request, '403.html')

@user_passes_test(es_administrador)   
def editar_diseño(request,pk):
    diseño = get_object_or_404(Diseño, pk=pk)
    if request.method == 'POST':
        form = DiseñoForm(request.POST, request.FILES, instance=diseño)
        if form.is_valid():
            diseño = form.save(commit=False)
            diseño.save()

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
    return render(request, 'diseñoEditar.html', {'form': form, 'diseño': diseño})


def detalle_diseño(request,pk):
    diseño = get_object_or_404(Diseño, pk=pk)
    imagenes = diseño.todas_las_imagenes()
    return render(request, 'diseñoDetalle.html',{'diseño': diseño,'imagenes': imagenes})

def like_diseno(request, diseno_id):
    if request.method == 'POST':
        diseno = get_object_or_404(Diseño, id=diseno_id)
        diseno.popularidad += 1
        diseno.save()
        return JsonResponse({'popularidad': diseno.popularidad})
    return JsonResponse({'error': 'Invalid request'}, status=400)