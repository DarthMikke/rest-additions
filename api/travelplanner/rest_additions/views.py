from django.http import HttpResponse, HttpRequest, JsonResponse
from typing import Any, Union
from django.views import View
from django.db.models import Q
from django.urls import reverse


def unimplemented(request, *args, **kwargs):
    return JsonResponse({"error": "Not yet implemented"}, status=501)


class BaseAPIView(View):
    model = ...
    """
    @var ModelBase - model this view refers to
    """

    identifiers: list = ...
    """
    @var list[list[tuple[str, dict]]] - list of tuples with URL query variable and model field name
    """

    links: Union[dict, None] = None
    """
    @var dict - links to include in the *_links* field in the HAL response
    """

    def generate_links(self, *args, **kwargs):
        return {
            x: reverse(y[0], kwargs={
                a: b.format(*args, **kwargs) for (a, b) in y[1].items()
            })
            for x, y in self.links.items()
        }


class CRUDView(BaseAPIView):
    """
    If method is GET, PATCH, DELETE, set self.instance to the instance of the
    model the user is trying to get.
    """

    instance = ...
    """
    @var ModelBase - instance of the model
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
        response = self.instance.serialize()
        if self.links is not None:
            response["_links"] = self.generate_links(*args, **kwargs)

        return JsonResponse(response)

    def post(self, request, *args, **kwargs):
        return unimplemented()

    def put(self, request, *args, **kwargs):
        return unimplemented()

    def patch(self, request, *args, **kwargs):
        return unimplemented()

    def delete(self, request, *args, **kwargs):
        return unimplemented()


class ListView(BaseAPIView):
    """
    If method is GET, set self.instances to the list of the instances of the
    model the user is trying to get.
    """

    instances = ...
    """
    @var list[ModelBase] - instances of the model.
    """

    paginated = False
    """
    @var bool - whether to add pagination info to the response or not.
    """

    total = ...

    per_page = 20
    
    def generate_links(self, *args, **kwargs):
        links = super().generate_links(*args, **kwargs)

        if self.paginated:
            links = dict(links, **{
                'first': '',
                'prev': '',
                'next': '',
                'final': '',
            })
        
        return links

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        super().setup(request, *args, **kwargs)

        filter_query = None
        for query in self.identifiers:
            for identifier in query:
                partial_query = {}

                if (isinstance(identifier, tuple)):
                    (url_identifier, model_identifier) = identifier
                else:
                    url_identifier = identifier
                    model_identifier = identifier
                
                if url_identifier in kwargs.keys():
                    partial_query[model_identifier] = kwargs[url_identifier]
                
                if partial_query:
                    filter_query = (filter_query | Q(**partial_query)) \
                        if filter_query is not None else Q(**partial_query)
        
        try:
            self.instances = self.model.objects.filter(filter_query)
            self.total = self.instances.count()
            if self.total > self.per_page:
                self.paginated = True
                self.page = int(request.GET['page']) if 'page' in request.GET else 1
                first = (self.page - 1)*self.per_page
                last = min(first + self.per_page, self.instances.count())
                self.instances = self.instances.all()[first:last]
        except Exception as e:
            return JsonResponse({"original_exception": repr(e)}, status=404)
    
    def get(self, request, *args, **kwargs):
        print(repr(request.GET))
        items = [x.serialize() for x in self.instances]
        response = {
            'count': len(items),
            'items': items,
        }
        if self.paginated:
            response['total'] = self.total
            response['offset'] = self.page * self.per_page
        if self.links is not None:
            response["_links"] = self.generate_links(*args, **kwargs)
        
        print(response)
        
        return JsonResponse(response)

