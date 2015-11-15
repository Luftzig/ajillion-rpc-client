import json

import requests_mock

from rpcclient.client import RpcClient

MOCK_SERVER_URL = "http://server/api/"

__author__ = 'yoav.luft@ajillionmax.com'


def insert_id(response_dict, status_code=200):
    def callback(request, context):
        body = request.body
        request_json = json.loads(body)
        response_dict['id'] = request_json['id']
        context.status_code = status_code
        return response_dict

    return callback


@requests_mock.mock()
def create_mock_rpc_client(mock):
    mock.register_uri('POST', MOCK_SERVER_URL,
                      json=insert_id({"id": None, "error": None, "result": {"token": "yea"}}),
                      headers={'Content-Type': "application/json"})
    return RpcClient("http://server/", None, 'user', 'password')
