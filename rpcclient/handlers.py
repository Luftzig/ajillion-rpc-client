from concurrent.futures._base import Executor
from concurrent.futures.thread import ThreadPoolExecutor
import json
import logging
from uuid import uuid4
import time

import requests

from rpcclient.exceptions import RemoteFailedError, RemoteTimeoutError


__author__ = 'yoav.luft@ajillionmax.com'

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 60 * 5
SLEEP_INTERVAL_SECONDS = 5


class RequestHandler:
    """
    This class defines how requests should be handled.
    It also provides default implementation for serial.
    """

    # noinspection PyUnusedLocal
    def __init__(self, method, url, headers, token, configuration=None, **kwargs):
        self.method = method
        self.url = url
        self.headers = headers
        self.token = token
        self.configuration = configuration

    def handle(self, **kwargs):
        """
        Synchronously call the target url with method, headers and token.
        :param kwargs: All keyword arguments will be sent in the request in the "params" field.
        :return: the raw response.
        """
        kwargs["token"] = self.token
        request_id = uuid4().int
        if 'method' in kwargs:
            method = kwargs['method']
            del kwargs['method']
        else:
            method = self.method
        payload = {
            "method": method,
            "params": kwargs,
            "jsonrpc": "2.0",
            "id": request_id
        }
        json_dumps = json.dumps(payload)
        response = requests.post(self.url, data=json_dumps, headers=self.headers)
        if response.status_code != 200 or response.json().get("error"):
            raise RemoteFailedError(response=response)
        return response.json()["result"]


class AsyncRequestHandler(RequestHandler):
    """
    Handler for retrieving reports using Ajillion's `asynchronous task API`_.
    The handler itself can run synchronously (blocking until it has report) or asynchronously and return
    :class:`concurrent.futures.Future`

    .. _asynchronous task API: http://clients.ajillionmax.com/ajillion_api.html#Report
    """

    def __init__(self, *args, **kwargs):
        """
        Accepts the same arguments as :func:`RequestHandler.__init__`
        """
        super(AsyncRequestHandler, self).__init__(*args, **kwargs)
        self._max_failures = self.configuration.get('max_failures') or 1
        self.delegate = RequestHandler(*args, **kwargs)
        self._num_failures = 0

    def handle(self, _timeout=None, _sleep_interval=None, _async=False, _max_failures=None, **kwargs):
        """
        :param _timeout: Request timeout in seconds, default to the `timeout` value in the client's configuration or 300
         seconds
        :param _sleep_interval: Wait interval between checks for the remote procedure's status. Defaults to the value in
         the client's configuration or 5 seconds
        :param _async: If false or None this call will block until the remote has returned a response or timeout. Else,
         this call will return immediately with a Future encapsulating the execution. If the parameter is an instance of
         :class:`concurrent.futures.Executor` this executor will be used for running the async, else, if the client
         configuration has `async_executor` it will be used, otherwise new
         :class:`concurrent.futures.thread.ThreadPoolExecutor` will be used.
        :param _retries: The number of consecutive failures to retrieve the report status that should be ignored.
         Defaults to the `max_failures` parameter in configuration or 1.
        :param kwargs: Keyword arguments will be passed to the remote as the `params` field in the request.
        :return: The raw response from the RPC target, or a future that will contain it.
        """
        self._max_failures = _max_failures if _max_failures is not None else self._max_failures
        if _async or self.configuration.get('run_async'):
            if isinstance(_async, Executor):
                executor = _async
            else:
                executor = self.configuration.get('async_executor') or ThreadPoolExecutor(max_workers=1)
            return executor.submit(self._internal_handle, _timeout=_timeout, _sleep_interval=_sleep_interval, **kwargs)
        else:
            return self._internal_handle(_timeout, _sleep_interval, **kwargs)

    def _internal_handle(self, _timeout=None, _sleep_interval=None, **kwargs):
        timeout = _timeout or (self.configuration and self.configuration.get('timeout', None)) or TIMEOUT_SECONDS
        sleep_interval = _sleep_interval \
                         or (self.configuration and self.configuration.get('sleep_interval', None)) \
                         or SLEEP_INTERVAL_SECONDS
        token = self.delegate.handle(**kwargs)['report_token']
        timeout = time.time() + timeout
        log.debug("Doing poll-wait for report " + self.method + " with token " + token)
        while not self._report_ready(token):
            time.sleep(sleep_interval)
            if time.time() > timeout:
                log.error('Timeout of ' + str(timeout) + ' seconds expired!')
                raise RemoteTimeoutError()
        return self.delegate.handle(method='report.data.get', report_token=token)

    def _report_ready(self, token):
        try:
            response = self.delegate.handle(method='report.status.get', report_token=token)
            status = response['status'] == 'ready'
            # Will not reach this if error!
            self._num_failures = 0
            return status
        except:
            if self._should_reraise_status_get_error():
                raise RemoteFailedError('No status in response')

    def _should_reraise_status_get_error(self):
        self._num_failures += 1
        return self._num_failures > self._max_failures
