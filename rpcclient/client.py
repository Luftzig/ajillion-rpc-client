import json
import logging
from uuid import uuid4

import requests

from rpcclient.exceptions import LoginError
from rpcclient.method_proxy import MethodProxy


__author__ = 'yoav.luft@ajillionmax.com'

log = logging.getLogger(__name__)


class RpcClient(object):
    """
    JSON-RPC client encapsulating a session.
    The client uses proxy methods for structuring the correct request, so executing the code
    ``client.advertisers.get(**kwargs)`` will execute the remote method 'advertisers.get' with ``kwargs`` as
    the parameters for the request. The authentication token is also added automatically.
    Requesting the 'task' method (e.g. ``client.advertiser.report.task()``)

    The constructor of the client accepts a configuration dictionary which can include the following values:

    host
     The host name
    port
     The port to use
    username
     The username to use for login. Will be passed to the login method
    password
     The password to use for login. Will be passed to the login method
    url
     The exact API URL. If not provided, ``host + "api/"`` will be used
    headers
     A dictionary of headers to attach to each request. Default to "Content-Type: application/json"
    login
     An override for the default login method. Either a callable that accepts ``username, password`` parameters and
     return the authentication that will be sent in each request, or the token string itself.
    handlers
     An iterable of 2-tuples, the first one is a callable in the form ``can_handle(url, method, **kwargs)`` which will
     passed to the request handler and return True if the handler can handle the request; The second is the handler
     class that will be instantiated with ``method, url, headers, token, configuration, **kwargs`` and then immediately
     calling it's ``handle`` method.
    timeout
     The default timeout in seconds for async requests.
    sleep_interval
     The default wait time in seconds between async requests.
    deserializers
     Either a deserializer object (with ``create_from`` method), a dictionary of method names mapping to deserializers
     or function that given a method name returns a deserializer object. If deserializer was found it will be used to
     deserialize the response. *A deserializer can also be passed on the call as `_deserializer=` argument*

    """

    def __init__(self, host=None, port=None, username=None, password=None, configuration: dict=None):
        """
        Creates new RpcClient
        All required parameters can be given on the configuration dictionary instead.
        :param host: The host name to send requests to, e.g. "http://my.server/". Required, must include trailing /
        :param port: Not supported
        :param username: The username to use for login, Required
        :param password: The password to use for login, Required
        :param configuration: Optional dictionary of configurations, see class documentation for possible values
        """
        self.configuration = configuration or {}
        self._host = (host or self.configuration['host'])
        self._port = port or self.configuration.get('port') or ''
        self._url = self.configuration.get('url') or self._build_url()
        self._headers = self.configuration.get('headers') or {'content-type': 'application/json'}
        username, password = username or self.configuration['username'], password or self.configuration['password']
        self.token = self.login(username, password)

    def _build_url(self):
        schema = self._host.split('://')[0] if '://' in self._host else 'http'
        hostname = (self._host.split('://')[1] if '://' in self._host else self._host).strip('/')
        if self._port:
            hostname += ':' + str(self._port)
        return schema + '://' + hostname + "/api/"

    def login(self, username, password):
        if 'login' in self.configuration:
            login = self.configuration['login']
            if callable(login):
                return login(username, password)
            elif isinstance(login, str):
                return login
        else:
            return self._rpc_login(username, password)

    def _rpc_login(self, username, password):
        uuid = uuid4().int
        payload = {
            "method": "login",
            "params": {
                "username": username,
                "password": password},
            "jsonrpc": "2.0",
            "id": uuid}
        response = requests.post(self._url, data=json.dumps(payload), headers=self._headers).json()
        if response.get('id') == uuid and response.get('error') is None:
            log.info("RpcClient successfully connected to {} as {}".format(self._host, username))
            return response['result']['token']
        log.error("Failed to login, response: " + repr(response))
        raise LoginError(response=response)

    def __getattr__(self, item):
        return MethodProxy(self._url, self._headers, self.token, item, self.configuration)

    def get_host(self):
        return self._host

