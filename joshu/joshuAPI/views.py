import datetime
import re
import jwt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from joshu import settings
from .api_error_list import response_api_error
from .models import Task, JoshuUser, TaskFolder
from .serializers import (
    TaskListSerializer,
    JoshuUserSerializer, TaskFolderSerializer,
    TaskFolderCreateSerializer,
    TaskCreateSerializer,
    TaskUpdateSerializer,
    TaskFolderUpdateSerializer, TaskListData, ResponceError, AccessTokenSeriazels,
    TaskFolderListSerializer,
    TZSerializer
)
# from .permissions import IsOwnerOrReadOnly
from joshu.settings import SECRET_KEY, BOT_NAME
from django.utils.timezone import pytz
from joshuAPI.tasks import send_email_delegating_task


TELEG_URL='https://telegram.me'


def correct_date_converter(volume):
    date = float(volume) - 10800.0  # корректировка +3 часа МСК
    user_timezone = pytz.timezone(settings.TIME_ZONE)
    """ на выходе строка вида '1970-01-01T00:00:00+03:00' """
    return datetime.datetime.fromtimestamp(date, tz=user_timezone)

# API Task List CBV controller


class TaskListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskListSerializer
    authentication_classes = (JWTAuthentication,)

    @swagger_auto_schema(
        operation_id='task list view',

        manual_parameters=[
            openapi.Parameter(
                name='date', in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="<timestamp>",
                required=True
            ),
        ],
        responses={
            200: TaskListData(),
            400: ResponceError()
        },
        tags=['Task'],
    )
    def get(self, request, ):
        user = request.user

        date = request.GET['date']  # выдергиваем значение параметра date из запроса
        try:
            priority = request.GET['priority']
        except:
            priority = None

        if date == '0':
            # если в запросе передан '0', отдаем весь список
            # data_queryset = Task.objects.filter(folderId__task_folder_user=user)
            data_queryset = Task.objects.filter(task_user=user)
        else:
            # если в запросе передан метка времени, отдаем список
            # от сохраненного значения task_sinhro и до метки в запросе
            # и те Task у кого дата редактирования входит в даты запроса
            min_date = user.task_sinhro
            max_date = correct_date_converter(date)
            # data_queryset = Task.objects.filter(folderId__task_folder_user=user,
            #                                    dateTime__gte=min_date, dateTime__lt=max_date, priority=priority)
            data_queryset = Task.objects.filter(task_user=user,
                                                dateTime__gte=min_date, dateTime__lt=max_date,
                                                edit__gte=min_date, edit__lt=max_date, priority=priority)

        seriazer = TaskListSerializer(data_queryset, many=True)

        last_task_sinhro = user.task_sinhro.timestamp()  # предыдущее время синхронизации отправляем в запросе

        user_timezone = pytz.timezone(settings.TIME_ZONE)
        user.task_sinhro = datetime.datetime.now(tz=user_timezone)  # сохраняем текущее время синхронизации
        user.save()

        res = {
            "data": seriazer.data,
            "lastDate": int(last_task_sinhro),
        }
        return Response(res, status.HTTP_200_OK)

# API Joshu User registration / authorization CBV controller

class CreateJoshuUserAPIView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = JoshuUserSerializer

    @swagger_auto_schema(
        operation_id='user registration / authorization',
        security=[],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'uid': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='unique user id',
                ),
                'displayName': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='reserved'
                )
            }
        ),
        responses={
            200: AccessTokenSeriazels(),
            400: ResponceError()
        },
        tags=['JoshuUser']
    )
    def post(self, request):
        data = request.data
        current_user = JoshuUser.objects.filter(uid=data["uid"])
        """
        если uid - найден, обновляем токены
        """
        if current_user:
            user_obj = current_user[0]
            refresh = RefreshToken.for_user(user_obj)  # uid уникальный

            res = {
                "accessToken": str(refresh.access_token),
                "refreshToken": str(refresh),
            }
            return Response(res, status.HTTP_200_OK)
        else:
            """
            если uid - НЕ найден, создаем новые токены
            """
            serializer = JoshuUserSerializer(data=data)
            if not serializer.is_valid():
                return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            res = {
                "accessToken": str(refresh.access_token),
                "refreshToken": str(refresh),
            }
            return Response(res, status.HTTP_201_CREATED)


