from django.urls import path
from . import views

app_name = 'careers'

urlpatterns = [
    path('', views.careers, name='careers'),
    path('apply/', views.apply, name='apply'),
]
