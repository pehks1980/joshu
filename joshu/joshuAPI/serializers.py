import datetime

import pytz
from drf_yasg import openapi
from rest_framework import serializers

from joshu import settings
from joshuAPI.models import Task, JoshuUser, TaskFolder
from drf_yasg.utils import swagger_serializer_method


class DateTimeSeriasers(serializers.BaseSerializer):
    def to_representation(self, instance):
        date_time = int(instance.timestamp())
        return date_time


class TaskListSerializer(serializers.ModelSerializer):
    dateTime = DateTimeSeriasers()  # Однотипные задачи, решаем с помощью одной ф-ции
    createDate = DateTimeSeriasers()  #
    edit = DateTimeSeriasers()  #

    class Meta:
        model = Task
        exclude = ['tid', 'task_user', 'enabled', 'overdue', 'shed_time', 'last_fired_at', 'text_edit',
                   'dateTimeEdit', 'overdue_done']


class JoshuUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = JoshuUser
        fields = '__all__'


class TaskFolderSerializer(serializers.ModelSerializer):
    createDate = DateTimeSeriasers()  # Однотипные задачи, решаем с помощью одной ф-ции
    edit = DateTimeSeriasers()  #

    class Meta:
        model = TaskFolder
        exclude = ['fid', 'task_folder_user', 'title_edit']


# CRUD Task TaskFolder serializers

class TaskFolderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskFolder
        exclude = ['fid', 'task_folder_user', 'edit', 'title_edit']
        ref_name = None  # запрет передачи названия функции на фронт


class TaskFolderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskFolder
        exclude = ['id', 'task_folder_user', 'fid', 'title_edit']
        ref_name = None  # запрет передачи названия функции на фронт


class TaskCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        exclude = ['tid', 'task_user', 'edit', 'enabled', 'overdue', 'shed_time', 'last_fired_at', 'text_edit',
                   'dateTimeEdit', 'overdue_done']
        ref_name = None  # запрет передачи названия функции на фронт


class TaskUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        exclude = ['id', 'tid', 'task_user', 'enabled', 'overdue', 'shed_time', 'last_fired_at', 'text_edit',
                   'dateTimeEdit', 'overdue_done']
        ref_name = None  # запрет передачи названия функции на фронт


# ----- Serializers function -----

class TaskList(serializers.ModelSerializer):
    class Meta:
        model = Task
        exclude = ['tid', 'task_user', 'enabled', 'overdue', 'shed_time', 'last_fired_at', 'text_edit',
                   'dateTimeEdit', 'overdue_done']
        ref_name = None  # запрет передачи названия функции на фронт


class TaskListData(serializers.Serializer):
    # date = TaskList(many=True)
    date = serializers.ListSerializer(child=TaskList(), read_only=True)
    lastDate = serializers.IntegerField(help_text="<timestamp>", read_only=True)

    class Meta:
        ref_name = None  # запрет передачи названия функции на фронт


class ErrorsList(serializers.Serializer):
    code = serializers.IntegerField(read_only=True, help_text='error code')
    message = serializers.CharField(read_only=True, help_text='error message')

    class Meta:
        ref_name = None  # запрет передачи названия функции на фронт


class ResponceError(serializers.Serializer):
    errors = serializers.ListSerializer(child=ErrorsList())

    class Meta:
        ref_name = None  # запрет передачи названия функции на фронт


class AccessTokenSeriazels(serializers.Serializer):
    accessToken = serializers.CharField(read_only=True, help_text='new access Token')
    refreshToken = serializers.CharField(read_only=True, help_text='new refresh Token')

    class Meta:
        ref_name = None  # запрет передачи названия функции на фронт


class TaskFolderList(serializers.ModelSerializer):
    class Meta:
        model = TaskFolder
        exclude = ['fid', 'task_folder_user', 'title_edit']
        ref_name = None  # запрет передачи названия функции на фронт


class TaskFolderListSerializer(serializers.Serializer):
    date = serializers.ListSerializer(child=TaskFolderList(), read_only=True)
    lastDate = serializers.IntegerField(help_text="<timestamp>", read_only=True)

    class Meta:
        ref_name = None  # запрет передачи названия функции на фронт


from timezone_field.rest_framework import TimeZoneSerializerField

class TZSerializer(serializers.Serializer):
    tz = TimeZoneSerializerField()
    class Meta:
        # model = Task
        # fields = ('tz',)
        ref_name = None  # запрет передачи названия функции на фронт


