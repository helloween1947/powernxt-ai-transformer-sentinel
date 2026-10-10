"""Run contract/frontend checks against a separate owned test database, redact secrets."""
import os
from pathlib import Path
import subprocess
import sys
import json
from datetime import datetime, timezone
root = Path(__file__).resolve().parents[1]
private = dict(line.split('=', 1) for line in (root/'data/generated/single-transformer/private.env').read_text().splitlines() if '=' in line)
password = private['SINGLE_DB_PASSWORD']
compose = ['docker','compose','--env-file','data/generated/single-transformer/private.env','-f','integration/compose.single-transformer.yaml']
logdir=root/'docs/evidence/single-transformer-app-20261011'
report={'timestamp':datetime.now(timezone.utc).isoformat(),'commands':[],'windows_execution':os.name=='nt'}
def run(name, command, env=None):
    p=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (logdir/(name+'.log')).write_text((p.stdout+p.stderr).replace(password,'<redacted>'),encoding='utf-8')
    report['commands'].append({'name':name,'command':command,'exit_code':p.returncode})
    (logdir/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(name,'exit',p.returncode,flush=True)
    if p.returncode: raise RuntimeError('Inspect '+name+'.log')
existing = subprocess.check_output(compose+['exec','-T','db','psql','-U','sentinel','-d','postgres','-Atc',"SELECT 1 FROM pg_database WHERE datname='single_transformer_contract_test'"], cwd=root, text=True).strip()
if existing != '1':
    run('contract-database',compose+['exec','-T','db','createdb','-U','sentinel','single_transformer_contract_test'])
env=os.environ.copy()
env['DATABASE_URL']=env['TEST_DATABASE_URL']=f"postgresql+psycopg://sentinel:{password}@127.0.0.1:{private['SINGLE_DB_PORT']}/single_transformer_contract_test"
run('backend-contract-tests',[sys.executable,'-m','pytest','backend/tests','analytics/contracts','-q','--tb=short'],env)
run('frontend-tests',['npm.cmd','test','--prefix','frontend'])
run('frontend-lint',['npm.cmd','run','lint','--prefix','frontend'])
run('frontend-build',['npm.cmd','run','build','--prefix','frontend'])
run('sample-mapper-tests',['node','--test','integration/frontend/maintenanceAdapter.test.mjs'])
run('final-docker-build',compose+['build','backend','frontend'])
run('frontend-refresh',compose+['up','-d','--no-build','--no-deps','--wait','frontend'])
print('PASS checks; test database retained; parent environment unchanged')
