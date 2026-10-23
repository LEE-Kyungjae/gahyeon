#!/usr/bin/env python3
"""Prepare a dedicated worker SSH endpoint; does not start it or change system SSH."""
import argparse
import base64
import getpass
import ipaddress
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys


def prepare(base, owner, scope, target, public_key, listen='127.0.0.1', port=2222):
    base = base.resolve()
    if owner <= 0 or scope <= 0 or target not in {'mac', 'land'}:
        raise ValueError('Verified owner actor, scope and fixed target required')
    ipaddress.ip_address(listen)
    if not 1024 <= port <= 65535:
        raise ValueError('Unprivileged port required')
    parts = public_key.strip().split()
    if len(parts) < 2 or parts[0] != 'ssh-ed25519':
        raise ValueError('Dedicated Ed25519 public key required')
    base64.b64decode(parts[1], validate=True)
    if base.exists() and any(base.iterdir()):
        raise ValueError('Use a new endpoint directory; never overwrite an existing grant')
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    base.chmod(0o700)
    for name in ['workspace', 'state']:
        (base / name).mkdir(mode=0o700)
    shutil.copyfile(Path(__file__).with_name('worker.py'), base / 'worker.py')
    config = dict(ownerActor=str(owner), scope=str(scope), target=target,
                  workspace=str(base/'workspace'), stateDir=str(base/'state'),
                  testCommand=[sys.executable, '-I', '-m', 'unittest', 'discover', '-s', '.'])
    (base/'config.json').write_text(json.dumps(config, indent=2)+'\n')
    (base/'config.json').chmod(0o600)
    command = shlex.join([sys.executable, str(base/'worker.py'), '--config', str(base/'config.json')])
    escaped = command.replace('\\','\\\\').replace('"','\\"')
    (base/'authorized_keys').write_text('restrict,command="'+escaped+'" '+parts[0]+' '+parts[1]+'\n')
    (base/'authorized_keys').chmod(0o600)
    subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-f',str(base/'host_key')], check=True)
    settings = f'''Port {port}
ListenAddress {listen}
HostKey "{base / 'host_key'}"
PidFile "{base / 'sshd.pid'}"
AuthorizedKeysFile "{base / 'authorized_keys'}"
StrictModes yes
PasswordAuthentication no
KbdInteractiveAuthentication no
UsePAM no
PermitRootLogin no
AllowUsers {getpass.getuser()}
AllowTcpForwarding no
AllowAgentForwarding no
PermitTunnel no
X11Forwarding no
PermitTTY no
MaxSessions 1
MaxStartups 2
LoginGraceTime 15
'''
    (base/'sshd_config').write_text(settings)
    (base/'sshd_config').chmod(0o600)
    return dict(target=target, workspace=str(base/'workspace'),
                command=['/usr/sbin/sshd','-D','-e','-f',str(base/'sshd_config')],
                state='prepared_not_started')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--owner-actor',type=int,required=True)
    parser.add_argument('--scope',type=int,required=True)
    parser.add_argument('--target',choices=['mac','land'],required=True)
    parser.add_argument('--public-key',type=Path,required=True)
    parser.add_argument('--listen',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=2222)
    args=parser.parse_args()
    print(json.dumps(prepare(args.base,args.owner_actor,args.scope,args.target,
                            args.public_key.read_text(),args.listen,args.port)))


if __name__ == '__main__':
    main()
