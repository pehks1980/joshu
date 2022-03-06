from django.contrib import admin

from joshuAPI.models import Task, JoshuUser, TaskFolder


class TaskFolderAdmin(admin.ModelAdmin):
    list_display = ('task_folder_user', 'fid', 'id', 'title', 'color', 'createDate', 'edit')
    search_fields = ('task_folder_user', 'fid', 'id', 'title', 'color', 'createDate', 'edit')


admin.site.register(TaskFolder, TaskFolderAdmin)


class TaskAdmin(admin.ModelAdmin):
    list_display = ('task_user', 'tid', 'id', 'text', 'dateTime', 'folderId', 'createDate', 'edit')
    search_fields = ('task_user', 'tid', 'id', 'text', 'dateTime', 'folderId', 'createDate', ' edit')


admin.site.register(Task, TaskAdmin)


class JoshuUserAdmin(admin.ModelAdmin):
    list_display = ('uid', 'admin', 'staff', 'chat_id', 'telegram_ch_admin')


admin.site.register(JoshuUser, JoshuUserAdmin)
