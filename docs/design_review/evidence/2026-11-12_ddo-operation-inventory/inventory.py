"""Frozen source/catalog inventory; never import application implementations."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / 'python/corpus-structure/src/corpus_structure'

def inventory():
    catalog_path = PACKAGE / 'model/semantic/execution-model.yaml'
    catalog = yaml.safe_load(catalog_path.read_text())
    implementations = {x['id']: x for x in catalog['implementations']}
    operations = []
    for op in catalog['operations']:
        impl = implementations.get(op.get('implementation'), {})
        operations.append({
            'id': op['id'], 'authority': 'declaration-owned protocol',
            'source': str(catalog_path.relative_to(ROOT)),
            'profile': ('command' if op.get('effects') else 'selection' if op.get('outcome_domain') in {'selection','admission'} else 'read' if op['id'].startswith(('read_', 'inspect_', 'open_', 'query', 'explain', 'validate_continuation')) else 'derivation'),
            'inputs': op.get('inputs', []), 'results': op.get('results', []),
            'applicability': op.get('applicability', []), 'effects': op.get('effects', []),
            'outcomes': op.get('outcomes', []), 'dependencies': op.get('dependencies', []),
            'implementation': impl, 'calls': op.get('calls', []),
            'migration_owner': 'DDO-01/03 definition; DDO-04/07/08 native/adapter consumer',
        })
    candidates, bypasses, source_files = [], [], {}
    for path in sorted(PACKAGE.rglob('*.py')):
        if '/_model/' in str(path):
            continue
        raw = path.read_bytes()
        tree = ast.parse(raw, filename=str(path))
        relative = str(path.relative_to(ROOT))
        source_files[relative] = hashlib.sha256(raw).hexdigest()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                attrs = {}
                for statement in node.body:
                    if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
                        continue
                    targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                    for target in targets:
                        if isinstance(target, ast.Name) and statement.value is not None:
                            try:
                                attrs[target.id] = ast.literal_eval(statement.value)
                            except (ValueError, TypeError):
                                pass
                if isinstance(attrs.get('name'), str) and any(
                    isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name in {'run','plan','select'}
                    for m in node.body
                ):
                    candidates.append({'id': attrs['name'], 'class': node.name,
                        'source': relative, 'line': node.lineno,
                        'bases': [ast.unparse(base) for base in node.bases],
                        'local_capabilities': [m.name for m in node.body if isinstance(m, (ast.FunctionDef,ast.AsyncFunctionDef))],
                        'authority': 'implementation-owned candidate; reconcile actual registry',
                        'migration_owner': 'DDO-07/08', 'version': attrs.get('version')})
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'OperationDescriptor':
                bypasses.append({'source':relative,'line':node.lineno,
                    'fields':{kw.arg:ast.unparse(kw.value) for kw in node.keywords if kw.arg},
                    'migration_owner':'DDO-08 descriptor replacement'})
    modules = {}
    for rel in source_files:
        path=ROOT/rel
        module='corpus_structure.'+str(path.relative_to(PACKAGE).with_suffix('')).replace('/', '.')
        if module.endswith('.__init__'): module=module[:-9]
        tree=ast.parse(path.read_bytes())
        symbols={}
        for node in tree.body:
            if isinstance(node,ast.ImportFrom):
                prefix=node.module or ''
                if node.level:
                    parts=module.split('.')[:-node.level]
                    prefix='.'.join([*parts,*([prefix] if prefix else [])])
                for alias in node.names: symbols[alias.asname or alias.name]=prefix+'.'+alias.name
            elif isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
                symbols[node.name]=node
            elif isinstance(node,(ast.Assign,ast.AnnAssign)):
                targets=node.targets if isinstance(node,ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target,ast.Name): symbols[target.id]=node.value
        modules[module]=(rel,symbols)
    def definition(reference, trail=()):
        if reference in trail: return None
        mod,_,name=reference.rpartition('.')
        if mod not in modules:return None
        value=modules[mod][1].get(name)
        if isinstance(value,str):return definition(value,(*trail,reference))
        return (mod,value) if value is not None else None
    registered=[]; unresolved=[]
    def expand(module,node,seen=()):
        if isinstance(node,(ast.Tuple,ast.List)):
            for child in node.elts:expand(module,child,seen)
        elif isinstance(node,ast.Starred):expand(module,node.value,seen)
        elif isinstance(node,ast.Name):
            ref=modules[module][1].get(node.id)
            if isinstance(ref,str):expand_ref(ref,seen)
            elif isinstance(ref,ast.AST):expand(module,ref,seen)
            else:unresolved.append(module+':'+node.id)
        elif isinstance(node,ast.Attribute) and isinstance(node.value,ast.Name):
            owner=modules[module][1].get(node.value.id)
            if isinstance(owner,str):expand_ref(owner+'.'+node.attr,seen)
            else:unresolved.append(module+':'+ast.unparse(node))
        elif isinstance(node,ast.Call):
            name=ast.unparse(node.func)
            ref=modules[module][1].get(name)
            target=definition(ref) if isinstance(ref,str) else (module,ref)
            if target and isinstance(target[1],ast.ClassDef):
                registered.append({'module':target[0],'class':target[1].name,'line':target[1].lineno,'authority':'implementation-owned','migration_owner':'DDO-07/08'})
            elif target and isinstance(target[1],ast.FunctionDef):
                for child in target[1].body:
                    if isinstance(child,ast.ImportFrom):
                        prefix=child.module or ''
                        if child.level:prefix='.'.join([*target[0].split('.')[:-child.level],prefix])
                        for alias in child.names:modules[target[0]][1][alias.asname or alias.name]=prefix+'.'+alias.name
                for child in target[1].body:
                    if isinstance(child,ast.Return):expand(target[0],child.value,seen)
                # Local construction binding inside the factory.
                for child in target[1].body:
                    if isinstance(child,ast.Assign) and isinstance(child.value,ast.Call):expand(target[0],child.value,seen)
            else:unresolved.append(module+':'+name)
        else:unresolved.append(module+':'+type(node).__name__)
    def expand_ref(ref,seen):
        if ref in seen:unresolved.append('cycle:'+ref);return
        target=definition(ref)
        if target:expand(target[0],target[1],(*seen,ref))
        else:unresolved.append(ref)
    expand_ref('corpus_structure.orchestrate.phase0.METHODS',())
    configs=[]
    for path in sorted((ROOT/'domains').glob('*/methods.yaml')):
        value=yaml.safe_load(path.read_text()) or {}
        configs.append({'source':str(path.relative_to(ROOT)),'method_ids':sorted((value.get('configs') or {}).keys()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return {'schema':'ddo-operation-inventory-v1', 'registered_constructor_evidence':registered,
        'registry_unresolved':sorted(set(u for u in unresolved if not u.endswith(':producer'))), 'pack_configurations':configs,'catalog_sha256':hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        'operations':operations,'method_candidates':candidates,'descriptor_sites':bypasses,
        'examined_sources':source_files,
        'limits':['candidate method scan does not prove registry membership or inherited names',
                  'external pack methods/plugins and implicit action consumers require explicit reconciliation',
                  'profile labels are DDO-00 inventory classification, not compiler authority or inferred runtime behavior']}

if __name__ == '__main__':
    result=inventory()
    (Path(__file__).parent/'raw/inventory.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print({key:len(result[key]) for key in ('operations','method_candidates','descriptor_sites','examined_sources')})
