#!/usr/bin/env python3
"""Ephemeral zeze -> Mac forced-command SSH fixture. No production identity/grant is enabled."""
import base64
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from prepare_worker import prepare


def main():
    address = subprocess.check_output(['ipconfig','getifaddr','en0'],text=True).strip()
    with tempfile.TemporaryDirectory(prefix='gahyeon-topology-') as tmp:
        base=Path(tmp).resolve(); key=base/'client'
        subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
        with socket.socket() as sock:
            sock.bind((address,0));port=sock.getsockname()[1]
        prepared=prepare(base/'endpoint',42,7,'mac',key.with_suffix('.pub').read_text(),listen=address,port=port)
        host=(base/'endpoint/host_key.pub').read_text().split()
        test='import unittest\nclass Example(unittest.TestCase):\n    def test_sum(self):\n        self.assertEqual(2 + 3, 5)\n'
        tasks=[dict(target='mac',action='write',path='test_example.py',content=test,expectedSha256='absent'),
               dict(target='mac',action='read',path='test_example.py'),dict(target='mac',action='test')]
        requests=[dict(actor='42',scope='7',jobId=hashlib.sha256(json.dumps(t).encode()).hexdigest(),task=t) for t in tasks]
        wrong=dict(requests[-1],actor='99',jobId='b'*64)
        payload=dict(address=address,port=port,key=base64.b64encode(key.read_bytes()).decode(),
                     hostKey=host[0]+' '+host[1],requests=requests+[wrong],user='ze')
        remote='''import base64,json,subprocess,tempfile,os
from pathlib import Path
p=PAYLOAD
with tempfile.TemporaryDirectory(prefix='gahyeon-fixture-key-') as tmp:
 base=Path(tmp);key=base/'client';key.write_bytes(base64.b64decode(p['key']));key.chmod(0o600)
 known=base/'known_hosts';known.write_text('['+p['address']+']:'+str(p['port'])+' '+p['hostKey']+'\\n')
 results=[]
 for request in p['requests']:
  args=['ssh','-F','/dev/null','-T','-p',str(p['port']),'-i',str(key),'-o','BatchMode=yes','-o','ConnectTimeout=5','-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(known),p['user']+'@'+p['address']]
  result=subprocess.run(args,input=json.dumps(request)+'\\n',capture_output=True,text=True,timeout=80)
  try: reply=json.loads(result.stdout)
  except ValueError: reply={'ok':False,'transportError':result.stderr[:100]}
  results.append({'action':request['task']['action'],'exitCode':result.returncode,'ok':reply.get('ok',False),'jobMatches':reply.get('jobId')==request['jobId'],'testExitCode':reply.get('result',{}).get('exitCode'),'sha256':reply.get('result',{}).get('sha256')})
 print(json.dumps({'path':'zeze -> dedicated Mac SSH -> isolated worker','results':results,'productionIdentityUsed':False}))
'''.replace('PAYLOAD',repr(payload))
        with (base/'server.log').open('w') as log:
            server=subprocess.Popen(prepared['command'],stdout=log,stderr=log)
            try:
                time.sleep(.4)
                process=subprocess.run(['ssh','land','ssh zeze python3 -'],input=remote,text=True,capture_output=True,timeout=150)
                if process.returncode: raise RuntimeError('Topology probe transport failed')
                result=json.loads(process.stdout)
                expected=hashlib.sha256(test.encode()).hexdigest()
                result['passed']=(all(r['ok'] and r['jobMatches'] for r in result['results'][:3])
                                  and result['results'][0]['sha256']==expected
                                  and result['results'][1]['sha256']==expected
                                  and result['results'][2]['testExitCode']==0
                                  and not result['results'][3]['ok'])
            finally:
                server.terminate();server.wait(timeout=5)
        result['endpointStopped']=True
        result['temporaryKeysRemovedOnExit']=True
    path=Path('artifacts/trusted-research-owner-work-20261016/zeze-mac-topology.json')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return 0 if result['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
