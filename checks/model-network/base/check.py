import os, socket, urllib.request
host='command-helper-predictor.intro-openshift-ai.svc.cluster.local'
socket.getaddrinfo(host,8080)
blocked=os.environ['EXPECT_BLOCKED']=='true'
try:
 with urllib.request.urlopen('http://'+host+':8080/health',timeout=8) as r:
  assert r.status==200
except (TimeoutError, urllib.error.URLError) as e:
 reason=getattr(e,'reason',e)
 if not blocked or not isinstance(reason,(TimeoutError,socket.timeout)): raise
 print('DENIED-CLIENT-TIMED-OUT-AS-EXPECTED',flush=True)
else:
 if blocked: raise RuntimeError('Unlabeled client unexpectedly reached model')
 print('ALLOWED-CLIENT-HEALTH-PASSED',flush=True)
