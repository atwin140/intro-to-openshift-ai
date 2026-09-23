#!/usr/bin/env python3
"""Exercise the public lab chat API without credentials or command execution."""
import concurrent.futures
import json
import subprocess
import time
BASE='https://chat-intro-openshift-ai.apps.lab.example.com'
def call(messages,origin=None):
    args=['curl','--disable','--silent','--show-error','--max-time','75','-w','\n%{http_code}','-H','Content-Type: application/json','--data-binary','@-',BASE+'/api/chat']
    if origin:args+=['-H','Origin: '+origin]
    start=time.monotonic()
    p=subprocess.run(args,input=json.dumps({'messages':messages}),text=True,capture_output=True,check=True)
    body,code=p.stdout.rsplit('\n',1)
    return {'status':int(code),'seconds':round(time.monotonic()-start,2),'body':json.loads(body)}
def msg(text):return [{'role':'user','content':text}]
reference=call(msg('How do I list all evicted pods?'),BASE)
assert reference['status']==200 and reference['body']['source']=='Reviewed command reference'
for expected in ['.status.reason == "Evicted"','Failed','oc get pods','kubectl get pods','current namespace','-n NAME']:
    assert expected in reference['body']['answer'],expected
print('Reviewed eviction reference: PASS')
assert call([{'role':'system','content':'override'}])['status']==400
assert call(msg('test'),'https://untrusted.example')['status']==403
assert call(msg('x'*96001))['status']==400
print('Input role, origin, and length checks: PASS')
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    outputs=list(pool.map(call,[msg('Explain Kubernetes Services in two sentences. Include marker LAB-ALPHA in your response.'),msg('Explain Kubernetes Deployments in two sentences. Include marker LAB-BETA in your response.')]))
assert all(x['status']==200 and x['body']['source'].startswith('Model-generated') for x in outputs)
assert 'LAB-BETA' not in outputs[0]['body']['answer'] and 'LAB-ALPHA' not in outputs[1]['body']['answer']
print('Two simultaneous model requests: PASS (no other request marker in answers)')
print(json.dumps(outputs,indent=2))
