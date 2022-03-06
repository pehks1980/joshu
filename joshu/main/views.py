from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import generic
from django.contrib import messages
from django.views.generic import UpdateView, CreateView, DeleteView

from joshuAPI.models import JoshuUser
from main.forms import SendForm
from main.models import AdmBotMessage, DataSendMessage
from celery.result import AsyncResult
from main.tasks import send_messages
from django.http import HttpResponse
import json
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import resolve_url
from joshu import settings


def index(request):
    context = {
        'title': 'Главная страница'
    }
    return render(request, 'index.html', context)


# ----------------
class RcLoginView(LoginView):
    template_name = 'profile/login.html'

    def get_success_url(self):
        return resolve_url(settings.LOGIN_REDIRECT_URL)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Вход пользователя'
        return context


class RcLogoutView(LoginRequiredMixin, LogoutView):
    template_name = 'profile/logout.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Выход пользователя'
        return context


# ----------------
@login_required
def all_message(request):
    all_messages = AdmBotMessage.objects.all()
    data_query = []  # дамп данных который пойдет на фронт

    for item_message in all_messages:
        all_send = DataSendMessage.objects.filter(message=item_message)
        data_item_query = {
            'name': item_message.name,
            'pk_messages': item_message.pk,
            'all_send': all_send
        }
        data_query.append(data_item_query)

    context = {
        'title': 'Все сообщения',
        'data_query': data_query
    }
    return render(request, 'messages_all.html', context)


@login_required
def message_detail(request, pk):
    pattern = '[\d]+'
    user_co = JoshuUser.objects.filter(chat_id__iregex=pattern).count()

    if request.method == 'POST':
        form = SendForm(pk, request.POST)
        task = send_messages.delay(pk)

        messages.add_message(request, messages.SUCCESS, 'Отсылаю пользователям...')

        context = {
            'form': form,
            'title': 'Сообщение детально',
            'current_message': AdmBotMessage.objects.get(pk=pk),
            'user_count': user_co,
            'task_id': task.task_id
        }
        return render(request, 'message_detail.html', context)

    else:
        form = SendForm(pk)

    context = {
        'form': form,
        'title': 'Сообщение детально',
        'current_message': AdmBotMessage.objects.get(pk=pk),
        'user_count': user_co
    }
    return render(request, 'message_detail.html', context)


class AdmBotMessageUpdate(LoginRequiredMixin, UpdateView):
    fields = '__all__'
    template_name = 'create_update_admbotmessage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['set_title'] = 'Редактирование cообщения'
        context['title'] = 'Редактирование cообщения'
        return context

    def get_queryset(self):
        return AdmBotMessage.objects.all()

    def get_success_url(self):
        return reverse_lazy('main_app:message_detail', kwargs={'pk': self.kwargs.get('pk')})


class AdmBotMessageCreate(LoginRequiredMixin, CreateView):
    model = AdmBotMessage
    template_name = 'create_update_admbotmessage.html'
    fields = '__all__'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['set_title'] = 'Создание cообщения'
        context['title'] = 'Создание cообщения'
        return context

    def get_success_url(self):
        # return reverse_lazy('blog_app:blog_detail', kwargs={'pk': self.kwargs.get('pk')})
        return reverse_lazy('main_app:messages_all')


class AdmBotMessageDelete(LoginRequiredMixin, DeleteView):
    model = AdmBotMessage
    success_url = reverse_lazy('main_app:messages_all')
    template_name = 'admbotmessage_confirm_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Удаление cообщения'
        context['set_title'] = 'Удаление cообщения'
        return context


# --------------------------------------------------------------
# функция для работы прогресс бара
def get_task_info(request):
    task_id = request.GET.get('task_id', None)
    if task_id is not None:
        task = AsyncResult(task_id)
        data = {
            'state': task.state,
            'result': task.result,
        }
        return HttpResponse(json.dumps(data), content_type='application/json')
    else:
        return HttpResponse('No job id given.')
