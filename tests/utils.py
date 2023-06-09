import os
import logging

from ipernity_api import auth

log = logging.getLogger(__name__)

class TestCaseError(Exception):
    pass


AUTH_FILE_PATH = '.tests.ipernity_auto_auth.tmp'
AUTH_HANDLER = None


def auth_in_browser(auth_cls, perms):
    ''' OAuth in Browser and return auth object
    Implement:
        1. oauth support url redirect after auth done
        2. we can setup a HTTP server to get such token
    '''
    port = 5678
    redirt_url = "http://localhost:%d/oac" % port

    # get auth url
    if auth_cls is auth.OAuthAuthHandler:
        log.debug('Creating OAuth handler')
        auth_handler = auth_cls(callback=redirt_url, perms=perms)
    else:
        log.debug('Creating auth handler')
        auth_handler = auth_cls(perms=perms)
    url = auth_handler.get_auth_url()
    # open url in browser
    import webbrowser
    log.debug('Opening URL ' + url)
    print('Add ":%d" after "localhost" in browser URL' % port)
    webbrowser.open_new(url)
    
    if auth_cls is auth.DesktopAuthHandler:
        input('Press <Enter> to continue...')
        auth_handler.getToken()
    
    else:
        
        # setup a temporary http server to get oath_token
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                # parse url to get auth_token
                #import urllib.parse
                #p = urllib.parse.urlparse(self.path)
                #q = urllib.parse.parse_qs(p.query)
                #auth_token = q['oauth_token'][0]
                #auth_verifier = q['oauth_verifier'][0]
                # save back to auth handler
                auth_handler.verify()
                # send response to webpage
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write("Auth OK. Please close this page.")
                self.wfile.close()

        httpd = HTTPServer(("", port), Handler)

        httpd.handle_request()  # just handle on request

    return auth_handler


def auto_auth():
    global AUTH_HANDLER
    if AUTH_HANDLER:
        return
    if not os.path.exists(AUTH_FILE_PATH):
        perms = {'doc': 'delete',
                 'blog': 'delete',
                 'network': 'delete', }
        handler = auth_in_browser(auth.OAuthAuthHandler, perms)
        # save handler
        handler.save(AUTH_FILE_PATH)
    handler = auth.AuthHandler.load(AUTH_FILE_PATH)
    auth.set_auth_handler(handler)
    AUTH_HANDLER = handler
