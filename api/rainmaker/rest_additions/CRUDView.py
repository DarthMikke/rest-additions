from django.http import HttpResponse, HttpRequest, JsonResponse
from typing import Any
from django.views import View


def unimplemented(request, *args, **kwargs):
    return JsonResponse({"error": "Not yet implemented"}, status=501)


class CRUDView(View):
    """
    If method is GET, PATCH, DELETE, set self.instance to the instance of the
    model the user is trying to get.
    """
    
    model = ... 
    """
    @var ModelBase - model this view refers to
    """

    instance = ...
    """
    @var ModelBase - instance of the model
    """

    identifiers: list = ...
    """
    @var list - list of tuples with URL query variable and model field name
    """

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        super().setup(request, *args, **kwargs)
        
        model_kwargs = {}
        for identifier in self.identifiers:
            if (isinstance(identifier, tuple)):
                (url_identifier, model_identifier) = identifier
            else:
                url_identifier = identifier
                model_identifier = identifier
            
            if url_identifier in kwargs.keys():
                model_kwargs[model_identifier] = kwargs[url_identifier]
        
        try:
            self.instance = self.model.objects.get(**model_kwargs)
        except Exception as e:
            return JsonResponse({"original_exception": repr(e)}, status=404)

    def get(self, request, *args, **kwargs):
        return JsonResponse(self.instance.serialize())

    def post(self, request, *args, **kwargs):
        return unimplemented()

    def put(self, request, *args, **kwargs):
        return unimplemented()

    def patch(self, request, *args, **kwargs):
        return unimplemented()

    def delete(self, request, *args, **kwargs):
        return unimplemented()
