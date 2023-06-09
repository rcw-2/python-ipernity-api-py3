'''
Applications can request permissions on the following items:

    Photos/video/docs: permissions for photos/videos/docs posted.
    Articles: permissions for articles.
    Contact: permissions on the contacts.
    Profile: permissions on the user's profile.

    The requested permission can be:
        read : grants read-only access to user's items, even private.
        write : permits the modification of the user's items (and also grants read permission.).
        delete : permits the deletion of the user's items (and also grants write and read permission.).


A connection URL is built like this:
http://www.ipernity.com/apps/authorize?api_key=[api_key]&perm_X=[perm]&api_sig=[api_sig]
    [api_key] : your API key.
    [api_sig] : this request signature built using your secret.
    [doc] : the requested permission for photos/videos/docs. (read/write/delete).
    [blog] : the requested permission for articles. (read/write/delete).
    [network] : the requested permission for the contacts (read/write/delete).
    [profile] : the requested permission for the user's profile (read/write).

In the case of an authentication request for a desktop application, a frob parameter will have to be added.
http://www.ipernity.com/apps/authorize?api_key=[api_key]&perm_X=[perm]&frob=[frob]&api_sig=[api_sig]

'''
import logging
import urllib
import json
from abc import abstractmethod
from . import keys
from . import rest
from .ipernity import User, Auth

USER_AUTH_URL = 'http://www.ipernity.com/apps/authorize'

OAUTH_REQUEST_TOKEN_URL = 'http://www.ipernity.com/apps/oauth/request'
OAUTH_USER_AUTH_URL = 'http://www.ipernity.com/apps/oauth/authorize'
OAUTH_ACCESS_TOKEN_URL = 'http://www.ipernity.com/apps/oauth/access'

AUTH_HANDLER = None

log = logging.getLogger(__name__)

class AuthError(Exception):
    pass


class AuthHandler(object):
    def __init__(self, api_key=None, api_secret=None, perms=None, auth_token=None):
        '''
        Parameters:
            perms: is a dict consist of 'TYPE': 'read/write/delete'
                TYPE can be: doc, blog, network, profile
        '''
        self.api_key = api_key or keys.API_KEY
        self.api_secret = api_secret or keys.API_SECRET
        if not self.api_key or not self.api_secret:
            raise AuthError('No api_key or api_secret given')

        if perms:  # sanity check for permissions
            perm_types = ['doc', 'blog', 'network', 'post', 'profile']
            perm_modes = ['read', 'write', 'delete']
            for k in perms.keys():
                if k not in perm_types:
                    raise AuthError('Unknown permission type: %s' % k)
                if perms[k] not in perm_modes:
                    raise AuthError('Unknown permission mode %s for %s' % (perms[k], k))
        self.perms = perms
        self.auth_token = auth_token

        self.frob = None

    def getmeta(self):
        ''' get meta info about AuthHandler '''
        return {
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'perms': self.perms,
            'auth_token': self.auth_token,
        }

    def save(self, fname):
        ''' save Handler to a file '''
        fp = open(fname, 'w')
        data = {
            'class': self.__class__.__name__,
            'meta': self.getmeta(),
        }
        fp.write(json.dumps(data))
        fp.close()

    @staticmethod
    def load(fname):
        ''' Handler loaded from file '''
        with open(fname) as auth:
            data = json.loads(auth.read())
        meta = data['meta']
        classname = data['class']
        # find the class through globals() and init with **meta, then return
        # auth handler instance
        return globals()[classname](**meta)

    @abstractmethod
    def get_auth_url(self):
        ''' get auth url

        this method need to be overrided
        '''

    @abstractmethod
    def sign_params(*args, **kwargs):
        ''' sign paramters '''

    def compose_url(self, **kwarg):
        ''' compose url for auth

        parameters:
            **kwarg: additional parameters can be provided,
                for example: frob, callback
        '''
        params = {}
        params['api_key'] = self.api_key  # add api_key
        # need to add 'perm_' prefix to permission type
        perms = {'perm_' + k: v for k, v in self.perms.items()}
        params.update(perms)  # append permissions
        params.update(kwarg)  # additional parameters
        # auth url need api_sig
        api_sig = rest.sign_keys(self.api_secret, params)
        params['api_sig'] = api_sig
        query = urllib.parse.urlencode(params)
        # composite url
        url = USER_AUTH_URL + '?' + query
        return url

    def getToken(self, frob=None):
        ''' get token from frob '''
        if frob is None:
            frob = self.frob
        resp = rest.call_api('auth.getToken',
                             api_key=self.api_key,
                             api_secret=self.api_secret,
                             frob=frob,
                             signed=True)
        self.auth_token = resp['auth']
        return self.auth_token

    def getUser(self):
        ''' get User of this AuthHanlder '''
        token = getattr(self, 'auth_token') or getattr(self, 'oauth_token')
        if not token:
            raise AuthError('No token in Handler')
        authobj = Auth.get(auth_handler=self, auth_token=token)
        user_id = authobj.user['user_id']
        return User(user_id=user_id)


