"""task_manager URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import re_path
from django.contrib import admin
from django.urls import include, path

# from drf_spectacular.views import (
#   SpectacularAPIView,
#   SpectacularSwaggerView,
#   SpectacularRedocView
# )

from processes import views

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r"^auth/", include("djoser.urls.base")),
    re_path(r"^auth/", include("djoser.urls.jwt")),
    # These don't work, possibly due to a problem with django-filter
    # See https://github.com/tfranzel/drf-spectacular/issues/155
    #path('api-docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    #path('api-docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    #path('api-docs/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
    path('', include('processes.urls')),
    re_path(r'^', views.FrontendAppView.as_view()),
]
