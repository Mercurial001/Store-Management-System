from django.shortcuts import redirect
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth.models import User
from functools import wraps


def unauthenticated_user(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('homepage')
        # if request.user.is_authenticated and request.user.groups.exists():
        #     group = request.user.groups.all()[0].name
        #     if group == 'admin':
        #         return redirect('newsletterPanel')
        #     else:
        #         return redirect('frontpage')
        else:
            return view_func(request, *args, **kwargs)
    return wrapper_func


def admin_group_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if the user is authenticated and is a member of the 'admin' group
        if request.user.is_authenticated and request.user.groups.filter(name='admin').exists():
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden("You don't have permission to access this page.")

    return _wrapped_view