class JWTAuthenticationSafe(JWTAuthentication):
    def authenticate(self, request):
        try:
            return super().authenticate(request=request)
        except InvalidToken:
            return None

# API Refresh JWT TOKEN CBV controller

class RefreshTokenJoshuUserAPIView(APIView):
    # permission_classes = (IsAuthenticated, )
    permission_classes = (AllowAny,)
    authentication_classes = [JWTAuthenticationSafe]

    @swagger_auto_schema(
        operation_id='user refresh token',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'refresh': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='refresh token',
                )
            }
        ),
        responses={
            200: AccessTokenSeriazels(),
            400: ResponceError()
        },
        tags=['JoshuUser']
    )
    def post(self, request):
        data = request.data
        try:
            headers = request.headers["Authorization"]
            print(headers)
            my_pattern = re.compile(r"Bearer ([-_.\w\d]+)", re.S)  # Ищем токен в заголовке
            temp = my_pattern.findall(headers)

            if temp:
                """
                если не просрочен, выдергиваем user_id из токена access
                """
                try:
                    data = jwt.decode(temp[0], SECRET_KEY, algorithms=['HS256'])
                except:
                    """
                    если просрочен, выдергиваем user_id из токена refresh
                    """
                    data = jwt.decode(data["refresh"], SECRET_KEY, algorithms=['HS256'])

            else:
                res = {
                    "errors": response_api_error(1)
                }
                return Response(res, status.HTTP_400_BAD_REQUEST)

            user_name = data["user_id"]
            current_user = JoshuUser.objects.filter(uid=user_name)

            if current_user:
                user_obj = current_user[0]
                refresh = RefreshToken.for_user(user_obj)  # uid уникальный
                res = {
                    "accessToken": str(refresh.access_token),
                    "refreshToken": str(refresh),
                }
                return Response(res, status.HTTP_201_CREATED)
            else:
                res = {
                    "errors": response_api_error(2)
                }
                return Response(res, status.HTTP_400_BAD_REQUEST)
        except:
            res = {
                "errors": response_api_error(3)
            }
            return Response(res, status.HTTP_400_BAD_REQUEST)

# API Task Folder List CBV controller

class TaskFolderListView(generics.ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskFolderSerializer

    @swagger_auto_schema(
        operation_id='task folder list view',

        manual_parameters=[
            openapi.Parameter(
                name='date', in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="<timestamp>",
                required=True
            ),
        ],
        responses={
            200: TaskFolderListSerializer(),
            400: ResponceError()
        },
        tags=['TaskFolder']
    )
    def get(self, request, ):
        user = request.user

        date = request.GET['date']  # выдергиваем значение параметра date из запроса
        try:
            priority = request.GET['priority']
        except:
            priority = None

        if date == '0':
            # если в запросе передан '0', отдаем весь список
            data_queryset = TaskFolder.objects.filter(task_folder_user=user)
        else:
            # если в запросе передан метка времени, отдаем список
            # от сохраненного значения task_sinhro и до метки в запросе
            min_date = user.task_folder_sinhro
            max_date = correct_date_converter(date)
            data_queryset = TaskFolder.objects.filter(task_folder_user=user,
                                                      createDate__gte=min_date, createDate__lt=max_date,
                                                      edit__gte=min_date, edit__lt=max_date, priority=priority)

        seriazer = TaskFolderSerializer(data_queryset, many=True)

        last_task_folder_sinhro = user.task_folder_sinhro.timestamp()  # предыдущее время синхронизации отправляем в запросе

        user_timezone = pytz.timezone(settings.TIME_ZONE)
        user.task_folder_sinhro = datetime.datetime.now(tz=user_timezone)  # сохраняем текущее время синхронизации
        user.save()

        res = {
            "data": seriazer.data,
            "lastDate": int(last_task_folder_sinhro),
        }
        return Response(res, status.HTTP_200_OK)


# API Logout CBV controller

class LogoutJoshuUserAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(
        operation_id='user logout controller (empty function)',
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="user logout success"
            ),
            400: ResponceError()
        },
        tags=['JoshuUser']
    )
    def post(self, request):
        data = request.data

        res = {
            "data": {},
        }
        return Response(res, status.HTTP_200_OK)

