from rainmaker.rest_additions.permissions import *


class TransactionPermissions(NotFoundPermissions):
    def get(self, request, *args, **kwargs):
        if request.user.is_staff:
            return True


class AccountPermissions(NotFoundPermissions):
    def get(self, request, *_, **__) -> Union[HttpResponse, bool]:
        if not request.user.is_authenticated:
            return self.notFound
        
        if not self.view:
            return self.notFound
        
        if not 'instance' in dir(self.view):
            return self.notFound
        
        if (request.user.id == self.view.instance.book.owner.id
            or
            request.user.id in [x.id for x in self.view.instance.book.shared_with.all()]
            ):
            return True
    
    def post(self, *args, **kwargs) -> Union[HttpResponse, bool]:
        return self.get(*args, **kwargs)
    
    def put(self, *args, **kwargs) -> Union[HttpResponse, bool]:
        return self.get(*args, **kwargs)
    
    def patch(self, *args, **kwargs) -> Union[HttpResponse, bool]:
        return self.get(*args, **kwargs)
    
    def delete(self, request, *args, **kwargs) -> Union[HttpResponse, bool]:
        return self.get(request, *args, **kwargs)
