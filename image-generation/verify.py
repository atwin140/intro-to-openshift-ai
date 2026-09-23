#!/usr/bin/env python3
"""Exercise the deployed image API without saving credentials or prompt bodies in logs."""
import base64
import concurrent.futures
import json
import pathlib
import threading
import generate

root=pathlib.Path(__file__).resolve().parents[1]
out=root.parent/'outputs'/'image-generation'
out.mkdir(parents=True,exist_ok=True)
results={}
assert generate.oc('whoami','--show-server')==generate.API
status,_=generate.request('/v1/models');assert status in (401,403),status
results['anonymous_http']=status
status,_=generate.request('/v1/models','invalid');assert status in (401,403),status
results['invalid_token_http']=status
token=generate.oc('whoami','-t')
status,body=generate.request('/v1/models',token);assert status==200,(status,body)
results['model']=json.loads(body)
for name,payload in [
 ('empty_prompt',{'prompt':''}),('blank_prompt',{'prompt':'   '}),
 ('too_many_steps',{'prompt':'A forest','steps':100}),
 ('extra_field',{'prompt':'A forest','width':1024}),
 ('wrong_type',{'prompt':'A forest','steps':'25'}),
 ('too_many_tokens',{'prompt':'x '*240}),
]:
 status,body=generate.request('/v1/images/generations',token,payload)
 assert status==422,(name,status,body)
 results[name]=status
status,_=generate.request('/v1/images/generations',token,{'prompt':'x'*9000});assert status==413,status
results['oversized_request']=status
payload={'prompt':'A watercolor painting of a lighthouse on a rocky coast at sunrise, soft blue sea, warm golden light','seed':42,'steps':25}
status,body=generate.request('/v1/images/generations',token,payload);assert status==200,(status,body)
def save(body,name):
 r=json.loads(body);png=base64.b64decode(r.pop('data')[0]['b64_json'],validate=True)
 assert png[:8]==b'\x89PNG\r\n\x1a\n'
 assert int.from_bytes(png[16:20],'big')==512
 assert int.from_bytes(png[20:24],'big')==512
 (out/name).write_bytes(png)
 return r
results['sample']=save(body,'lighthouse.png')
barrier=threading.Barrier(2)
def call(i):
 barrier.wait()
 return generate.request('/v1/images/generations',token,{'prompt':'A photograph of a red fox sitting in a sunlit forest, detailed natural colors','seed':100+i,'steps':40})
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 responses=list(pool.map(call,range(2)))
statuses=sorted(s for s,b in responses)
assert statuses==[200,429],statuses
results['simultaneous_requests_http']=statuses
for status,body in responses:
 if status==200:results['second_sample']=save(body,'fox.png')
(root/'inventory'/'image-generator-verification.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
