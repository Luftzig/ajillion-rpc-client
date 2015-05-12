import logging

from rpcclient.exceptions import NoHandlerError
from rpcclient.handlers import RequestHandler, AsyncRequestHandler


__author__ = 'yoav.luft@ajillionmax.com'

log = logging.getLogger(__name__)


class MethodProxy:
    default_handlers = [
        (lambda url, method, **kwargs: method.endswith('.task'), AsyncRequestHandler),
        (lambda *args, **kwargs: True, RequestHandler)
    ]

    def __init__(self, url, headers, token, method_name, configuration=None):
        self._method = method_name
        self._url = url
        self._headers = headers
        self._token = token
        self._configuration = configuration

    def __call__(self, _deserializer=None, **kwargs):
        handler = self._get_handler_instance(**kwargs)
        response = self._get_response(handler, **kwargs)
        deserializer = self._get_deserializer(_deserializer)
        if deserializer is not None:
            return deserializer.create_from(response)
        return response

    def __getattr__(self, inner_item):
        new_method = self._method + "." + inner_item
        return self.__class__(self._url, self._headers, self._token, new_method, self._configuration)

    def _get_response(self, handler, **kwargs):
        return handler.handle(**kwargs)

    def _get_deserializer(self, deserializer):
        if deserializer is not None:
            return deserializer
        if self._configuration and 'deserializers' in self._configuration:
            deserializers = self._configuration['deserializers']
            if hasattr(deserializers, 'create_from'):
                return deserializers
            elif isinstance(deserializers, dict):
                return deserializers.get(self._method, None)
            elif callable(deserializers):
                return deserializers(self._method)
        return None

    def _get_handler_instance(self, **kwargs):
        handlers = (self._configuration and self._configuration.get('handlers', None)) or MethodProxy.default_handlers
        for (can_handle, handler) in handlers:
            if can_handle(self._url, self._method, **kwargs):
                return handler(self._method, self._url, self._headers, self._token, self._configuration, **kwargs)
        else:
            raise NoHandlerError('No handler supplied that can handle method=%s, url=%s, params=%s'
                                 % (self._method, self._url, str(kwargs)))
