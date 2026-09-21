from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('distributor/', include('accounts.urls')),
    path('', include('core.urls')),
]

# Serve media files via Django view (handles both standard domain and cPanel preview URL)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^~siteqaxw/media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]