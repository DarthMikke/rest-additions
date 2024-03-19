import json
from django.http import HttpResponse, HttpRequest, JsonResponse
import django.db.models
from typing import Any, Union
from django.views import View
from django.db.models import Q
from django.urls import reverse
from django.shortcuts import render


def unimplemented(request, *args, **kwargs):
    return JsonResponse({"error": "Not yet implemented"}, status=501)


class APIViewBase(View):
    """
    Base class for serializing views, containing common parameters of child
    classes `CRUDView` and `ListView`.
    """

    model: django.db.models.Model = ...
    """model this view refers to
    """

    identifiers: list = ...
    """
    `list[list[tuple[str, dict]]]`) -- Description of how the model is to
    be retrieved from the database. This parameter is a list of tuples with
    URL query variable and model field name.
    """

    links: Union[dict, None] = None
    """
    `dict[str, tuple[str, dict[str, str]]]` -- links to include in the *_links*
    field in the HAL response
    links: dict[str, tuple[str, dict[str, str]]]

    dict with string keys and tuple definitions.

    Each link is defined by a tuple containing:
        - the Django view name as the first element
        - as the second element, dict with django URL parameter names
          as keys and parameter values as dict values. 
    """

    def generate_links(self, *args, **kwargs):
        """
        Generate links based on the self.links parameter, for use in
        HAL `links` object.

        See self.links for valid link definitions.
        """
        try:
            return {
                x: reverse(y[0], kwargs={
                    a: b.format(*args, **kwargs) for (a, b) in y[1].items()
                })
                for x, y in self.links.items()
            }
        except KeyError as e:
            print(dir(e))
            raise KeyError(f"\
            An error occured. Check if the key {repr(e.args[0])} \
            exists in URL args/kwargs, or if the link definition is a tuple.")


class SingleViewBase(APIViewBase):
    def setup(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """Set up `self.instance`.

        Sets up the view according to the `identifiers` object, `request`, and
        URL arguments.
        """

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
            return self.notFound


class ListViewBase(APIViewBase):
    def setup(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        super().setup(request, *args, **kwargs)

        filter_query = None

        if not type(self.identifiers) == list:
            raise TypeError("ListView.identifier has to be a list of lists.")

        for query in self.identifiers:
            if not type(query) == list:
                raise TypeError("ListView.identifier has to be a list of lists.")
            for identifier in query:
                partial_query = {}

                if (isinstance(identifier, tuple)):
                    (url_identifier, model_identifier) = identifier
                else:
                    url_identifier = identifier
                    model_identifier = identifier
                
                if url_identifier == 'USERID':
                    partial_query[model_identifier] = request.user.id
                elif url_identifier in kwargs.keys():
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


class CRUDView(SingleViewBase):
    """Endpoint implementing CRUD operations on models matching the query.

    Supported methods are `GET`, `PUT`, `PATCH`, `DELETE`.
    """

    instance: django.db.models.Model = ...
    """`django.db.models.Model` - instance of the model
    """

    notFound = JsonResponse({"error": "Not found"}, status=404)

    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        response = self.instance.serialize()
        if self.links is not None:
            response["_links"] = self.generate_links(*args, **kwargs)

        return JsonResponse(response)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """Unimplemented."""
        return unimplemented()

    def put(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        # Check if every defined field exists in the request
        # @TODO: Move field validation to a separate deserializer
        parsed_body = json.loads(request.body)

        for field in self.model.SerializerMeta.deserializer_fields:
            if type(field) is tuple:
                field = field[0]
            if field not in parsed_body.keys():
                raise KeyError(f"Required value {field} is not provided.")
        # Check if every field provided in request exists in the model definition
        for field in parsed_body.keys():
            put_fields = [x[0] if (type(x) is tuple) else x for x in self.put_fields]
            if field not in put_fields:
                raise KeyError(f"Provided value {field} is not defined.")
        
        # Overwrite
        try:
            for field in self.model.SerializerMeta.deserializer_fields:
                if type(field) == tuple:
                    (keyword, transform) = field
                    parsed_body[keyword] = transform(parsed_body[keyword])
            instance = self.model(**parsed_body)
        except Exception as e:
            return JsonResponse({"error": repr(e)}, status=422)
        
        # Save the instance
        try:
            instance.save()
        except Exception as e:
            return JsonResponse({"error": repr(e)}, status=500)

        # Return 204
        return HttpResponse(None, status=204)

    def patch(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        # Retrieve instance or 404
        if not self.instance:
            return self.notFound
        
        parsed_body = json.loads(request.body)
        
        # Check if every field provided in request exists in the model definition
        for field in parsed_body.keys():
            if field not in self.writable_fields:
                raise KeyError(f"Provided value {field} is not defined.")
        
        for field in self.model.SerializerMeta.deserializer_fields:
            if field not in parsed_body.keys():
                continue
            if type(field) == tuple:
                (keyword, transform) = field
                parsed_body[keyword] = transform(parsed_body[keyword])
        # Overwrite
        for field in parsed_body.keys():
            try:
                self.instance.__setattr__(field, parsed_body[field])
            except Exception as e:
                raise KeyError(f"Provided value {field} is not defined.")
        
        # Save the instance
        try:
            self.instance.save()
        except Exception as e:
            return JsonResponse({"error": repr(e)}, status=500)

        # Return 204
        return HttpResponse(None, status=204)

    def delete(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        # Retrieve instance or 404
        if not self.instance:
            return self.notFound

        # Delete the instance
        try:
            self.instance.delete()
        except Exception as e:
            return JsonResponse({"error": repr(e)}, status=500)

        return HttpResponse(None, status=204)


class ListView(ListViewBase):
    """Set self.instances to the list of the instances of the
    `model` that match the user's query.

    Allowed methods: `GET`.
    """

    instances: "list[django.db.models.Model]" = ...
    """instances of the model"""

    paginated: bool = False
    """whether to add pagination info to the response or not"""

    total: int = ...
    """number of total instances matching the query"""

    identifiers: list = ...
    """list of identifiers to filter by, with values
    """

    embedded: dict = ...
    """dictionary of items to include in the _embed field of the response
    """

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
    
    def get(self, request, *args, **kwargs):
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
        if type(self.embedded) == dict:
            response["_embedded"] = self.embedded
        
        print(response)
        
        return JsonResponse(response)


class TemplateView(SingleViewBase):
    """Retrieve an object from the database based on the URL query, and render
    a template with it.
    """

    instance: "django.db.models.Model" = ...
    """instance of the model
    """

    notFound = HttpResponse("Not found.", status=404)
    """Response to serve in case no object instance corresponds to the query. 
    """

    template: str
    """Template name to use for this view.

    TODO: Allow user to specify custom theme.
    """

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        response = render(request, self.template, {
            "model": self.instance
        })

        return response

