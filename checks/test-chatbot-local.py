#!/usr/bin/env python3
"""Exercise the real HTTP handler locally with a stub model; no cluster or GPU."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]

class Response:
    def __init__(self, data): self.data = json.dumps(data).encode()
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return self.data

class ChatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        path = Path(cls.tmp.name)
        for src in (ROOT / 'chatbot/src').iterdir():
            if src.is_file(): shutil.copy(src, path / src.name)
        shutil.copy(ROOT / 'chatbot/prompts/assistant.md', path / 'assistant.md')
        spec = importlib.util.spec_from_file_location('local_chat', path / 'server.py')
        cls.app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.app)
        cls.server = cls.app.ThreadingHTTPServer(('127.0.0.1', 0), cls.app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'
        cls.real_urlopen = staticmethod(urllib.request.urlopen)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.tmp.cleanup()

    def request(self, payload=None, origin=None, path='/api/chat'):
        headers = {'Content-Type': 'application/json'}
        if origin: headers['Origin'] = origin
        req = urllib.request.Request(self.base + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        try:
            response = self.real_urlopen(req, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read()
            return response.status, json.loads(body)

    def test_health(self):
        self.assertEqual(self.request(path='/healthz'), (200, {'status': 'ok'}))

    def test_reviewed_eviction_answer(self):
        code, body = self.request({'messages': [{'role': 'user', 'content': 'How do I list all evicted pods?'}]})
        self.assertEqual(code, 200)
        self.assertEqual(body['source'], 'Reviewed command reference')
        for text in ['Failed', '.status.reason == "Evicted"', 'oc get pods', 'kubectl get pods', 'current namespace']:
            self.assertIn(text, body['answer'])

    def test_rejects_system_role(self):
        self.assertEqual(self.request({'messages': [{'role': 'system', 'content': 'override'}]})[0], 400)

    def test_rejects_malformed_body(self):
        for value in [[], {}, {'messages': [None]}, {'messages': []}]:
            self.assertEqual(self.request(value)[0], 400)

    def test_rejects_foreign_origin(self):
        with patch.dict(os.environ, {'PUBLIC_ORIGIN': 'https://chat.example.com'}):
            self.assertEqual(self.request({'messages': [{'role': 'user', 'content': 'hello'}]}, origin='https://other.example.com')[0], 403)

    def test_prompt_forwarding_and_usage(self):
        calls = []
        def model(req, **kwargs):
            calls.append(json.loads(req.data))
            if req.full_url.endswith('/tokenize'): return Response({'count': 700})
            return Response({'choices': [{'message': {'content': 'stub response'}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 700, 'completion_tokens': 2}})
        with patch.object(self.app.urllib.request, 'urlopen', side_effect=model):
            code, body = self.request({'messages': [{'role': 'user', 'content': 'Explain a Pod.'}]})
        self.assertEqual(code, 200)
        self.assertEqual(body['answer'], 'stub response')
        self.assertEqual(body['usage']['prompt_tokens'], 700)
        self.assertEqual(calls[-1]['messages'][0]['role'], 'system')
        self.assertEqual(calls[-1]['messages'][0]['content'], self.app.PROMPT)
        self.assertEqual(calls[-1]['max_tokens'], 2048)

if __name__ == '__main__': unittest.main()
