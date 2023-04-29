from unittest import TestCase
from unittest import mock

from bitcoin_peer_rotate import BitcoinPeerRotate
from bitcoin_peer_rotate import BitcoinRpc
from bitcoin_peer_rotate import Request


class MockResponse:
    def __init__(self, status_code=200, content=None, json_response=None):
        self.status_code = status_code
        self.content = content
        self.json_response = json_response

    def json(self):
        return self.json_response


class TestBitcoinRpc(TestCase):
    @mock.patch("bitcoin_peer_rotate.bitcoin_peer_rotate.Request")
    @mock.patch("bitcoin_peer_rotate.BitcoinRpc._read_cookie_auth")
    def setUp(self, mock_read_cookie_auth, mock_request):
        mock_read_cookie_auth.return_value = ("username", "password")
        self.mock_request = mock_request
        self.rpc = BitcoinRpc()
        self.ok = "ok"

    def test_addnode(self):
        self.mock_request.return_value.post.return_value = MockResponse(
            json_response=dict(result=self.ok)
        )
        result = self.rpc.addnode("127.0.0.1:1000")
        self.assertEqual(result, self.ok)

    def test_disconnectnode(self):
        self.mock_request.return_value.post.return_value = MockResponse(
            json_response=dict(result=self.ok)
        )
        result = self.rpc.disconnectnode("127.0.0.1:1000")
        self.assertEqual(result, self.ok)

    def test_getaddednodeinfo(self):
        self.mock_request.return_value.post.return_value = MockResponse(
            json_response=dict(result=self.ok)
        )
        result = self.rpc.getaddednodeinfo()
        self.assertEqual(result, self.ok)

    def test_getpeerinfo(self):
        self.mock_request.return_value.post.return_value = MockResponse(
            json_response=dict(result=self.ok)
        )
        result = self.rpc.getpeerinfo()
        self.assertEqual(result, self.ok)

    @mock.patch("bitcoin_peer_rotate.BitcoinRpc.addnode")
    @mock.patch("bitcoin_peer_rotate.BitcoinRpc.getaddednodeinfo")
    @mock.patch("bitcoin_peer_rotate.BitcoinRpc.disconnectnode")
    @mock.patch("bitcoin_peer_rotate.BitcoinRpc.getpeerinfo")
    def test_purge_peers(
        self,
        mock_getpeerinfo,
        mocked_disconnectnode,
        mock_getaddednodeinfo,
        mock_addnode,
    ):
        mock_getpeerinfo.return_value = [dict(addr="127.0.0.1:1000")]
        mock_getaddednodeinfo.return_value = [dict(addednode="127.0.0.1:2000")]
        self.assertEqual(self.rpc.purge_peers(), 2)


class TestBitcoinPeerRotate(TestCase):
    @mock.patch("bitcoin_peer_rotate.bitcoin_peer_rotate.BitcoinRpc")
    @mock.patch("bitcoin_peer_rotate.bitcoin_peer_rotate.Request")
    def setUp(self, mock_request, mock_bitcoin_rpc):
        self.mock_request = mock_request
        self.mock_bitcoin_rpc = mock_bitcoin_rpc
        self.bpr = BitcoinPeerRotate(min_limit=1)

    def test_rotate(self):
        self.mock_request.return_value.get.return_value = MockResponse(
            json_response=dict(nodes={"127.0.0.1:1000": {"a": "b"}})
        )
        self.bpr.rotate()
        self.assertEqual(self.mock_bitcoin_rpc.return_value.purge_peers.call_count, 1)
        self.assertEqual(self.mock_bitcoin_rpc.return_value.addnode.call_count, 1)


class TestRequest(TestCase):
    @mock.patch("requests.Session")
    def setUp(self, mock_session):
        self.mock_session = mock_session
        self.request = Request()
        self.url = "http://localhost"
        self.ok = "ok"

    def test_get(self):
        self.mock_session.return_value.get.return_value = MockResponse(content=self.ok)
        response = self.request.get(self.url)
        self.assertEqual(response.content, self.ok)

    @mock.patch("time.sleep")
    def test_400_get(self, mock_sleep):
        self.mock_session.return_value.get.return_value = MockResponse(status_code=400)
        response = self.request.get(self.url)
        self.assertIsNone(response.content)
        self.assertEqual(mock_sleep.call_count, 10)

    def test_post(self):
        self.mock_session.return_value.post.return_value = MockResponse(content=self.ok)
        response = self.request.post(self.url)
        self.assertEqual(response.content, self.ok)

    @mock.patch("time.sleep")
    def test_400_post(self, mock_sleep):
        self.mock_session.return_value.post.return_value = MockResponse(status_code=400)
        response = self.request.post(self.url)
        self.assertIsNone(response.content)
        self.assertEqual(mock_sleep.call_count, 10)