#API set user time-zone CBV controller

class SetUserTZAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)
    serializer_class = TZSerializer

    @swagger_auto_schema(
        operation_id='set TZ for telegram bot joshu user view',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'tz': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='time zone, e.g "Europe/Moscow" full list in: pytz.all_timezones',
                )
            }
        ),
        responses={
            200: TZSerializer(),
            400: ResponceError()
        },
        tags=['JoshuUser']
    )

    def post(self, request):
        # check if we got mandatory data tz :
        try:
            _ = self.request.data['tz']
        except:
            res = {
                "errors": response_api_error(4)
            }
            return Response(res, status.HTTP_400_BAD_REQUEST)

        # get json data to serializer
        tz_serializer = TZSerializer(data=request.data)
        tz_serializer.is_valid(raise_exception=True)  # true

        # update telegram link
        joshu_user = JoshuUser.objects.get(id=self.request.user.id)

        # set timezone - tz to user
        joshu_user.tz = tz_serializer.validated_data['tz']
        joshu_user.save()

        res = {
            "user TZ is set to": str(tz_serializer.validated_data['tz'])
        }
        return Response(res, status.HTTP_200_OK)

# API generate Telegram chat bot link for authentication CBV controller

class GenTelegJoshuUserAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    @swagger_auto_schema(
        operation_id='Generate user link to Telegram bot controller',
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="user link to Telegram bot is ready, if any problem, regenerate Telegram link again"
            ),
            400: ResponceError()
        },
        tags=['JoshuUser']
    )

    def post(self, request):
        # update telegram link
        joshu_user = JoshuUser.objects.get(id=self.request.user.id)
        JoshuUser.gen_telegram_link(joshu_user)
        # joshu_user.save(update_fields=['chat_id', 'bot_link_key'])
        joshu_user.save()
        linkTelegram = f'{TELEG_URL}/{BOT_NAME}/?start={joshu_user.bot_link_key}'

        res = {
            "linkTelegram": str(linkTelegram)
        }
        return Response(res, status.HTTP_200_OK)

# API Logout from Telegram chat bot CBV controller

class ClrTelegChatIdAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    @swagger_auto_schema(
        operation_id='clear user link to Telegram bot controller',
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="user link to Telegram bot cleared, if you need it, regenerate Telegram link again"
            ),
            400: ResponceError()
        },
        tags=['JoshuUser']
    )
    def post(self, request):
        # clear telegram link - chat_id
        joshu_user = JoshuUser.objects.get(id=self.request.user.id)
        JoshuUser.clr_telegram_chat_id(joshu_user)
        joshu_user.save()

        res = {
            "data": {},
        }
        return Response(res, status.HTTP_200_OK)

# API Create Task CBV controller

