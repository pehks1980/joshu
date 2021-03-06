#from django.conf.urls import url
from django.urls import include, re_path as url
from django.contrib import admin
from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from telegram_bot.views import TelegramBotView
from main.views import index

schema_view = get_schema_view(
    openapi.Info(
        title="Joshu API",
        default_version='v1',
        description="Joshu API v1",
        # terms_of_service="https://www.google.com/policies/terms/",
        # contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    url(r'^$', index, name='index'),
    path('admin/', admin.site.urls),

    # API
    path('api/v1/', include('joshuAPI.urls', namespace='joshu_api')),

    # Swagger
    url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # Telegram_bot
    path('webhooks/telegram_bot/', csrf_exempt(TelegramBotView.as_view())),

    # MainApp
    path('main/', include('main.urls', namespace='main_app')),

    # CeleryProgress
    path('celery-progress/', include('celery_progress.urls')),

]
