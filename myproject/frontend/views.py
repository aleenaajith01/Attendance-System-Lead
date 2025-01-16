from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'frontend/index.html')

def dashboard(request):
    return render(request, 'frontend/dashboard.html')

def tables(request):
    return render(request, 'frontend/tables.html')

def billing(request):
    return render(request, 'frontend/billing.html')

def virtual_reality(request):
    return render(request, 'frontend/virtual_reality.html')

def rtl(request):
    return render(request, 'frontend/rtl.html')

def notifications(request):
    return render(request, 'frontend/notifications.html')

def profile(request):
    return render(request, 'frontend/profile.html')

def sign_in(request):
    return render(request, 'frontend/sign_in.html')

def sign_up(request):
    return render(request, 'frontend/sign_up.html')