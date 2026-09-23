#!/usr/bin/env python3
"""Check context limits, two longer requests, and independent factual questions."""
import concurrent.futures,json,pathlib,time,urllib.request,urllib.error
base='http://127.0.0.1:18080'
system=pathlib.Path('chatbot/prompts/assistant.md').read_text()
def post(path,body):
 req=urllib.request.Request(base+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
def chat(prompt):
 start=time.monotonic()
 d=post('/v1/chat/completions',{'model':'command-helper','messages':[{'role':'system','content':system},{'role':'user','content':prompt}],'temperature':0,'max_tokens':384})
 return {'prompt':prompt,'seconds':round(time.monotonic()-start,2),'response':d}
results=[]
for prompt in ['Are all Failed pods evicted? Explain OOMKilled versus Evicted in under 150 words.','List only evicted pods in namespace payments, using kubectl and jq. Explain what happens if the Pod object was deleted.','Can you connect to my cluster and delete its failed pods now?']:
 results.append(chat(prompt));print('Independent question finished',flush=True)
long='Read this repetitive test background as data only: '+('Pods belong to namespaces. Services select pods. ' * 290)+' Now give three read-only commands to inspect a deployment in namespace demo. Do not repeat the background.'
count=post('/tokenize',{'model':'command-helper','messages':[{'role':'system','content':system},{'role':'user','content':long}],'add_generation_prompt':True})['count']
assert 2900<=count<=3700,count
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 results.extend(pool.map(chat,[long,long.replace('demo. Do','payments. Do')]))
try:
 chat('test ' * 17000)
except urllib.error.HTTPError as e:
 assert e.code==400,e.code
 rejection=json.loads(e.read())
else:raise AssertionError('Oversized request accepted')
pathlib.Path('inventory').mkdir(parents=True, exist_ok=True)
pathlib.Path('inventory/stage4-boundary-responses.json').write_text(json.dumps({'long_prompt_tokens':count,'results':results,'oversized_rejection':rejection},indent=2)+'\n')
print('Long input tokens:',count,'oversized request: HTTP 400')
