import jadn
import json
import os
from jadn.definitions import has_fields, TypeName, BaseType, TypeOptions
from graphlib import TopologicalSorter

# SCHEMA_DIR = os.path.join('..', '..', 'Schemas', 'Metaschema')
# JSCHEMA = os.path.join(SCHEMA_DIR, 'oscal_catalog_schema_1.1.0.json')
SCHEMA_DIR = os.path.join('oscal-1.1.2', 'json', 'schema')
OUT_DIR = '../../Out'
DEBUG = False
D = [(f'${n}' if DEBUG else '') for n in range(10)]


def typedefname(jsdef: str) -> str:
    """
    Infer type name from a JSON Schema definition
    """
    assert isinstance(jsdef, str), f'Not a type definition name: {jsdef}'
    if d := jss['definitions'].get(jsdef, ''):
        if ':' in jsdef:  # qualified definition name
            tn = maketypename('', jsdef.split(':', maxsplit=1)[1]) + D[1]
            return tn
        if ref := d.get('$ref', ''):
            return ref.removeprefix('#/definitions/')+ D[2]
    return jsdef.removeprefix('#/definitions/') + D[0]     # Exact type name or none


def typerefname(jsref: dict) -> str:
    """
    Infer a type name from a JSON Schema property reference
    """
    if (t := jsref.get('type', '')) in ('string', 'integer', 'number', 'boolean', 'binary'):
        return t.capitalize() + D[4]    # Built-in type
    if ref := jsref.get('$ref', ''):
        td = jssx.get(ref, ref)
        if td.startswith('#/definitions/'):  # Exact type name
            return td.removeprefix('#/definitions/') + D[5]
        if ':' in td:
            return maketypename('', td.split(':', maxsplit=1)[1]) + D[6]  # Extract type name from $id
        if td2 := jss['definitions'].get(td, {}):
            return typerefname(td2) + D[7]
    return ''


def singular(name: str) -> str:
    """
    Guess a singular type name for the anonymous items in a plural ArrayOf type
    """
    if name.endswith('ies'):
        return name[:-3] + 'y'
    elif name.endswith('es'):
        n = -2 if name[-4:-3] == 's' else -1
        return name[:n]
    elif name.endswith('s'):
        return name[:-1]
    return name + '-item'


def plural(name: str) -> str:
    """
    Guess a plural type name for anonymous ArrayOf types with named item types
    """
    if name.endswith('y'):
        return name[:-1] + 'ies'
    elif name.endswith('s'):
        return name + 'es'
    return name + 's'


def maketypename(tn: str, name: str) -> str:
    """
    Convert a type and property name to type name
    """
    tn = typedefname(tn)
    name = f'{tn}${name}' if tn else name.capitalize()
    return name + '1' if jadn.definitions.is_builtin(name) else name


def is_defined(items: dict) -> bool:
    return '$ref' in items or items.get('type', '') in {'string', 'integer', 'number', 'boolean'}


