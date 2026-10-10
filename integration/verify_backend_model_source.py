"""Compare vendored computational definitions with recorded authoritative Git source."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def verify(output):
    manifest=json.loads((ROOT/'backend/app/analytics/person_b/ADOPTION_MANIFEST.json').read_text())
    source=manifest['source_manifest'];commit=source['computation_source_commit']
    upstream={}
    for record in source['source_files']:
        data=subprocess.check_output(['git','show',commit+':'+record['path']],cwd=ROOT).replace(b'\r\n',b'\n')
        assert hashlib.sha256(data).hexdigest()==record['sha256'],record['path']
        upstream[record['path']]=data.decode()
    def definitions(code):
        return {node.name:ast.dump(node,include_attributes=False) for node in ast.parse(code).body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
    checked=[]
    for module,names in manifest['function_class_ast_equal_to_source'].items():
        if module=='core':
            originals={**definitions(upstream['analytics/transformer_twin/model.py']),**definitions(upstream['analytics/transformer_twin/engine.py'])}
        else:originals=definitions(upstream['analytics/'+module+'.py'])
        adopted=definitions((ROOT/f'backend/app/analytics/person_b/{module}.py').read_text(encoding='utf-8'))
        for name in names:
            assert adopted[name]==originals[name],(module,name)
            checked.append(module+'.'+name)
    hashes={}
    for section in ('adapted_sha256','historical_sha256'):
        for path,expected in manifest[section].items():
            actual=hashlib.sha256((ROOT/path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            assert actual==expected,path
            hashes[path]=actual
    result={'status':'PASS','computation_source_commit':commit,'source_files_verified':len(upstream),'computational_definitions_equal':checked,'definitions_count':len(checked),'adapted_and_historical_hashes':hashes,'equations_changed':False}
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    print('PASS:',len(checked),'computational definitions;',len(upstream),'source files;',len(hashes),'adopted/historical hashes')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args();verify(args.output)
