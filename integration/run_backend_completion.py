"""Windows isolated verification coordinator; credentials stay in child environments.

Never changes the parent environment. All Compose operations use one unique project.
Retains the volume and logs even on failure. Invoke from the owned worktree.
"""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from datetime import datetime
from uuid import uuid4
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

def main():
    project = 'analytics_worker_test_' + uuid4().hex[:12]
    api_port, db_port = free_port(), free_port()
    password = secrets.token_hex(24)
    env = os.environ.copy()
    env.update(COMPOSE_PROJECT_NAME=project,
               COMPOSE_FILE=os.pathsep.join(['compose.yaml', 'integration/compose.analytics-test.yaml', 'integration/compose.backend-completion-test.yaml']),
               ANALYTICS_TEST_PORT=str(api_port), BACKEND_TEST_DB_PORT=str(db_port),
               POSTGRES_USER='sentinel', POSTGRES_PASSWORD=password, POSTGRES_DB='worker_integration_test',
               WORKER_VERIFICATION_IMAGE_BASIS='normal repository Dockerfile --pull --no-cache on Windows')
    env['TEST_DATABASE_URL'] = f'postgresql+psycopg://sentinel:{password}@127.0.0.1:{db_port}/worker_integration_test'
    env['DATABASE_URL'] = env['TEST_DATABASE_URL']
    directory = ROOT / 'data/generated' / ('backend-completion-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    directory.mkdir(parents=True)
    report = dict(timestamp=datetime.now().astimezone().isoformat(), project=project,
                  api_port=api_port, db_port=db_port, commands=[], windows_execution=os.name=='nt',
                  source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    compose = ['docker','compose','--profile','analytics']
    def run(label, command, *, check=True):
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        output = (result.stdout + result.stderr).replace(password,'<redacted>')
        (directory / (label + '.log')).write_text(output, encoding='utf-8')
        report['commands'].append(dict(label=label, command=command, exit_code=result.returncode))
        (directory/'execution.json').write_text(json.dumps(report,indent=2)+'\n')
        print(label, 'exit=',result.returncode, flush=True)
        if result.returncode and check:
            raise RuntimeError(label + ' failed; inspect retained log')
        return result
    try:
        config = json.loads(subprocess.check_output(compose+['config','--format','json'],cwd=ROOT,env=env,text=True))
        assert config['name']==project
        assert config['volumes']['postgres_data']['name']==project+'-postgres_data'
        assert config['services']['db']['container_name']==project+'-db'
        assert config['services']['db']['environment']['POSTGRES_DB']=='worker_integration_test'
        for service in config['services'].values():
            for key in list(service.get('environment',{})):
                if any(s in key for s in ('PASSWORD','TOKEN','DATABASE_URL')):
                    service['environment'][key]='<redacted>'
        (directory/'resolved-compose.json').write_text(json.dumps(config,indent=2)+'\n')
        run('clean-build',compose+['build','--pull','--no-cache','backend','worker'])
        run('database-start',compose+['up','-d','db'])
        run('fresh-upgrade',compose+['run','--rm','backend','alembic','-c','backend/alembic.ini','upgrade','head'])
        run('backend-start',compose+['up','-d','--no-build','backend'])
        base = f'http://127.0.0.1:{api_port}'
        for attempt in range(60):
            try:
                with urlopen(base+'/health/ready',timeout=2) as response:
                    if response.status==200: break
            except Exception: time.sleep(1)
        else: raise RuntimeError('Readiness timeout')
        run('alembic-heads',compose+['exec','-T','backend','alembic','-c','backend/alembic.ini','heads'])
        run('alembic-check',compose+['exec','-T','backend','alembic','-c','backend/alembic.ini','check'])
        run('durable-worker', [sys.executable,'-m','integration.verify_analytics_worker','--base-url',base])
        run('backend-contract-tests',[sys.executable,'-m','pytest','backend/tests','analytics/contracts','-q'],check=False)
        run('docker-python312-contract-tests',compose+['run','--rm','--no-deps','-v',str(ROOT)+':/audit:ro','-w','/audit','backend','sh','-c',
            'pip install -r backend/requirements-dev.txt -r analytics/contracts/requirements-test.txt && python -m pytest backend/tests analytics/contracts -q -p no:cacheprovider'],check=False)
        run('populated-upgrade',[sys.executable,'-c',
            "import os; from integration.rehearse_populated_migration import run_rehearsal; run_rehearsal(os.environ['TEST_DATABASE_URL'],r'"+str(directory/'populated-migration.json')+"')"])
        # Additional live acceptance verifier is deliberately separate from pytest.
        if (ROOT/'integration/verify_backend_completion.py').exists():
            run('live-completion',[sys.executable,'-m','integration.verify_backend_completion','--base-url',base,'--output',str(directory/'live-completion.json')])
        run('backup-restore',[sys.executable,'-m','integration.verify_backend_restore','--output',str(directory/'backup-restore.json')])
        run('images',compose+['images','--format','json'])
        report['status']='PASS' if all(c['exit_code']==0 for c in report['commands']) else 'FAIL'
    except Exception as exc:
        report['status']='FAIL'
        report['failure']=str(exc)
        run('isolated-failure-logs',compose+['logs','--no-color','--tail','100','backend','worker'],check=False)
    finally:
        stopped=run('isolated-stop',compose+['stop','worker','backend','db'],check=False)
        report.update(isolated_stack_stopped=stopped.returncode==0, volume_retained=True,
                      parent_environment_unchanged=True)
        (directory/'execution.json').write_text(json.dumps(report,indent=2)+'\n')
        print(str(directory),report['status'],flush=True)
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':
    raise SystemExit(main())
