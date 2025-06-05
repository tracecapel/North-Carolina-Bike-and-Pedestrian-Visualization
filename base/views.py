from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import requests

# Home view
def home(request):
    """
    Render the home page.
    """

    
    
    return render(request, 'base/home.html')





def superset(request):
    """
    Render the Superset page.
    """
    return render(request, 'base/superset.html')

    
    








