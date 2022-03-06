from django.urls import path
from main.views import message_detail, get_task_info, RcLoginView, RcLogoutView, all_message, AdmBotMessageUpdate, \
    AdmBotMessageCreate, AdmBotMessageDelete

app_name = 'main_app'

urlpatterns = [
    # Message
    path('messages_all/', all_message, name='messages_all'),
    path('message_detail/<int:pk>/', message_detail, name='message_detail'),
    path('message_update/<int:pk>/', AdmBotMessageUpdate.as_view(), name='message_update'),
    path('message_create/', AdmBotMessageCreate.as_view(), name="message_create"),
    path('message_delete/<int:pk>/', AdmBotMessageDelete.as_view(), name="message_delete"),

    # Celery-result
    path('get-task-info/', get_task_info),

    # Profile
    path('login/', RcLoginView.as_view(), name='login'),
    path('logout/', RcLogoutView.as_view(), name='logout'),
]
