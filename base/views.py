from django.shortcuts import render

# Create your views here.
def base(request):
    return render(request, 'base.html')

def sobreMi(request):
    return render(request, 'sobreMi.html')