def scandef(tn: str, key: str, tv: dict, nt: list):
    global seen, rseen, level, rlevel
    """
    Process nested type definitions, add to list nt
    """
    basetype = ''
    fields = []
    popts = ''
    # print(f'->{rlevel:3}{min(level, 10)*" ."}{key}:  {tv.get("$ref", tv.get("type", tv.get("allOf", tv.get("anyOf", tv))))}')
    if ref := tv.get('$ref', ''):
        dn = typedefname(rn := jssx.get(ref, ref))
        if ref not in rseen:
            tva = jss['definitions'][dn if dn in jss['definitions'] else rn]
            rlevel += 1
            d = scandef(dn, '', tva, nt)
            rlevel -= 1
            rseen.update((ref,))
        if tn not in seen and '.' not in tn and ':' not in tn and tn != 'json-schema-directive':  # Construct referenced "Alias" type from Choice
            print(f'Alias {tn} -> {dn}')
            seen.update({tn: tv})
            tdesc = tv.get('description', tv.get('title', ''))
            nt.append([tn, 'Choice', ['CA'], tdesc, [[1, 'alias', dn, [], '']]])
        return dn
    elif (vtype := tv.get('type', '')) in {'string', 'integer', 'number', 'boolean'}:
        basetype = vtype.capitalize()
    elif vtype == 'object':
        if tn not in seen:
            seen.update({tn: tv})
            basetype = 'Record'
            level += 1
            # print(f'->{level} Record({tn})')
            for k, v in tv.get('properties', {}).items():
                fields.append((k, scandef(f'{tn}.{k}', k, v, nt), v))
            popts = f'\n<-{level} Record({tn}){[k[0] for k in fields]}'
            level -= 1
    elif vtype == 'array':
        if isinstance(items := tv.get('items', {}), dict):
            fields.append((scandef(f'{tn}', '', items, nt)))
            if is_defined(items):
                return fields[0]
            basetype = 'ArrayOf'
            tn += '-list'
            popts = f'({fields[0]})'
        elif isinstance(items, list):
            for n, v in enumerate(items):
                scandef(f'{tn}.{n}', '', v, nt)
            print(f'- {tn}: ArrayX')
    elif enum := tv.get('enum', []):
        basetype = 'Enumerated'
        for v in enum:
            fields.append(v)
        popts = f'({len(fields)})'
    elif cc := [c for c in ('anyOf', 'allOf', 'oneOf') if c in tv][0]:
        basetype = 'Choice'
        for n, v in enumerate(tv[cc]):
            fields.append(scandef(f'{tn}.{n}', '', v, nt))
        popts = f'({cc})({len(fields)})'
    else:
        raise ValueError(f'- {tn}: Unexpected type: {vtype}: {tv}')

    if basetype:
        lv = f'< {rlevel:3}{min(level,10)*" ."} '
        # if rlevel < 15:
            # print(f'{lv} {tn:80}: {basetype}' if ref else f'{lv} {tn}: {basetype}{popts}')
        td = make_jadn_type(tn, basetype, fields, tv)
        if '.' in tn:   # if generated type and built-in with no options, optimize it out. TODO: match $SYS
            if td[BaseType] in {'String', 'Integer', 'Number', 'Boolean'} and len(td[TypeOptions]) == 0:
                return td[BaseType]
        nt.append(td)
        return td[TypeName]

    # if rlevel < 15:
        # print(f'  {rlevel:3}{min(level,10)*" ."} {key}: *** No basetype {tn}')


def make_jadn_type(tn: str, basetype: str, flist: list, tv: dict):
    tnroot, tnpath = tn.split('.', maxsplit=1) if '.' in tn else (tn, '')
    typename = typedefname(tnroot) + (f'.{tnpath}' if tnpath else '')
    topts = []
    fields = []
    tdesc = tv.get('description', tv.get('title', ''))
    if basetype == 'Record':
        req = tv.get('required', [])
        for n, f in enumerate(flist, start=1):
            k, v, fv = f
            fdesc = fv.get('description', '')
            fopts = ['[0'] if k not in req else []
            # if fv.get('type', '') == 'array':
            #     fopts.append(f']{fv.get("maxItems", 0)}')
            fields.append([n, k, v, fopts, fdesc])

    elif basetype == 'ArrayOf':
        topts = [f'{{{tv["minItems"]}'] if 'minItems' in tv else []
        topts.append(f'}}{tv["maxItems"]}') if 'maxItems' in tv else '}0'
        topts.append(f'*{flist[0]}')

    elif basetype == 'Enumerated':
        for n, f in enumerate(flist, start=1):
            fields.append([n, f, ''])

    elif basetype == 'Choice':
        cc = [c for c in ('anyOf', 'allOf', 'oneOf') if c in tv][0]
        topts = [{
            'anyOf': 'CO',
            'allOf': 'CA',
            'oneOf': 'CX'
        }[cc]]
        for n, v in enumerate(flist, start=1):
            fields.append([n, f'c{n}', v, [], ''])

    elif basetype == 'String':  # process string opts
        if x := tv.get('format', ''):
            topts.append(f'/{x}')
        if x := tv.get('pattern', ''):
            topts.append(f'%{x}')
    elif basetype == 'Integer':
        pass # process integer opts
    elif basetype == 'Number':
        pass # process number opts
    elif basetype == ('Boolean'):
        pass # done - no opts on boolean
    elif basetype:
        raise ValueError(f'unsupported type {basetype}')

    return [typename, basetype, topts, tdesc, fields]


