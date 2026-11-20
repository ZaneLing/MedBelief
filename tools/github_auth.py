"""Use ordinary gh/Git authentication without writing or displaying credentials."""
import os,subprocess

def environment():
 env=dict(os.environ)
 if env.get('GH_TOKEN') or env.get('GITHUB_TOKEN'):return env
 ok=subprocess.run(['gh','auth','status','--hostname','github.com'],capture_output=True).returncode==0
 if ok:return env
 r=subprocess.run(['git','credential','fill'],input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,env=dict(env,GIT_TERMINAL_PROMPT='0'))
 if r.returncode==0:
  c=dict(line.split('=',1) for line in r.stdout.splitlines() if '=' in line)
  if c.get('password'):env['GH_TOKEN']=c['password'];return env
 raise RuntimeError('Authenticate with gh auth login --hostname github.com; do not paste a token into the project.')
