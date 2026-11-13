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
                    'arguments':[ast.unparse(arg) for arg in node.args], 'fields':{kw.arg:ast.unparse(kw.value) for kw in node.keywords if kw.arg},
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
                    elif isinstance(target,ast.Tuple) and isinstance(node.value,ast.Tuple):
                        for item,value in zip(target.elts,node.value.elts):
                            if isinstance(item,ast.Name):symbols[item.id]=value
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
    phase0_end=len(registered)
    m1=modules['corpus_structure.orchestrate.m1'][1]['registry']
    for child in m1.body:
        if isinstance(child,ast.ImportFrom):
            prefix='.'.join([*'corpus_structure.orchestrate.m1'.split('.')[:-child.level],child.module or ''])
            for alias in child.names:modules['corpus_structure.orchestrate.m1'][1][alias.asname or alias.name]=prefix+'.'+alias.name
        if isinstance(child,ast.Return) and isinstance(child.value,ast.Call):
            expand('corpus_structure.orchestrate.m1',child.value.args[0],())
    def qualified(module,node):
        if isinstance(node,ast.Name):
            value=modules[module][1].get(node.id)
            return value if isinstance(value,str) else module+'.'+node.id
        if isinstance(node,ast.Attribute):return qualified(module,node.value)+'.'+node.attr
        return ast.unparse(node)
    def literal(module,node,seen=()):
        try:return ast.literal_eval(node)
        except (TypeError,ValueError):pass
        if isinstance(node,ast.Name) and (module,node.id) not in seen:
            value=modules[module][1].get(node.id)
            if isinstance(value,ast.AST):return literal(module,value,(*seen,(module,node.id)))
            if isinstance(value,str):return value
        return {'source_reference':qualified(module,node)}
    def class_facts(module,cls,seen=()):
        if (module,cls.name) in seen:return ({},{})
        fields={}; dispatch={}
        for base in cls.bases:
            target=definition(qualified(module,base))
            if target and isinstance(target[1],ast.ClassDef):
                attrs,methods=class_facts(*target,(*seen,(module,cls.name)))
                fields.update(attrs);dispatch.update(methods)
        for child in cls.body:
            if isinstance(child,(ast.FunctionDef,ast.AsyncFunctionDef)):
                dispatch[child.name]={'owner':module+'.'+cls.name+'.'+child.name,'line':child.lineno}
            elif isinstance(child,(ast.Assign,ast.AnnAssign)):
                for name in (child.targets if isinstance(child,ast.Assign) else [child.target]):
                    if isinstance(name,ast.Name) and child.value is not None:
                        fields[name.id]=literal(module,child.value)
        return fields,dispatch
    effective=[]
    for i,entry in enumerate(registered):
        target=definition(entry['module']+'.'+entry['class'])
        if target and isinstance(target[1],ast.ClassDef):
            fields,dispatch=class_facts(*target)
            effective.append({**entry,'registry':'phase0' if i<phase0_end else 'm1',
                'identity':{k:fields.get(k) for k in ('name','version','Config','family','unit_type')},
                'dispatch':{k:v for k,v in dispatch.items() if k in ('select','input_digest','run','plan','close')},
                'publisher_consumer':'native source/unit completion and pinned contribution/characterization readers; DDO-07/08 migrate the actual family'})
    dynamic=[]
    for rel in source_files:
        if not rel.endswith(('/orchestrate/semantic.py','/orchestrate/ready.py')):continue
        for node in ast.walk(ast.parse((ROOT/rel).read_bytes())):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='getattr' and len(node.args)>1 and isinstance(node.args[1],ast.Constant) and node.args[1].value in ('plan','close'):
                dynamic.append({'source':rel,'line':node.lineno,'capability':node.args[1].value,'migration_owner':'DDO-08 typed capability replacement'})
            if isinstance(node,ast.Constant) and node.value in ('source_dependencies','source_dependency_method'):
                dynamic.append({'source':rel,'line':node.lineno,'capability':node.value,'migration_owner':'DDO-08 declared input dependency replacement'})
    configs=[]
    for path in sorted((ROOT/'domains').glob('*/*methods.yaml')):
        value=yaml.safe_load(path.read_text()) or {}
        configs.append({'source':str(path.relative_to(ROOT)),'method_ids':sorted((value.get('configs') or {}).keys()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return {'schema':'ddo-operation-inventory-v2', 'registered_constructor_evidence':registered, 'effective_registry_entries':effective, 'dynamic_dispatch_consumers':dynamic,
        'registry_unresolved':sorted(set(u for u in unresolved if not u.endswith(':producer'))), 'pack_configurations':configs,'catalog_sha256':hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        'operations':operations,'method_candidates':candidates,'descriptor_sites':bypasses,
        'examined_sources':source_files,
        'limits':['method_candidates is a lexical candidate list; effective_registry_entries reconciles phase0 and M1 roots',
                  'scope is both repository registries, all repository pack configurations, declared protocol operations and explicit descriptor/dynamic dispatch sites; no unconfigured external plugin completeness claim',
                  'profile labels are DDO-00 inventory classification, not compiler authority or inferred runtime behavior']}

if __name__ == '__main__':
    result=inventory()
    (Path(__file__).parent/'raw/inventory-v2.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print({key:len(result[key]) for key in ('operations','method_candidates','descriptor_sites','examined_sources')})
