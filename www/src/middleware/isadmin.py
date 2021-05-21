from django.contrib.auth.views import redirect_to_login
from django.utils.deprecation import MiddlewareMixin 
from django.shortcuts import redirect

class IsAdminMiddleware(MiddlewareMixin):
    def process_request(self, request):
        url_for_admin = ['curvas','caudalimetros','senales','consumo','modelos','avisos']

        for url in url_for_admin:
            if request.path.startswith('/'+url+'/'):
                if 'cps-forecast-role' not in request.session['user']:
                    request.session['user']['cps-forecast-role']="not-admin"
                if request.session['user']['cps-forecast-role']!="admin":
                    return redirect("/")
        # Continue processing the request as usual:
        return None


