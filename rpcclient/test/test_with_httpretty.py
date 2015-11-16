import concurrent
from concurrent.futures._base import Future
import json
from threading import Barrier
import time
import unittest
import requests_mock
from rpcclient.client import RpcClient
from rpcclient.deserialize import DictDeserializer
from rpcclient.exceptions import RemoteFailedError
from rpcclient.handlers import RequestHandler
from rpcclient.test.testutils import insert_id, create_mock_rpc_client

UNMAPPED_BEHAVIOUR = DictDeserializer.UnmappedBehaviour

__author__ = 'yoav.luft@ajillionmax.com'


class ClientTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.client = create_mock_rpc_client()

    def test_login(self):
        self.assertEqual(self.client.token, "yea")

    @requests_mock.mock()
    def test_get_first_level_method(self, mock):
        mock.register_uri('POST', "http://server/api/", status_code=200, json=insert_id(
            {"error": None, "jsonrpc": "2.0", "id": {},
             "result": {"report": "success"}}),
                          )
        self.client.test(arg1="arg")
        request = mock.request_history[-1].json()
        self.assertRegex(request['jsonrpc'], '2.0')
        self.assertRegex(request['method'], 'test')
        self.assertIn('token', request['params'])
        self.assertRegex(request['params']['token'], 'yea')
        self.assertIn('arg1', request['params'])
        self.assertRegex(request['params']['arg1'], 'arg')

    @requests_mock.mock()
    def test_get_second_level_method(self, mock):
        mock.register_uri('POST', "http://server/api/", status_code=200, json=insert_id(
            {"error": None, "jsonrpc": "2.0", "id": {},
             "result": {"report": "success"}}),
                          )
        self.client.test.level2(arg1="arg")
        request = mock.request_history[-1].json()
        self.assertRegex(request['jsonrpc'], '2.0')
        self.assertRegex(request['method'], 'test.level2')
        self.assertIn('token', request['params'])
        self.assertRegex(request['params']['token'], 'yea')
        self.assertIn('arg1', request['params'])
        self.assertRegex(request['params']['arg1'], 'arg')

    @requests_mock.mock()
    def test_async_request(self, mock):
        mock.register_uri('POST', "http://server/api/", [
            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"report_token": "08d7d7bc608848668b3afa6b528a45d8"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "processing"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "ready"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"report": "success"}})},
        ])
        start_time = time.time()
        interval_time = 2
        response = self.client.test.task(_sleep_interval=interval_time)
        self.assertEqual(response, {"report": "success"})
        self.assertGreater(time.time() - start_time, interval_time, "Expected request to wait between calls")
        last_request = mock.request_history[-1].json()
        self.assertIn('method', last_request)
        self.assertRegex(last_request['method'], 'report.data.get')
        self.assertIn('params', last_request)
        self.assertIn('report_token', last_request['params'])
        self.assertRegex(last_request['params']['report_token'], "08d7d7bc608848668b3afa6b528a45d8")

    @requests_mock.mock()
    def test_async_timeout(self, mock):
        mock.register_uri('POST', "http://server/api/", [
            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"report_token": "08d7d7bc608848668b3afa6b528a45d8"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "processing"}})},
            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "processing"}})},
            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "processing"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "ready"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"report": "success"}})},
        ])
        self.assertRaises(TimeoutError, self.client.test.task, _timeout=3, _sleep_interval=2)

    @requests_mock.mock()
    def test_async_timeout_from_configuration(self, mock):
        mock.register_uri('POST', "http://server/api/", [
            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"report_token": "08d7d7bc608848668b3afa6b528a45d8"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "processing"}})},
            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "processing"}})},
            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "processing"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "ready"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"report": "success"}})},
        ])
        self.client.configuration['timeout'] = 3
        self.client.configuration['sleep_interval'] = 2
        self.assertRaises(TimeoutError, self.client.test.task)

    @requests_mock.mock()
    def test_async_handler_ignores_single_failure_for_status(self, mock):
        mock.register_uri('POST', "http://server/api/", [
            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"report_token": "08d7d7bc608848668b3afa6b528a45d8"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "processing"}})},
            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {}})},
            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "processing"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "ready"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"report": "success"}})},
        ])
        interval_time = 1
        response = self.client.test.task(_sleep_interval=interval_time)
        self.assertEqual(response, {"report": "success"})

    def test_override_handlers(self):
        called_with_params = {}

        class MockHandler(RequestHandler):
            def __init__(self, method, url, headers, token, configuration=None, **kwargs):
                super().__init__(method, url, headers, token, configuration, **kwargs)
                called_with_params['method'] = method

            def handle(self, **kwargs):
                return 'Mock value'

        client = RpcClient(configuration={
            'host': 'http://mockhost',
            'handlers': [
                (lambda *args, **kwargs: True, MockHandler)
            ],
            'login': 'False token',
            'username': '',
            'password': '',
        })
        self.assertEqual(client.some.method(arg1='Argument'), 'Mock value')
        self.assertEqual(called_with_params['method'], 'some.method')
        self.assertEqual(client.token, 'False token')

    @requests_mock.mock()
    def test_async_can_run_in_different_thread(self, mock):
        b = Barrier(2, timeout=5)

        def block_response(response_dict):
            def callback(request, context):
                b.wait()
                body = request.body
                request_json = json.loads(body)
                response_dict['id'] = request_json['id']
                context.status_code = 200
                return response_dict

            return callback

        mock.register_uri('POST', "http://server/api/", [
            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"report_token": "08d7d7bc608848668b3afa6b528a45d8"}})},

            {'status_code': 200, 'json': block_response(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "processing"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"status": "ready"}})},

            {'status_code': 200, 'json': insert_id(
                {"error": None, "jsonrpc": "2.0", "id": {},
                 "result": {"report": "success"}})},
        ])
        response = self.client.test.task(_sleep_interval=0.5, _async=True)
        b.wait()
        self.assertIsInstance(response, Future)
        self.assertTrue(response.running())
        done, not_done = concurrent.futures.wait([response], timeout=5)
        self.assertGreater(len(done), 0)
        self.assertIsInstance(response.result(), dict)

    @requests_mock.mock()
    def test_return_result(self, mock):
        mock.register_uri('POST', "http://server/api/",
                          [{'status_code': 200, 'json': insert_id(
                              {"error": None, "jsonrpc": "2.0", "id": {},
                               "result": {"report": "success"}})},
                           ])
        response = self.client.test(arg1="arg")
        self.assertEqual(response, {"report": "success"})

    @requests_mock.mock()
    def test_return_list_result(self, mock):
        mock.register_uri('POST', "http://server/api/",
                          [{'status_code': 200, 'json': insert_id(
                              {"error": None, "jsonrpc": "2.0", "id": {},
                               "result": [1, 2, 3]})},
                           ])
        response = self.client.test(arg1="arg")
        self.assertListEqual(response, [1, 2, 3])

    @requests_mock.mock()
    def test_raises_error_on_none_200(self, mock):
        mock.register_uri('POST', "http://server/api/", json=insert_id({
                                  "error": None, "jsonrpc": "2.0", "id": {},
                                  "result": {"report": "success"}
                              }, status_code=500))
        self.assertRaises(RemoteFailedError, self.client.test, arg1="arg1")

    @requests_mock.mock()
    def test_raises_error_on_response_error(self, mock):
        mock.register_uri('POST', "http://server/api/",
                          [{'status_code': 200, 'json': insert_id({
                              "error": 1, "jsonrpc": "2.0", "id": {},
                              "result": {"report": "success"}
                          })}
                           ])
        self.assertRaises(RemoteFailedError, self.client.test, arg1="arg1")

    @requests_mock.mock()
    def test_raises_error_on_result_error(self, mock):
        mock.register_uri('POST', "http://server/api/",
                          [{'status_code': 200, 'json': insert_id({
                              "error": None, "jsonrpc": "2.0", "id": {},
                              "result": {"error": "true"}
                          })}
                           ])
        self.assertRaises(RemoteFailedError, self.client.test, arg1="arg1")


class AutoDeserializationTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.client = create_mock_rpc_client()

    @requests_mock.mock()
    def test_deserializer_passed_in_method(self, mock):
        class Result(object):
            def __init__(self, report): self.report = report

        mock.register_uri('POST', "http://server/api/",
                          [{'status_code': 200, 'json': insert_id(
                              {"error": None, "jsonrpc": "2.0", "id": {},
                               "result": {"report": "success"}})},
                           ])

        result_deserializer = DictDeserializer(Result, unmapped_behaviour=UNMAPPED_BEHAVIOUR.TO_KWARGS)
        response = self.client.test(_deserializer=result_deserializer)
        self.assertIsInstance(response, Result)
        self.assertEqual(response.report, "success")

    @requests_mock.mock()
    def test_deserializer_given_in_dictionary(self, mock):
        class Result(object):
            def __init__(self, report): self.report = report

        mock.register_uri('POST', "http://server/api/",
                          [{'status_code': 200, 'json': insert_id(
                              {"error": None, "jsonrpc": "2.0", "id": {},
                               "result": {"report": "success"}})},
                           ])

        result_deserializer = DictDeserializer(Result, unmapped_behaviour=UNMAPPED_BEHAVIOUR.TO_KWARGS)
        client = RpcClient(configuration={
            'host': 'http://server/',
            'login': 'False token',
            'username': '',
            'password': '',
            'deserializers': {
                'test': result_deserializer,
            }
        })
        response = client.test()
        self.assertIsInstance(response, Result)
        self.assertEqual(response.report, "success")

    @requests_mock.mock()
    def test_deserializer_given_in_dictionary_used_just_for_method(self, mock):
        class Result(object):
            def __init__(self, report): self.report = report

        mock.register_uri('POST', "http://server/api/",
                          [{'status_code': 200, 'json': insert_id(
                              {"error": None, "jsonrpc": "2.0", "id": {},
                               "result": {"report": "success"}})},
                           ])

        result_deserializer = DictDeserializer(Result, unmapped_behaviour=UNMAPPED_BEHAVIOUR.TO_KWARGS)
        client = RpcClient(configuration={
            'host': 'http://server/',
            'login': 'False token',
            'username': '',
            'password': '',
            'deserializers': {
                'test': result_deserializer,
            }
        })
        response = client.test2()
        self.assertNotIsInstance(response, Result)
        self.assertEqual(response, {"report": "success"})

    @requests_mock.mock()
    def test_deserializer_from_factory(self, mock):
        class Result(object):
            def __init__(self, report): self.report = report

        mock.register_uri('POST', "http://server/api/",
                          [{'status_code': 200, 'json': insert_id(
                              {"error": None, "jsonrpc": "2.0", "id": {},
                               "result": {"report": "success"}})},
                           ])

        result_deserializer = DictDeserializer(Result, unmapped_behaviour=UNMAPPED_BEHAVIOUR.TO_KWARGS)
        client = RpcClient(configuration={
            'host': 'http://server/',
            'login': 'False token',
            'username': '',
            'password': '',
            'deserializers': lambda method: result_deserializer if method == 'test' else None
        })
        response = client.test2()
        self.assertNotIsInstance(response, Result)
        self.assertEqual(response, {"report": "success"})

        response = client.test()
        self.assertIsInstance(response, Result)
        self.assertEqual(response.report, "success")

    @requests_mock.mock()
    def test_deserializer_global_from_conf(self, mock):
        class Result(object):
            def __init__(self, report): self.report = report

        mock.register_uri('POST', "http://server/api/",
                          [{'status_code': 200, 'json': insert_id(
                              {"error": None, "jsonrpc": "2.0", "id": {},
                               "result": {"report": "success"}})},
                           ])

        result_deserializer = DictDeserializer(Result, unmapped_behaviour=UNMAPPED_BEHAVIOUR.TO_KWARGS)
        client = RpcClient(configuration={
            'host': 'http://server/',
            'login': 'False token',
            'username': '',
            'password': '',
            'deserializers': result_deserializer
        })
        response = client.test()
        self.assertIsInstance(response, Result)
        self.assertEqual(response.report, "success")
