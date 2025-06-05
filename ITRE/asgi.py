"""
ASGI config for ITRE project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""



import os
import django

from fastapi import FastAPI
from django.core.asgi import get_asgi_application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ITRE.settings')

application = get_asgi_application()

from api.nmcoast_api import app as fastapi_app  