class TaskCreateView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskCreateSerializer

    def get_queryset(self):
        joshu_user = JoshuUser.objects.get(id=self.request.user.id)
        return TaskFolder.objects.filter(task_folder_user=joshu_user)

    @swagger_auto_schema(
        operation_id='task create view',
        responses={
            200: TaskCreateSerializer(),
            400: ResponceError()
        },
        tags=['Task']
    )
    def post(self, request, *args, **kwargs):
        # custom validation here:

        # check if we got mandatory data id :
        try:
            _ = self.request.data['id']
        except:
            res = {
                "errors": response_api_error(4)
            }
            return Response(res, status.HTTP_400_BAD_REQUEST)

        # check if such task already exists:
        joshu_user = JoshuUser.objects.get(id=self.request.user.id)
        task_id = Task.objects.filter(id=self.request.data['id'], task_user=joshu_user)
        # query set not empty means such task id exists - error
        if task_id.exists():
            res = {
                "errors": response_api_error(5)
            }
            return Response(res, status.HTTP_400_BAD_REQUEST)

        # check other problems here
        # ...

        # get json data to serializer
        serializer = self.get_serializer(data=request.data)
        # finally call default validation
        serializer.is_valid(raise_exception=True)
        # go ahead with creation
        self.perform_create(serializer)

        res = {
            "Task": serializer.data,
        }
        return Response(res, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        # create task with id and link it to folder of folderId
        joshu_user = JoshuUser.objects.get(id=self.request.user.id)
        user_timezone = pytz.timezone(settings.TIME_ZONE)
        task_edit = datetime.datetime.now(tz=user_timezone)  # сохраняем текущее время
        serializer.save(task_user=joshu_user, folderId=self.request.data['folderId'], id=self.request.data['id'],
                        edit=task_edit)


# API Update or Delete Task CBV controller

class TaskPutDelView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskUpdateSerializer
    authentication_classes = (JWTAuthentication,)

    # update task put method
    @swagger_auto_schema(
        operation_id='task update view',
        request_body=TaskUpdateSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="task update success"
            ),
            400: ResponceError()
        },
        tags=['Task']
    )
    def put(self, request, pk):
        # look for task to be updated
        # select join to get task which belongs to this user
        # task_qs = Task.objects.filter(id=int(pk), folderId__task_folder_user__id=self.request.user.id)

        joshu_user = JoshuUser.objects.get(id=self.request.user.id)
        task_qs = Task.objects.filter(id=int(pk), task_user=joshu_user)

        # empty qs means no such task - error
        if not task_qs.exists():
            res = {
                "errors": response_api_error(6)
            }
            return Response(res, status.HTTP_400_BAD_REQUEST)

        serializer = TaskUpdateSerializer(task_qs[0], data=request.data)

        if serializer.is_valid():
            serializer.save()
            user_timezone = pytz.timezone(settings.TIME_ZONE)
            task_edit = datetime.datetime.now(tz=user_timezone)  # сохраняем текущее время
            current_task = task_qs[0]
            current_task.edit = task_edit
            current_task.save()
            res = {
                "Task": serializer.data,
            }
            return Response(res, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # delete task
    @swagger_auto_schema(
        operation_id='task delete view',
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="task delete success"
            ),
            400: ResponceError()
        },
        tags=['Task']
    )
    def delete(self, request, pk):
        # select join to get task which belongs to this user
        joshu_user = JoshuUser.objects.get(id=self.request.user.id)
        task_qs = Task.objects.filter(id=int(pk), task_user=joshu_user)
        if task_qs.exists():
            task_qs[0].delete()
            return Response(status=status.HTTP_200_OK)

        res = {
            "errors": response_api_error(6)
        }
        return Response(res, status.HTTP_400_BAD_REQUEST)


# API Create Task Folder CBV controller

