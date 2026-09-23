"""Small, anonymous lab chat server. No tools, shell execution, or Kubernetes client."""
import json
import os
import re
import threading
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
PROMPT = (ROOT / 'assistant.md').read_text()
MODEL_URL = os.environ.get('MODEL_URL', 'http://command-helper-predictor:8080/v1/chat/completions')
SLOTS = threading.BoundedSemaphore(2)
REFERENCE = '''Evicted is a specific Pod reason, not a phase. Filtering only phase Failed also includes failures unrelated to eviction. These commands inspect existing Pod objects; they cannot recover deleted Pod history. Requires jq.

All namespaces:
```sh
oc get pods -A -o json | jq -r '.items[] | select(.status.reason == "Evicted") | [.metadata.namespace, .metadata.name] | @tsv'
kubectl get pods -A -o json | jq -r '.items[] | select(.status.reason == "Evicted") | [.metadata.namespace, .metadata.name] | @tsv'
```
For the current namespace, omit -A. For one namespace, replace -A with -n NAME. Your account must have permission to list Pods in the requested scope.

Source: https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/
Source: https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors/

These commands are examples only. This chat has not inspected your cluster or executed them.'''

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, *_):
        pass  # Do not log conversation contents or request headers.

    def reply(self, status, body, content_type='application/json'):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                  '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                  '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if self.path == '/healthz':
            return self.reply(200, {'status': 'ok'})
        if self.path not in assets:
            return self.reply(404, {'error': 'Not found'})
        file, mime = assets[self.path]
        self.reply(200, (ROOT / file).read_bytes(), mime)

    def do_POST(self):
        if self.path != '/api/chat':
            return self.reply(404, {'error': 'Not found'})
        origin = self.headers.get('Origin')
        expected = os.environ.get('PUBLIC_ORIGIN')
        if origin and origin != expected:
            return self.reply(403, {'error': 'Request origin is not allowed.'})
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.reply(415, {'error': 'Use application/json.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 400000:
                return self.reply(413, {'error': 'Message is too large.'})
            data = json.loads(self.rfile.read(length))
            messages = data['messages']
            if not isinstance(messages, list) or not 1 <= len(messages) <= 41:
                raise ValueError()
            if messages[-1].get('role') != 'user':
                raise ValueError()
            for m in messages:
                if m.get('role') not in ('user', 'assistant') or not isinstance(m.get('content'), str) or not m['content'].strip():
                    raise ValueError()
            if sum(len(m['content']) for m in messages) > 96000:
                return self.reply(400, {'error': 'Conversation is too long. Start a new chat or shorten your message.'})
        except (ValueError, KeyError, TypeError, AttributeError):
            return self.reply(400, {'error': 'Send a valid conversation.'})
        question = re.sub(r'[^a-z0-9 ]', '', messages[-1]['content'].lower()).strip()
        if question in ('how do i list all evicted pods', 'how do i list evicted pods', 'list all evicted pods'):
            return self.reply(200, {'answer': REFERENCE, 'source': 'Reviewed command reference'})
        if not SLOTS.acquire(blocking=False):
            return self.reply(429, {'error': 'Both lab chat slots are busy. Please try again shortly.'})
        try:
            payload = {'model': 'command-helper', 'messages': [{'role': 'system', 'content': PROMPT}] + [
                {'role': m['role'], 'content': m['content']} for m in messages],
                'temperature': 0.1, 'max_tokens': 2048}
            started = time.monotonic()
            trimmed = 0
            while True:
                token_req = urllib.request.Request(MODEL_URL.rsplit('/v1/', 1)[0] + '/tokenize',
                    data=json.dumps({'model': 'command-helper', 'messages': payload['messages'], 'add_generation_prompt': True}).encode(),
                    headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(token_req, timeout=15) as response:
                    count = json.load(response)['count']
                if count + 2048 <= 16384:
                    break
                if len(payload['messages']) <= 2:
                    return self.reply(400, {'error': 'This message alone exceeds the context budget. Shorten it before sending.'})
                del payload['messages'][1:3]
                trimmed += 2
            req = urllib.request.Request(MODEL_URL, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.load(response)
            self.reply(200, {'answer': result['choices'][0]['message']['content'], 'source': 'Model-generated · review before use', 'usage': result.get('usage', {}), 'context_limit': 16384, 'trimmed_messages': trimmed, 'seconds': round(time.monotonic()-started, 1), 'finish_reason': result['choices'][0].get('finish_reason')})
        except urllib.error.HTTPError as exc:
            self.reply(502, {'error': 'The model rejected this request. Try a shorter message or a new chat.' if exc.code == 400 else 'The model is unavailable. Please try again.'})
        except (OSError, ValueError, KeyError, IndexError):
            self.reply(502, {'error': 'The model did not respond. Please try again.'})
        finally:
            SLOTS.release()

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
