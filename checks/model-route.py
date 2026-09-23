#!/usr/bin/env python3
"""Test the reference HTTPS model route using the current oc login; never print tokens."""
import argparse
import json
import pathlib
import subprocess
import sys

NS = 'intro-openshift-ai'
API = 'https://api.lab.example.com:6443'
HOST = 'command-helper-intro-openshift-ai.apps.lab.example.com'

def oc(*args):
    return subprocess.check_output(['oc', *args], text=True).strip()

def request(path, token=None, payload=None):
    # Pass credentials through stdin, never through command arguments or files.
    cfg = ['silent', 'show-error', 'connect-timeout = 10', 'max-time = 60',
           'url = ' + json.dumps('https://' + HOST + path),
           'write-out = "\\n%{http_code}"']
    if token:
        cfg.append('header = ' + json.dumps('Authorization: Bearer ' + token))
    if payload is not None:
        cfg.extend(['header = "Content-Type: application/json"',
                    'data = ' + json.dumps(json.dumps(payload))])
    result = subprocess.run(['curl', '--disable', '--config', '-'],
                            input='\n'.join(cfg) + '\n', text=True,
                            capture_output=True, timeout=70)
    if result.returncode:
        raise RuntimeError('HTTPS request failed; check DNS, trusted certificates, and connectivity.')
    body, status = result.stdout.rsplit('\n', 1)
    return int(status), body

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt', default='How do I list all evicted pods?')
    args = parser.parse_args()
    if oc('whoami', '--show-server') != API:
        raise RuntimeError('Current oc connection is not the intended reference cluster.')
    host = oc('get', 'route', 'command-helper', '-n', NS,
              '-o', 'jsonpath={.spec.host}')
    if host != HOST:
        raise RuntimeError('Route hostname differs from the reviewed reference hostname.')
    if oc('auth', 'can-i', 'get', 'inferenceservices.serving.kserve.io/command-helper', '-n', NS) != 'yes':
        raise RuntimeError('Current user cannot access this InferenceService.')
    status, _ = request('/v1/models')
    print('Anonymous model-list request:', status)
    if status not in (401, 403):
        raise RuntimeError('Expected authentication rejection; stop and inspect the route.')
    token = oc('whoami', '-t')
    if not token:
        raise RuntimeError('Current login has no bearer token; authenticate normally with oc.')
    status, body = request('/v1/models', token)
    print('Authenticated model-list request:', status)
    if status != 200:
        raise RuntimeError('Authenticated model request failed.')
    models = json.loads(body)['data']
    model = models[0]['id']
    print('Model:', model)
    system = (pathlib.Path(__file__).resolve().parents[1] / 'chatbot/prompts/assistant.md').read_text()
    status, body = request('/v1/chat/completions', token, {
        'model': model, 'messages': [{'role': 'system', 'content': system},
                                   {'role': 'user', 'content': args.prompt}],
        'temperature': 0, 'max_tokens': 768})
    print('Chat completion request:', status)
    if status != 200:
        raise RuntimeError('Chat completion failed; inspect model readiness and request limits.')
    print(json.loads(body)['choices'][0]['message']['content'])
    print('\nTransport check passed. Review the generated answer separately; no commands were executed.')

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.SubprocessError, ValueError, KeyError, IndexError) as exc:
        # Never dump subprocess arguments/output or credential-bearing request configuration.
        print('CHECK FAILED:', str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__, file=sys.stderr)
        sys.exit(1)