class TaskFolderCreateView(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskFolderCreateSerializer
    authentication_classes = (JWTAuthentication,)

    # try to find such folder in db
    def get_queryset(self):
        joshu_user = JoshuUser.objects.get(id=self.request.user.id)
        return TaskFolder.objects.filter(task_folder_user=joshu_user, id=self.request.data['id'])

    @swagger_auto_schema(
        operation_id='task folder create view',
        responses={
            200: TaskFolderCreateSerializer(),
            400: ResponceError()
        },
        tags=['TaskFolder']
    )
    def post(self, request, *args, **kwargs):

        # custom validation here:
        # check if we got mandatory data id:
        try:
            _ = self.request.data['id']
        except:
            res = {
                "errors": response_api_error(7)
            }
            return Response(res, status.HTTP_400_BAD_REQUEST)

        #check if folder exists:
        user_task_folder_qs = self.get_queryset()

        # not empty query set means folder exists already - error
        if user_task_folder_qs.exists():
            res = {
                "errors": response_api_error(8)
            }
            return Response(res, status.HTTP_400_BAD_REQUEST)

        # check other problems here
        # ...

        # get json data to serializer
        serializer = self.get_serializer(data=request.data)
        # finally call default validation
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        res = {
            "TaskFolder": serializer.data,
        }
        return Response(res, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        joshu_user = JoshuUser.objects.get(id=self.request.user.id)
        user_timezone = pytz.timezone(settings.TIME_ZONE)
        task_folder_edit = datetime.datetime.now(tz=user_timezone)  # сохраняем текущее время
        # create task folder with id
        serializer.save(task_folder_user=joshu_user, id=self.request.data['id'], edit=task_folder_edit)

# API Update or Delete TaskFolder CBV controller

class TaskFolderPutDelView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskFolderUpdateSerializer
    authentication_classes = (JWTAuthentication,)

    # update task folder put method
    @swagger_auto_schema(
        operation_id='task folder update view',
        request_body=TaskFolderUpdateSerializer,
        responses={
            200: TaskFolderCreateSerializer(),
            400: ResponceError()
        },
        tags=['TaskFolder']
    )
    def put(self, request, pk):
        # look for task folder to be updated
        # select only folder which belong to this user
        joshu_user = JoshuUser.objects.get(id=self.request.user.id)
        task_folder_qs = TaskFolder.objects.filter(id=int(pk), task_folder_user=joshu_user)

        # empty qs means no such task - error
        if not task_folder_qs.exists():
            res = {
                "errors": response_api_error(9)     # The taskFolder with the specified "id" does not exists
            }
            return Response(res, status.HTTP_400_BAD_REQUEST)

        serializer = TaskFolderUpdateSerializer(task_folder_qs[0], data=request.data)

        if serializer.is_valid():
            serializer.save()
            user_timezone = pytz.timezone(settings.TIME_ZONE)
            time_edit = datetime.datetime.now(tz=user_timezone)  # сохраняем текущее время
            current_task_folder = task_folder_qs[0]
            current_task_folder.edit = time_edit
            current_task_folder.save()

            res = {
                "TaskFolder": serializer.data,
            }
            return Response(res, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # delete task folder
    @swagger_auto_schema(
        operation_id='task folder delete view',
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="task folder delete success"
            ),
            400: ResponceError()
        },
        tags=['TaskFolder']
    )
    def delete(self, request, pk):
        # look for task folder to be updated
        # select only folder which belong to this user
        joshu_user = JoshuUser.objects.get(id=self.request.user.id)
        task_folder_qs = TaskFolder.objects.filter(id=int(pk), task_folder_user=joshu_user)

        if task_folder_qs.exists():
            task_folder_qs[0].delete()
            return Response(status=status.HTTP_200_OK)

        res = {
            "errors": response_api_error(9)     # The taskFolder with the specified "id" does not exists
        }
        return Response(res, status.HTTP_400_BAD_REQUEST)

# API Transfer task CBV controller

class TransferTask(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    @swagger_auto_schema(
        operation_id='transfer_task',
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="Transfer task success"
            ),
            400: ResponceError()
        },
        tags=['Task']
    )
    def post(self, request, task_id):
        user = request.user
        data_queryset = Task.objects.filter(task_user=user, id=task_id)
        if data_queryset:
            current_task = data_queryset[0]
            send_email_delegating_task.delay(user.pk, current_task.tid, False)
            res = {
                "data": 'Transfer task success',
            }
            return Response(res, status.HTTP_200_OK)
        else:
            res = {
                "errors": response_api_error(6)  # 'The task with the specified "id" does not exist'
            }
            return Response(res, status.HTTP_400_BAD_REQUEST)

