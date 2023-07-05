from django.http import HttpResponse
from typing import Union

class PublicPermissions:
    def __init__(self, view):
        self.view = view
    
    def get(self, *_, **__) -> Union[HttpResponse, bool]:
        return True
    
    def post(self, *_, **__) -> Union[HttpResponse, bool]:
        return True
    
    def put(self, *_, **__) -> Union[HttpResponse, bool]:
        return True
    
    def patch(self, *_, **__) -> Union[HttpResponse, bool]:
        return True
    
    def delete(self, *_, **__) -> Union[HttpResponse, bool]:
        return True


class NotFoundPermissions:
    notFound = HttpResponse("Not found", status=404)
    
    def __init__(self, view):
        self.view = view

    def get(self, *_, **__) -> Union[HttpResponse, bool]:
        return self.notFound
    
    def post(self, *_, **__) -> Union[HttpResponse, bool]:
        return self.notFound
    
    def put(self, *_, **__) -> Union[HttpResponse, bool]:
        return self.notFound
    
    def patch(self, *_, **__) -> Union[HttpResponse, bool]:
        return self.notFound
    
    def delete(self, *_, **__) -> Union[HttpResponse, bool]:
        return self.notFound


class AuthMixin:
    # Default permission is that all routes are public.
    permission = None

    def dispatch(self, request, *args, **kwargs):
        try:
            self.permission = self.permission(self)
        except Exception as e:
            raise e

        try:
            permission_checker = self.permission.__getattribute__(request.method.lower())
        except Exception as e:
            raise e
        
        permitted = permission_checker(request, *args, **kwargs)
        if permitted == True:
            return super().dispatch(request, *args, **kwargs)
        
        return permitted


