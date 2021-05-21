from authlib.integrations.base_client import OAuthError
from authlib.integrations.django_client import OAuth
from authlib.oauth2.rfc6749 import OAuth2Token
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from src import settings
from forecast import views
from time import sleep
import logging
from django.http import HttpResponse

logger = logging.getLogger('django_logger')

# You must initialize logging, otherwise you'll not see debug output.
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True


class OAuthMiddleware(MiddlewareMixin):

    def __init__(self, get_response=None):
        
        super().__init__(get_response)
        self.oauth = OAuth()

    def process_request(self, request):
        
        if settings.OAUTH_URL_WHITELISTS is not None:
            for w in settings.OAUTH_URL_WHITELISTS:
                logger.info(request.path)
                if request.path.startswith(w):
                    return self.get_response(request)

        # update_token parameter is used to refresh the access_token when it’s expired.
        def update_token(token, refresh_token, access_token):
            logger.info("refresh the access_token when it’s expired")
            logger.info(request.path)
            request.session['token'] = token
            return None

        # Use the OAuth configuration to initialize the OAuth client.
        sso_client = self.oauth.register(
            settings.OAUTH_CLIENT_NAME, overwrite=True, **settings.OAUTH_CLIENT, update_token=update_token
        )

        # Process OAuth callback
        # After the user authorizes the login, our server should fetch the access_token from the authorization server and store it in user session.

        if request.path.startswith('/signin-oidc'): 

            self.clear_session(request)
            logger.info("Authorize access token")
            logger.info(request.path)
            request.session['token'] = sso_client.authorize_access_token(request)
            

            if self.get_current_user(sso_client, request) is not None:
                sleep(0.1)
                redirect_uri = request.session.pop('redirect_uri', None)
       
                if redirect_uri is not None:
                    return redirect(redirect_uri)
                return redirect('/forecast')

        if request.session.get('token', None) is not None:
            current_user = self.get_current_user(sso_client, request)
            logger.info("User info:  %s" % current_user)
            logger.info(request.path)
            if current_user is not None:
                return self.get_response(request)

        # remember redirect URI for redirecting to the original URL.
        request.session['redirect_uri'] = request.path
        redirect_uri = request.build_absolute_uri('/signin-oidc')
        return sso_client.authorize_redirect(request, redirect_uri)

    # fetch current login user info
    # 1. check if it's in cache
    # 2. fetch from remote API when it's not in cache
    @staticmethod
    def get_current_user(sso_client, request):
        logger.info("check if user in cache")
        logger.info(request.path)
        token = request.session.get('token', None)
        if token is None or 'access_token' not in token:
            return None

        if not OAuth2Token.from_dict(token).is_expired() and 'user' in request.session:
            return request.session['user']

        try:
            logger.info("Fetch from remote API when it's not in cache")
            res = sso_client.get(settings.OAUTH_CLIENT['userinfo_endpoint'], token=OAuth2Token(token))
            logger.info(res)
            if res.ok:
                request.session['user'] = res.json()
                return res.json()
        except OAuthError as e:
            logging.error(e)
        return None

    @staticmethod
    def clear_session(request):
        try:
            del request.session['user']
            del request.session['token']
        except KeyError:
            pass

    def __del__(self):
        print('destroyed')