def convert_js_to_jadn(jsfile, outfile):
    global jss, jssx, seen, rseen, level, rlevel
    """
    Create a JADN type from each definition in a Metaschema-generated JSON Schema
    """
    with open(jsfile, encoding='utf-8') as fp:
        jss = json.load(fp)
    assert jss['type'] == 'object', f'Unsupported JSON Schema format {jss["type"]}'
    jssx = {v.get('$id', k): k for k, v in jss['definitions'].items()}      # Index from $id to definition
    assert len(jssx) == len(jss['definitions']), f'$ids {len(jssx)} != defs {len(jss["definitions"])}'
    seen = {}   # Index of $refs to jss definitions
    rseen = set()   # Set of $refs already processed
    level = 0
    rlevel = 0

    info = {'package': jss['$id'].rstrip('.json')}
    info.update({'comment': jss['$comment']} if '$comment' in jss else {})
    info.update({'exports': ['$Root']})
    info.update({'config': {
        '$MaxString': 1000,
        '$TypeName': '^[$A-Z][-.$A-Za-z0-9]{0,96}$',
        '$FieldName': '^[$a-z][-_$A-Za-z0-9]{0,63}$',
        '$NSID': '^([A-Za-z][-A-Za-z0-9]{0,31})?$'}})

    nt = []     # Walk nested type definition tree to build type list
    scandef('$Root', '', jss, nt)
    for tn, tv in jss['definitions'].items():
        scandef(tn, '', tv, nt)
    ntx = {k[TypeName]: k for k in nt}
    deps = jadn.build_deps({'types': nt})
    for k, v in deps.items():
        if k in v:
            print(f'### deleted self-loop: {k}({len(v)}) {v}')
            deps[k] = deps[k] - {k, }

    def place_type(tname: str) -> None:
        try:
            if tdef := ntx.pop(tname):
                if tname.endswith('-list'):
                    nt1.append(tdef)
                    if tdef := ntx.pop(tname.rstrip('-list')):
                        nt1.append(tdef)
                elif tdef[BaseType] == 'Enumerated':
                    nt1.append(tdef)
                elif has_fields(tdef[BaseType]):
                    nt1.append(tdef)
                else:
                    nt3.append(tdef)
        except KeyError:
            pass

    def walk_types(tname: str) -> None:
        place_type(tname)
        for tn in deps[tname]:
            walk_types(tn)

    nt1, nt2, nt3 = [], [], []
    tn = e[0] if len(e := info.get('exports', [])) else ntx.get('$Root')[TypeName]
    walk_types(tn)

    print(f'{len(ntx)} unreferenced types: { {k for k in ntx} }')
    """
    ts = TopologicalSorter(deps)
    ts.prepare()
    nodes = []
    roots = {k: 0 for k in deps}
    while ts.is_active():
        nodes.append(n := ts.get_ready())
        ts.done(*n)
        for k in n:
            for j in deps[k]:
                roots[j] = len(nodes)
    ns = set(ntx)
    n = '$Root'
    for k in deps[n]:
        ns -= set(k)
    """

    schema = {'info': info, 'types': nt1 + nt2 + nt3}
    jadn.dump(schema, outfile)
    try:
        print('\n'.join([f'{k:>15}: {v}' for k, v in jadn.analyze(jadn.check(schema)).items()]))
    except ValueError as e:
        print(f'### {f}: {e}')


if __name__ == '__main__':
    jss = {}    # JSON-Schema schema
    jssx = {}   # Index of $ids to jss definitions
    seen = {}   # Index of $refs to jss definitions
    rseen = set()   # Set of $refs already processed
    level = 0
    rlevel = 0
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(SCHEMA_DIR):
        jsfile = os.path.join(SCHEMA_DIR, f)
        fn, fe = os.path.splitext(f)
        outfile = os.path.join(OUT_DIR, fn) + '.jadn'
        try:
            print(f'=== {jsfile}')
            convert_js_to_jadn(jsfile, outfile)
        except (ValueError, IndexError) as e:
            print(f'### {f}: {e}')
            raise
