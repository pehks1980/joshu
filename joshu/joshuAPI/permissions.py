from rest_framework import permissions

"""
class IsOwnerOrReadOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if obj.task_user:
            return obj.task_user == request.user or request.user.is_superuser
        return obj.username == request.user
"""