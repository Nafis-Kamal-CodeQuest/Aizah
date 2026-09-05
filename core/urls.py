from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('api/inquiry/', views.submit_inquiry, name='submit_inquiry'),
]