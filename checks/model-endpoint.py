#!/usr/bin/env python3
"""Exercise a locally forwarded model endpoint; never execute model output."""
import argparse, concurrent.futures, json, pathlib, time, urllib.request
p=argparse.ArgumentParser()
p.add_argument('--url', default='http://127.0.0.1:18080')
p.add_argument('--output',default='inventory/stage4-responses.json')
a=p.parse_args()
system=(pathlib.Path(__file__).resolve().parents[1]/'chatbot/prompts/assistant.md').read_text()
def chat(label,prompt):
 body={'model':'command-helper','messages':[{'role':'system','content':system},{'role':'user','content':prompt}],'temperature':0,'max_tokens':768}
 start=time.monotonic()
 req=urllib.request.Request(a.url+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=180) as r: data=json.load(r)
 result={'label':label,'seconds':round(time.monotonic()-start,2),'prompt':prompt,'response':data}
 print(label, result['seconds'], 'seconds',data.get('usage'),flush=True)
 return result
with urllib.request.urlopen(a.url+'/v1/models',timeout=10) as r: models=json.load(r)
results=[chat('evicted-single','How do I list all evicted pods?')]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 futures=[pool.submit(chat,'concurrent-evicted','How do I list all evicted pods?'),pool.submit(chat,'concurrent-rollout','How do I check deployment rollout status and view logs in namespace demo? Include oc and kubectl examples.')]
 results.extend(f.result() for f in futures)
pathlib.Path(a.output).parent.mkdir(parents=True, exist_ok=True)
pathlib.Path(a.output).write_text(json.dumps({'models':models,'results':results},indent=2)+'\n')
print('Saved responses for manual correctness review:',a.output)
