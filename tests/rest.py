from unittest import TestCase
from ipernity_api import rest, errors, keys
from ipernity_api import auth


class RESTTest(TestCase):
    def test_call_api(self):
        method = 'test.echo'
        echo = 'hello'

        resp = rest.call_api(method, echo=echo)
        self.assertEqual(resp['echo'], echo)

    def test_call_api_raise(self):
        with self.assertRaises(errors.IpernityAPIError):
            method = 'unknow_method'
            # send an unknow request, should raise Exception
            rest.call_api(method)

    def test_implicit_keys(self):
        # save key for later restoring
        api_key = keys.API_KEY
        api_secret = keys.API_KEY

        method = 'test.hello'
        # set keys to None, should raise exception
        keys.set_keys(None, None)
        with self.assertRaisesRegex(errors.IpernityError,
                                     'No Ipernity API keys'):
            rest.call_api(method)

        # explict pass keys should OK
        rest.call_api(method, api_key=api_key, api_secret=api_secret)

        # set back keys, should be OK now
        keys.set_keys(api_key, api_secret)
        rest.call_api(method)

    def test_call_api_signed(self):
        method = 'auth.getFrob'
        authhandler = auth.AUTH_HANDLER
        auth.set_auth_handler(None)
        # calling to a signed method without signed request
        # should recive exception
        with self.assertRaisesRegex(errors.IpernityAPIError, 'Signature'):
            rest.call_api(method)

        # this time should OK
        rest.call_api(method, signed=True)
        auth.set_auth_handler(authhandler)

    def test_get_request_cache(self):
        method = 'test.hello'
        rest.enable_cache()
        for i in range(20):
            rest.call_api(method, http_post=False)
        rest.disable_cache()
