from django.db import models
from django.contrib import admin


class AdmBotMessage(models.Model):
    name = models.CharField(max_length=256, verbose_name="Короткое название")
    description = models.TextField(verbose_name='Содержание сообщения', blank=True)

    class Meta:
        verbose_name_plural = "Сообщения"
        verbose_name = "Сообщение"
        ordering = ['name']

    def __str__(self):
        return f"{self.name}"


@admin.register(AdmBotMessage)
class AdminMessage(admin.ModelAdmin):
    list_display = ('name', )


class DataSendMessage(models.Model):
    message = models.ForeignKey(AdmBotMessage, on_delete=models.CASCADE, verbose_name='Сообщение')
    date_time = models.DateTimeField(auto_now_add=True, verbose_name='Дата рассылки')

    class Meta:
        verbose_name_plural = "Даты рассылки"
        verbose_name = "Дата рассылки"
        ordering = ['date_time']

    def __str__(self):
        return f"{self.date_time}"


@admin.register(DataSendMessage)
class AdminDataSendMessage(admin.ModelAdmin):
    list_display = ('message', 'date_time')
