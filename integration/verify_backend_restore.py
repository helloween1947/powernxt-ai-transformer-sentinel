"""Restore a real isolated PostgreSQL dump to a second isolated database; hash rows."""
import json
import os
from pathlib import Path
import subprocess

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
import hashlib

def verify(output):
    project=os.environ.get('COMPOSE_PROJECT_NAME','')
    assert project.startswith('analytics_worker_test_')
    url=make_url(os.environ['TEST_DATABASE_URL'])
    assert url.host=='127.0.0.1' and url.database=='worker_integration_test'
    compose=['docker','compose','--profile','analytics']
    config=json.loads(subprocess.check_output(compose+['config','--format','json'],text=True))
    assert config['services']['db']['container_name']==project+'-db'
    assert str(url.port)==str(config['services']['db']['ports'][0]['published'])
    def run(*args):
        result=subprocess.run(compose+['exec','-T','db',*args],capture_output=True,text=True,check=True)
        return result.stdout
    def inventory(target):
        engine=create_engine(target)
        try:
            with engine.connect() as db:
                tables=db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")).scalars().all()
                result={}
                for table in tables:
                    rows=db.execute(text(f'SELECT to_jsonb(t) FROM "{table}" t ORDER BY to_jsonb(t)')).scalars().all()
                    result[table]={'count':len(rows),'sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()}
                return result
        finally:engine.dispose()
    before=inventory(url)
    run('pg_dump','-U','sentinel','-d','worker_integration_test','-Fc','-f','/tmp/completion-preservation.dump')
    run('createdb','-U','sentinel','worker_completion_restore_test')
    run('pg_restore','-U','sentinel','--exit-on-error','-d','worker_completion_restore_test','/tmp/completion-preservation.dump')
    restored=inventory(url.set(database='worker_completion_restore_test'))
    assert before==restored
    result={'status':'PASS','source_database':'worker_integration_test','restored_database':'worker_completion_restore_test','all_public_tables_exact':True,'tables':before,'dump_location':'isolated db container /tmp/completion-preservation.dump','credentials_or_urls_saved':False}
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args();verify(args.output)
