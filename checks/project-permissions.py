#!/usr/bin/env python3
"""Run with the actual intended user's oc login, without impersonation."""
import subprocess
import sys

import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('expected_username')
parser.add_argument('--context', help='Use this existing authenticated context without switching the active one')
args = parser.parse_args()
expected = args.expected_username
OC = ['oc'] + (['--context', args.context] if args.context else [])
server = subprocess.check_output(OC + ['whoami', '--show-server'], text=True).strip()
if server != 'https://api.lab.example.com:6443':
    raise SystemExit('Wrong API endpoint; review the lab-specific target before proceeding')
namespace = 'intro-openshift-ai'
identity = subprocess.check_output(OC + ['whoami'], text=True).strip()
if identity != expected:
    raise SystemExit(f'Wrong identity: {identity}; expected {expected}')
# Inspect only the impersonation field, never credentials or complete kubeconfig.
impersonation = subprocess.check_output(
    OC + ['config', 'view', '--minify', '-o', 'jsonpath={.users[0].user.as}'], text=True
).strip()
if impersonation:
    raise SystemExit('Impersonated context is not a valid final handoff test')

def allowed(verb, resource, scope):
    result = subprocess.run(OC + ['auth', 'can-i', verb, resource, *scope],
                            capture_output=True, text=True)
    answer = result.stdout.strip()
    if answer not in ('yes', 'no'):
        raise SystemExit(f'Permission query failed for {verb} {resource}: {result.stderr}')
    return answer == 'yes'

for verb, resource in [('create', 'clusterrolebindings.rbac.authorization.k8s.io'),
                       ('patch', 'nodes'), ('create', 'namespaces')]:
    if allowed(verb, resource, []):
        raise SystemExit(f'Unexpected cluster privilege: {verb} {resource}; review identity')
resources = ['deployments.apps', 'services', 'routes.route.openshift.io',
             'configmaps', 'secrets', 'serviceaccounts', 'persistentvolumeclaims',
             'jobs.batch', 'pods', 'networkpolicies.networking.k8s.io',
             'inferenceservices.serving.kserve.io', 'servingruntimes.serving.kserve.io']
failures = []
for resource in resources:
    for verb in ['get', 'list', 'watch', 'create', 'patch', 'update', 'delete']:
        if not allowed(verb, resource, ['-n', namespace]):
            failures.append(f'{verb} {resource}')
if not allowed('create', 'pods/exec', ['-n', namespace]):
    failures.append('create pods/exec')
if not allowed('create', 'pods/portforward', ['-n', namespace]):
    failures.append('create pods/portforward')
if not allowed('get', 'pods/log', ['-n', namespace]):
    failures.append('get pods/log')
if failures:
    raise SystemExit('Missing project permissions: ' + ', '.join(failures))
print(f'PASS: {identity} has checked project permissions and lacks checked cluster privileges')
print('Next: apply, inspect, and delete checks/project-access using this same login.')
