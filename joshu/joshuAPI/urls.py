from django.conf.urls import url
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import CreateJoshuUserAPIView, RefreshTokenJoshuUserAPIView, TaskFolderListView, LogoutJoshuUserAPIView, \
    TaskFolderCreateView, GenTelegJoshuUserAPIView, ClrTelegChatIdAPIView, TransferTask, SetUserTZAPIView

from .views import TaskListView, TaskCreateView, TaskPutDelView, TaskFolderPutDelView


app_name = 'joshuAPI'

urlpatterns = [
    # Task
    path('task/all/', TaskListView.as_view()),
    path('task_folder/all/', TaskFolderListView.as_view()),

    path('task/', TaskCreateView.as_view()),
    path('task/<int:pk>/', TaskPutDelView.as_view()),
    path('transfer_task/<int:task_id>/', TransferTask.as_view()),

    path('task_folder/', TaskFolderCreateView.as_view()),
    path('task_folder/<int:pk>', TaskFolderPutDelView.as_view()),


    # User
    path('user/auth/', CreateJoshuUserAPIView.as_view(), name='user_auth'),
    # set user tz
    path('user/time-zone/', SetUserTZAPIView.as_view(), name='set_user_tz'),
    # Logout
    path('user/logout/', LogoutJoshuUserAPIView.as_view(), name='user_logout'),
    # Telegram link regenerate
    path('user/teleg_link/', GenTelegJoshuUserAPIView.as_view(), name='teleg_link'),
    # Clear Telegram link
    path('user/clear_chat_id/', ClrTelegChatIdAPIView.as_view(), name='clr_teleg_chat_id'),
    # JWT
    path('token/refresh/', RefreshTokenJoshuUserAPIView.as_view(), name='token_refresh'),


]
