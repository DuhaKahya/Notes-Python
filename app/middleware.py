from django.shortcuts import redirect
from django.urls import reverse

class RedirectIfNotAuthenticatedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.user.is_authenticated:
            path = request.path
            if not path.startswith(reverse('login')) and not path.startswith(reverse('register')):
                return redirect(reverse('login'))
        return response