class WebAuthHandler(AuthHandler):
    '''WebAuthHanlder: auth class for web application

    Steps:
        1. Redirect the user to the authentication page
        2. Get back the frob
        3. Exchange the frob for a token

    Note: web callback URL is registered in ipernity.com
    when applying for API key
    (Authentication method: Web)

    Once authenticated, the member (its browser) is automatically
    redirected to your callback URL with the frob parameter.
    For example: http://www.yoursite.com/callback.php?frob=123456789-0ad5e2a8
    This frob is a disposable one-time use authentication ticket.
    This ticket remains valid for a few minutes only and must be exchanged
    for an auth_token authentication token .
    '''
    def get_auth_url(self):
        return self.compose_url()


class DesktopAuthHandler(AuthHandler):
    '''DesktopAuthHandler: auth class for non-web application which has no callback.
    '''
    def _get_frob(self):
        # get frob
        log.debug('Calling API method auth.getFrob')
        resp = rest.call_api('auth.getFrob',
                             api_key=self.api_key,
                             api_secret=self.api_secret,
                             signed=True)
        # TODO: should we create a AUTH object here
        frob = resp['auth']['frob']
        log.debug('Call returned %s', frob)
        return frob
    
    def get_auth_url(self):
        if not self.frob:
            self.frob = self._get_frob()
        return self.compose_url(frob=self.frob)

#import urllib.parse
import random
import time


def escape(s):
    """Escape a URL including any /."""
    return urllib.parse.quote(s, safe='~')


def _utf8_str(s):
    """Convert unicode to utf-8."""
    #if isinstance(s, unicode):
    #    return s.encode("utf-8")
    #else:
    return str(s)


def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return str(int(time.time()))


class OAuthAuthHandler(AuthHandler):
    def __init__(self, callback=None, oauth_token=None, oauth_token_secret=None,
                 *arg, **kwarg):
        AuthHandler.__init__(self, *arg, **kwarg)
        self.callback = callback
        self.oauth_token = oauth_token
        self.oauth_token_secret = oauth_token_secret

    @staticmethod
    def _normalized_parameters(params):
        """Return a string that contains the parameters that must be signed."""
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v)))
                      for k, v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def _build_signature(self, url, params, token=None, post=False):
        ''' signature OAuth request '''
        # private key to signature
        # consist of "consumer secret&token secret"
        key = '%s&' % escape(self.api_secret)
        if token:
            key += escape(token)
        # string to be signed consist of 3 parts:
        # 1. HTTP request method, uppercase, i.e. HEAD, GET, POST
        # 2. request URL
        # 3. normalized request parameters
        # Each item is encoded and separated by an '&' character
        sig = ('POST' if post else 'GET',
               url,
               self._normalized_parameters(params))
        raw = '&'.join(map(escape, sig))
        # HMAC object.
        import hmac
        import binascii

        #try:
        import hashlib  # 2.5
        hashed = hmac.new(bytes(key, 'ascii'), raw.encode('utf-8'), hashlib.sha1)
        #except:
        #    import sha  # Deprecated
        #    hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]

    def _request(self, url, verify=False):
        ''' fire the request to url, and save the oauth token

        if token given, this is a access token verify request.
        '''
        params = {
            'oauth_consumer_key': self.api_key,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
        }
        # callback is not needed when do verify
        if self.callback and not verify:
            params['oauth_callback'] = self.callback
        if verify:  # verify the oauth_token
            params['oauth_token'] = self.oauth_token
            token_secret = self.oauth_token_secret
        else:
            token_secret = None
        # get signature
        oauth_signature = self._build_signature(url, params, token_secret)
        params['oauth_signature'] = oauth_signature
        # compose URL
        req_url = url + '?' + urllib.parse.urlencode(params)
        # send request and save auth token
        log.debug('Sending request ' + req_url)
        resp = urllib.request.urlopen(req_url)
        oauth_token_resp = dict(urllib.parse.parse_qsl(resp.read().decode('utf-8')))
        #oauth_token_resp = urllib.parse.parse_qs(resp.read())
        log.debug('Result: %s', oauth_token_resp)
        self.oauth_token = oauth_token_resp['oauth_token']
        self.oauth_token_secret = oauth_token_resp['oauth_token_secret']

    def get_auth_url(self):
        # first get a oauth token
        self._request(OAUTH_REQUEST_TOKEN_URL)
        # compose the url
        params = {}
        params['oauth_token'] = self.oauth_token
        perms = {'perm_' + k: v for k, v in self.perms.items()}
        params.update(perms)
        url = OAUTH_USER_AUTH_URL + '?' + urllib.parse.urlencode(params)
        return url

    def verify(self):
        ''' verify the access token '''
        self._request(OAUTH_ACCESS_TOKEN_URL, verify=True)

    def getmeta(self):
        # Oauth need to save oauth_token_secret too
        meta = AuthHandler.getmeta(self)
        meta.pop('auth_token')
        meta['oauth_token'] = self.oauth_token
        meta['oauth_token_secret'] = self.oauth_token_secret
        return meta

    def sign_params(self, url, kwargs, post=False):
        ''' accept request parameters and return Oauth signed paramters

        Parameters:
        -----
            url: request url
            kwargs:
        '''
        # Oauth basic params
        params = {
            'oauth_consumer_key': self.api_key,
            'oauth_token': self.oauth_token,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
        }
        # add input params
        try:
            kwargs.pop('api_key')
        except KeyError:
            pass
        params.update(kwargs)
        # get signature
        oauth_signature = self._build_signature(url, params, self.oauth_token_secret, post)
        params['oauth_signature'] = oauth_signature

        return params


def set_auth_handler(handler):
    global AUTH_HANDLER
    AUTH_HANDLER = handler
