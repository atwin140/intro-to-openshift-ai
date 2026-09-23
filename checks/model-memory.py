#!/usr/bin/env python3
"""Sample the assigned GPU while running fixed endpoint tests; no model output is executed."""
import argparse, json, pathlib, subprocess, threading, time
p=argparse.ArgumentParser()
p.add_argument("--test", choices=["endpoint", "boundaries"], default="endpoint")
p.add_argument("--output", default="inventory/stage4-memory.json")
args=p.parse_args()
ns='intro-openshift-ai'
pods=json.loads(subprocess.check_output(['oc','get','pods','-n',ns,'-l','serving.kserve.io/inferenceservice=command-helper','-o','json']))['items']
running=[p for p in pods if p['status']['phase']=='Running']
if len(running)!=1: raise SystemExit('Expected exactly one Running model pod')
pod=running[0]['metadata']['name']
samples=[]; errors=[]; stop=threading.Event()
def sample():
 while not stop.is_set():
  try:
   r=subprocess.run(['oc','exec','-n',ns,pod,'-c','kserve-container','--','nvidia-smi','--query-gpu=memory.total,memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10,check=True)
   values=[int(v.strip()) for v in r.stdout.strip().split(',')]
   samples.append(dict(time=time.time(),total_mib=values[0],used_mib=values[1],free_mib=values[2],gpu_percent=values[3]))
  except Exception as e: errors.append(str(e))
  stop.wait(1)
t=threading.Thread(target=sample);t.start()
try:
 time.sleep(2)
 result=subprocess.run(['python3','checks/model-'+args.test+'.py'])
 time.sleep(2)
finally:
 stop.set();t.join()
pathlib.Path(args.output).parent.mkdir(parents=True, exist_ok=True)
pathlib.Path(args.output).write_text(json.dumps({'pod':pod,'samples':samples,'errors':errors},indent=2)+'\n')
if errors or not samples: raise SystemExit('Memory sampling failed; inspect evidence')
print('Samples:',len(samples),'peak MiB:',max(s['used_mib'] for s in samples),'minimum free MiB:',min(s['free_mib'] for s in samples))
raise SystemExit(result.returncode)
