#!/usr/bin/env python3
"""Small official Codex CLI A/B pilot for GPT-5.6-sol vs Hy4-preview."""
from __future__ import annotations
import json, os, re, shutil, subprocess, tempfile, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SECRETS=ROOT/'configs/secrets.env.local'

def local_env():
 d={}
 for line in SECRETS.read_text().splitlines() if SECRETS.exists() else []:
  line=line.strip()
  if line and not line.startswith('#') and '=' in line:
   k,v=line.split('=',1);d[k.strip()]=v.strip().strip('"').strip("'")
 return d

TASKS=[
 ('logic_chain','有约束 A 在 B 前，B 在 C 前，D 和 E 无约束。以下哪个任务必然在 B 之后？只输出一个字母。','C'),
 ('math_multi','一个数先乘 7，再减 13，结果为 50。这个数是多少？只输出最终整数。','9'),
 ('code_contract','只输出 Python 代码：定义 two_sum(nums,target)，返回两下标使其和为 target，无解返回 [-1,-1]；并在代码中打印 two_sum([2,7,11,15],9) 的结果。','[0, 1]'),
 ('constraint','只输出三行：第一行 ALPHA；第二行必须是字符串 123；第三行 omega。不要编号、解释或 Markdown。','ALPHA'),
 ('json','只输出严格 JSON：{"answer":42,"steps":["add","multiply"],"confidence":0.9}，不得包含 Markdown。','"answer":42'),
 ('long_retrieval','下面有 180 条记录。请只输出唯一目标代码，不要解释。\n'+('普通记录\n'*89)+'唯一目标代码：ZX-4179\n'+('普通记录\n'*90),'ZX-4179'),
]

def run_cli(prompt, model, hy4_home=None, base_url=None):
 env=os.environ.copy()
 if hy4_home:
  env['CODEX_HOME']=hy4_home
 else:
  # Keep the user's normal Codex configuration for the GPT control run.
  env.pop('CODEX_HOME', None)
 args=['codex','exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','--model',model,'--json']
 if hy4_home:
  args += ['-c','model_provider="tencent"','-c','model_providers.tencent.name="tencent"',
           '-c',f'model_providers.tencent.base_url="{base_url or "https://tokenhub.tencentmaas.com/v1"}"',
           '-c','model_providers.tencent.wire_api="responses"','-c','model_providers.tencent.requires_openai_auth=true']
 try:
  p=subprocess.run(args+[prompt],cwd=str(ROOT),env=env,capture_output=True,text=True,timeout=360)
 except subprocess.TimeoutExpired as e:
  return {'status':'timeout','stdout':(e.stdout or '')[-4000:]}
 messages=[]; errors=[]
 for line in p.stdout.splitlines():
  try:
   x=json.loads(line)
   if x.get('type')=='item.completed':
    item=x.get('item') or {}
    if item.get('type')=='agent_message': messages.append(item.get('text',''))
    if item.get('type')=='error': errors.append(item.get('message',''))
   if x.get('type')=='error': errors.append(x.get('message',''))
  except Exception: pass
 final=messages[-1] if messages else ''
 return {'status':'ok' if p.returncode==0 and final else 'failed','returncode':p.returncode,'final':final,'errors':errors,'stderr':p.stderr[-2000:]}

def checks(row):
 text=row.get('final','').strip()
 tid=row['id']
 if tid=='logic_chain': return text=='C'
 if tid=='math_multi': return text=='9'
 if tid=='constraint': return text.splitlines()==['ALPHA','123','omega']
 if tid=='json':
  try: return json.loads(text)=={'answer':42,'steps':['add','multiply'],'confidence':0.9}
  except Exception: return False
 if tid=='long_retrieval': return text=='ZX-4179'
 if tid=='code_contract':
  m=re.search(r'```(?:python)?\s*(.*?)```',text,re.S)
  code=m.group(1) if m else text
  with tempfile.TemporaryDirectory(prefix='codex-code-check-') as d:
   f=Path(d)/'answer.py'; f.write_text(code)
   try:
    p=subprocess.run(['python',str(f)],capture_output=True,text=True,timeout=10)
    return p.returncode==0 and p.stdout.strip()=='[0, 1]'
   except (OSError, subprocess.TimeoutExpired): return False
 return False

def main():
 d=local_env(); key=d.get('TENCENT_MAAS_API_KEY','')
 if not key: raise SystemExit('missing TENCENT_MAAS_API_KEY')
 base_url=d.get('TENCENT_MAAS_BASE_URL','https://tokenhub.tencentmaas.com/v1').rstrip('/')
 home=tempfile.mkdtemp(prefix='codex-tencent-ab-')
 try:
  login=subprocess.run(['codex','login','--with-api-key'],input=key+'\n',text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={**os.environ,'CODEX_HOME':home},timeout=60)
  if login.returncode!=0: raise SystemExit('temporary Codex auth setup failed')
  out=[]
  for tid,prompt,expected in TASKS:
   print('Hy4',tid,flush=True);t=time.perf_counter(); r=run_cli(prompt,'hy4-preview',home,base_url); r.update({'model':'hy4-preview','id':tid,'expected':expected,'elapsed_sec':round(time.perf_counter()-t,2)}); r['match']=checks(r); out.append(r)
   time.sleep(3)
   print('GPT',tid,flush=True);t=time.perf_counter(); r=run_cli(prompt,'gpt-5.6-sol'); r.update({'model':'gpt-5.6-sol','id':tid,'expected':expected,'elapsed_sec':round(time.perf_counter()-t,2)}); r['match']=checks(r); out.append(r)
  path=ROOT/'data/reports/2026-08-30-codex-ab.json';path.write_text(json.dumps(out,ensure_ascii=False,indent=2));print('saved',path)
 finally:
  shutil.rmtree(home,ignore_errors=True)
if __name__=='__main__':main()
