import logging
import requests
import hashlib
from .errors import IpernityError, IpernityAPIError
from .cache import SimpleCache
from . import keys

CACHE = None

log = logging.getLogger(__name__)

def enable_cache(cache_object=None):
    """ enable caching
    Parameters:
    -----------
    cache_object: object, optional
        A Django compliant cache object. If None (default), a SimpleCache
        object is used.
    """
    global CACHE
    CACHE = cache_object or SimpleCache()


def disable_cache():
    """Disable cachine capabilities
    """
    global CACHE
    CACHE = None


def _clean_params(params):
    for k, v in params.items():
        if isinstance(v, bool):
            params[k] = 1 if v else 0
        if isinstance(v, int):
            params[k] = str(v)
    return params


def call_api(api_method, api_key=None, api_secret=None, signed=False,
             authed=False, http_post=True, auth_handler=None, **kwargs):
    ''' file request to ipernity API

    Parameters:
        method: The API method you want to call
        signed: if request need to add signature
        authed: if user auth needed
        auth_handler: auth_handler
        http_post: if set True, would use POST method, otherwise, GET
            some methods only support GET request, for example: api.methods.get

    Default:
        * format is JSON
    '''
    # api_keys handling
    if not api_key:
        api_key = keys.API_KEY
    if not api_secret:
        api_secret = keys.API_SECRET
    if not api_key or not api_secret:
        raise IpernityError('No Ipernity API keys been set')
    kwargs['api_key'] = api_key
    kwargs = _clean_params(kwargs)

    url = "http://api.ipernity.com/api/%s/%s" % (api_method, 'json')
    
    from . import auth
    auth_handler = auth_handler or auth.AUTH_HANDLER
    if authed and not auth_handler:
        raise IpernityError('no auth_handler provided')
    elif auth_handler and isinstance(auth_handler, auth.OAuthAuthHandler):
            kwargs = auth_handler.sign_params(url, kwargs, http_post)
    elif signed or authed:  # signature handling
        if authed:
            kwargs['auth_token'] = auth_handler.auth_token['token']
        api_sig = sign_keys(api_secret, kwargs, api_method)
        kwargs['api_sig'] = api_sig

    # send the request
    if http_post:  # POST
        if 'file' in kwargs:  # upload file handling
            log.debug('sending file ' + kwargs['file'])
            with open(kwargs['file'], 'rb') as fobj:
                files = {'file': fobj}
                r = requests.post(url, data=kwargs, files=files)
        else:
            r = requests.post(url, data=kwargs)
    else:  # GET
        # cache only works in GET request
        if CACHE is None:
            r = requests.get(url, params=kwargs)
        else:
            r = CACHE.get(url) or requests.get(url, params=kwargs)
            if url not in CACHE:
                CACHE.set(url, r)
    log.debug('Request returned %s', r)
    r.raise_for_status()  # raise error if necessary, response_code != 2xx

    resp = r.json()
    # check the response, if error happends, raise exception
    api = resp['api']
    if api['status'] == 'error':
        err_mesg = api['message']
        # add more info to err_mesg
        err_mesg += '\nAPI: %s \nPayload: %s' % (api_method, kwargs)
        err_code = int(api['code'])
        raise IpernityAPIError(err_code, err_mesg)

    return resp


def sign_keys(api_secret, kwargs, method=None):
    ''' request signature: Some API methods require signature.
    Support Request signature and Authorization link signature

    Parameters:
        api_secret: api_secret key
        kwargs: api parameters to be signed
        method: if provided, request signature, otherwise auth link signature

    The request signature corresponds to the md5 of a string
    composed of the following parameters concatenated
    each other without spaces:
        alphabetical ordered parameters followed by their values,
        the called method, (for Request Signature)
        your API key secret.

    Note: kwargs would be sorted in alphabetical order when convert to string
    '''
    param_keys = sorted(kwargs.keys())
    param_keys
    sig_str = ''.join(['%s%s' % (k, kwargs[k]) for k in param_keys])
    # append method & api_secret
    sig_str = sig_str + (method if method else '') + api_secret
    api_sig = hashlib.md5(sig_str.encode('utf-8')).hexdigest()
    return api_sig
