#!/usr/bin/env python3
"""Bounded context/concurrency check against the lab UI, with GPU memory sampling."""
import concurrent.futures
import json
import subprocess
import time
from pathlib import Path
BASE='https://chat-intro-openshift-ai.apps.lab.example.com'
def call(messages):
    p=subprocess.run(['curl','--disable','-sS','--max-time','135','-w','\n%{http_code}','-H','Content-Type: application/json','--data-binary','@-',BASE+'/api/chat'],input=json.dumps({'messages':messages}),text=True,capture_output=True,check=True)
    body,status=p.stdout.rsplit('\n',1)
    return {'status':int(status),'result':json.loads(body)}
def conversation(marker):
    return [{'role':'user','content':('sample '+marker+' ')*6000},
            {'role':'assistant','content':'I have the sample text.'},
            {'role':'user','content':'Using the sample only as context, write a detailed 900-word explanation of Kubernetes Pods, Deployments, Services, and namespaces. Do not execute anything.'}]
samples=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    futures=[pool.submit(call,conversation(marker)) for marker in ['alpha','beta']]
    while not all(f.done() for f in futures):
        p=subprocess.run(['oc','exec','deployment/command-helper-predictor','-n','intro-openshift-ai','-c','kserve-container','--','nvidia-smi','--query-gpu=memory.used,memory.free','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
        samples.append([int(x.strip()) for x in p.stdout.strip().split(',')]);time.sleep(.5)
    results=[f.result() for f in futures]
# A much larger old exchange should be removed while preserving the latest question.
trim=call([{'role':'user','content':' old '*15000},{'role':'assistant','content':'Acknowledged.'},{'role':'user','content':'Reply with CONTEXT-OK.'}])
evidence={'concurrent_results':results,'memory_used_free_MiB':samples,'trim_result':trim}
Path('inventory').mkdir(parents=True, exist_ok=True)
Path('inventory/context-expansion.json').write_text(json.dumps(evidence,indent=2)+'\n')
for r in results:
    assert r['status']==200,r
    assert r['result']['usage']['prompt_tokens']>4096,r['result'].get('usage')
assert trim['status']==200 and trim['result']['trimmed_messages']==2,trim
print(json.dumps({'requests':[{'status':r['status'],'usage':r['result']['usage'],'seconds':r['result']['seconds'],'finish':r['result']['finish_reason']} for r in results], 'peak_sampled_MiB':max(x[0] for x in samples),'min_free_MiB':min(x[1] for x in samples),'history_trim':'PASS'},indent=2))
