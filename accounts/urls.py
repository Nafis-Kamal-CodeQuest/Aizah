from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    # Auth
    path('login/',     views.distributor_login,     name='distributor_login'),
    path('logout/',    views.distributor_logout,    name='distributor_logout'),

    # Dashboard
    path('dashboard/', views.distributor_dashboard, name='distributor_dashboard'),

    # Ordering
    path('catalog/',              views.distributor_catalog,       name='distributor_catalog'),
    path('orders/',               views.distributor_order_history, name='order_history'),
    path('orders/<int:pk>/',      views.distributor_order_detail,  name='order_detail'),
]
