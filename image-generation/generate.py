#!/usr/bin/env python3
"""Generate a PNG using your current reference OpenShift login. Credentials stay in memory."""
import argparse
import base64
import json
import pathlib
import subprocess

API='https://api.lab.example.com:6443'
NS='intro-openshift-ai'
HOST='image-generator-intro-openshift-ai.apps.lab.example.com'

def oc(*args):
    return subprocess.check_output(['oc',*args],text=True).strip()

def request(path,token=None,payload=None):
    config=['silent','show-error','connect-timeout = 10','max-time = 180',
            'url = '+json.dumps('https://'+HOST+path), 'write-out = "\\n%{http_code}"']
    if token:config.append('header = '+json.dumps('Authorization: Bearer '+token))
    if payload is not None:
        config+=['header = "Content-Type: application/json"','data = '+json.dumps(json.dumps(payload))]
    r=subprocess.run(['curl','--disable','--config','-'],input='\n'.join(config)+'\n',capture_output=True,text=True,timeout=190)
    if r.returncode:raise RuntimeError('HTTPS request failed. Check connectivity and certificate trust.')
    body,status=r.stdout.rsplit('\n',1)
    return int(status),body

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('prompt');p.add_argument('--output',default='generated.png');p.add_argument('--seed',type=int,default=42);p.add_argument('--steps',type=int,default=25)
    a=p.parse_args()
    if oc('whoami','--show-server')!=API:raise RuntimeError('Log in to the reference cluster first.')
    if oc('get','route','image-generator','-n',NS,'-o','jsonpath={.spec.host}')!=HOST:raise RuntimeError('Unexpected image route.')
    token=oc('whoami','-t')
    status,body=request('/v1/images/generations',token,{'prompt':a.prompt,'seed':a.seed,'steps':a.steps})
    if status!=200:raise RuntimeError(f'Image request returned HTTP {status}: {body[:500]}')
    result=json.loads(body);png=base64.b64decode(result.pop('data')[0]['b64_json'],validate=True)
    if not png.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('Response is not a PNG.')
    output=pathlib.Path(a.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(png)
    output.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'Saved {output.resolve()}');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
