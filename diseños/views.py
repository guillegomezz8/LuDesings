from django.shortcuts import render
from .models import Diseño

# Create your views here.
def diseños(request):
    diseños = Diseño.objects.all()
    return render(request, 'diseños.html',{'diseños': diseños})