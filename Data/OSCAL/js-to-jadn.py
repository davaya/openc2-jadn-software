import jadn
import json
import os
from jadn.definitions import TypeName

# SCHEMA_DIR = os.path.join('..', '..', 'Schemas', 'Metaschema')
# JSCHEMA = os.path.join(SCHEMA_DIR, 'oscal_catalog_schema_1.1.0.json')
SCHEMA_DIR = os.path.join('oscal-1.1.2', 'json', 'schema')
OUT_DIR = 'Out'
DEBUG = False
D = [(f'${n}' if DEBUG else '') for n in range(10)]


def typedefname(jsdef: str, jss: dict) -> str:
    """
    Infer type name from a JSON Schema definition
    """
    assert isinstance(jsdef, str), f'Not a type definition name: {jsdef}'
    if d := jss['definitions'].get(jsdef, ''):
        if ':' in jsdef:  # qualified definition name
            tn = maketypename('', jsdef.split(':', maxsplit=1)[1], jss) + D[1]
            # print(f'{jsdef:60} -> {tn}')
            return tn
        if ref := d.get('$ref', ''):
            return ref.removeprefix('#/definitions/')+ D[2]
    return jsdef.removeprefix('#/definitions/') + D[0]     # Exact type name or none


def typerefname(jsref: dict, jss: dict, jssx: dict) -> str:
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
            return maketypename('', td.split(':', maxsplit=1)[1], jss) + D[6]  # Extract type name from $id
        if td2 := jss['definitions'].get(td, {}):
            return typerefname(td2, jss, jssx) + D[7]
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


def maketypename(tn: str, name: str, jss: dict) -> str:
    """
    Convert a type and property name to type name
    """
    tn = typedefname(tn, jss)
    name = f'{tn}${name}' if tn else name.capitalize()
    return name + '1' if jadn.definitions.is_builtin(name) else name


def scandef(tn: str, tv: dict, nt: list, jss: dict, jssx: dict):
    """
    Process nested type definitions, add to list nt
    """
    basetype = ''
    fields = []
    popts = ''
    if ref := tv.get('$ref', ''):
        dn = typedefname(jssx.get(ref, ref), jss)
        print(f'- {tn:80}: {dn}')
        return dn
    elif (vtype := tv.get('type', '')) == 'object':
        basetype = 'Record'
        for k, v in tv.get('properties', {}).items():
            fields.append((k, scandef(f'{tn}.{k}', v, nt, jss, jssx), v))
        popts = f'({len(fields)})'
    elif vtype == 'array':
        if type(items := tv.get('items', None)) == dict:
            basetype = 'ArrayOf'
            fields.append((scandef(f'{tn}', items, nt, jss, jssx)))
            popts = f'({fields[0]})'
        elif type(items) == list:
            for n, v in enumerate(items):
                scandef(f'{tn}.{n}', v, nt, jss, jssx)
            print(f'- {tn}: ArrayX')
    elif vtype in {'string', 'integer', 'number', 'boolean'}:
        print(f'- {tn:80}: {vtype}')
        return vtype.capitalize()
    elif enum := tv.get('enum', []):
        basetype = 'Enumerated'
        for v in enum:
            fields.append(v)
        popts = f'({len(fields)})'
    elif cc := [c for c in ('anyOf', 'allOf', 'oneOf') if c in tv][0]:
        basetype = 'Choice'
        for n, v in enumerate(tv[cc]):
            fields.append(scandef(f'{tn}.{n}', v, nt, jss, jssx))
        popts = f'({cc})({len(fields)})'
    else:
        raise ValueError(f'- {tn}: Unexpected type: {vtype}: {tv}')

    if basetype:
        print(f'- {tn}: {basetype}{popts}')
        nt.append(td := make_jadn_type(tn, basetype, fields, tv, jss, jssx))
        return td[TypeName]


def make_jadn_type(tn: str, basetype: str, flist: list, tv: dict, jss: dict, jssx: dict):
    tnroot, tnpath = tn.split('.', maxsplit=1) if '.' in tn else (tn, '')
    typename = typedefname(tnroot, jss) + (f'.{tnpath}' if tnpath else '')
    topts = []
    fields = []
    tdesc = tv.get('description', '')
    if basetype == 'Record':
        req = tv.get('required', [])
        for n, f in enumerate(flist, start=1):
            k, v, fv = f
            fdesc = fv.get('description', '')
            fopts = ['[0'] if k not in req else []
            fields.append([n, k, v, fopts, fdesc])

    elif basetype == 'ArrayOf':
        topts = [f'{{{tv["minItems"]}'] if 'minItems' in tv else []
        topts.append(f'}}{tv["maxItems"]}') if 'maxItems' in tv else []
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

    else:
        raise ValueError(f'unsupported type {basetype}')

    return [typename, basetype, topts, tdesc, fields]


def define_jadn_type(tn: str, tv: dict, jss: dict, jssx: dict) -> list:
    """
    Replaced by make_jadn_type - delete when conversion finished
    """
    topts = []
    tdesc = tv.get('description', '')
    fields = []
    unions = {
        'anyOf': 'CO',
        'allOf': 'CA',
        'oneOf': 'CX'
    }
    if (jstype := tv.get('type', '')) == 'object':
        basetype = 'Record'
        req = tv.get('required', [])
        for n, (k, v) in enumerate(tv.get('properties', {}).items(), start=1):
            fopts = ['[0'] if k not in req else []
            fdesc = v.get('description', '')
            if v.get('type', '') == 'array':
                ftype = maketypename('', k, jss)
                idesc = jss['definitions'].get(jssx.get(v['items'].get('$ref', ''), ''), {}).get('description', '')
                fdesc = fdesc if fdesc else v['items'].get('description', idesc)
            elif v.get('type', '') == 'object':
                ftype = typedefname(tn, jss)
            elif t := jssx.get(v.get('$ref', ''), ''):
                rt = jss['definitions'][t].get('$ref', '')
                ftype = typedefname(rt if rt else t, jss)
                ft = jss['definitions'][t]
                fdesc = ft.get('description', '')
            elif v.get('anyOf', '') or v.get('allOf', ''):
                ftype = maketypename(tn, k, jss)
            else:
                ftype = typerefname(v, jss, jssx)
            fdef = [n, k, ftype, fopts, fdesc]
            if not ftype:
                raise ValueError(f'  empty field type {tn}${k}')
            fields.append(fdef)
    elif cc := [c for c in ('anyOf', 'allOf', 'oneOf') if c in tv]:
        td = tv[cc[0]]
        basetype = 'Choice'
        topts = [unions[cc[0]]]
        for n, v in enumerate(td, start=1):
            fd = typerefname(v, jss, jssx)
            ftype = fd if fd else maketypename(tn, str(n), jss)
            fdef = [n, f'c{n}', ftype, [], '']
            fields.append(fdef)
    elif td := tv.get('enum', ''):
        basetype = 'Enumerated'
        for n, v in enumerate(td, start=1):
            fields.append([n, v, ''])
    elif jstype == 'array':     # TODO: process individual items
        basetype = 'ArrayOf'
        topts = [f'{{{tv["minItems"]}'] if 'minItems' in tv else []
        topts.append(f'}}{tv["maxItems"]}') if 'maxItems' in tv else []
        ref = jss['definitions'].get(jssx.get(tv['items'].get('$ref', ''), ''), {})
        tr = typerefname(ref, jss, jssx)
        tr = tr if tr else typerefname(tv['items'], jss, jssx)
        tr = tr if tr else singular(tn)
        topts.append(f'*{tr}')
    elif jstype in ('string', 'integer', 'number', 'boolean'):
        if p := tv.get('pattern', ''):
            topts.append(f'%{p}')
        basetype = jstype.capitalize()
    else:
        return []

    return [typedefname(tn, jss), basetype, topts, tdesc, fields]


def convert_js_to_jadn(jsfile, outfile):
    """
    Create a JADN type from each definition in a Metaschema-generated JSON Schema
    """
    with open(jsfile, encoding='utf-8') as fp:
        jss = json.load(fp)
    assert jss['type'] == 'object', f'Unsupported JSON Schema format {jss["type"]}'
    jssx = {v.get('$id', k): k for k, v in jss['definitions'].items()}      # Index from $id to definition
    assert len(jssx) == len(jss['definitions']), f'$ids {len(jssx)} != defs {len(jss["definitions"])}'
    # types = {typedefname(k, jss): v for k, v in jss['definitions'].items()}      # Index from type name to definition
    # seen = set()
    # t = [typedefname(k, jss) for k in jss['definitions']]
    # dupes = [k for k in t if k in seen or seen.add(k)]
    # print(f'Duplicate type names: {dupes}')

    info = {'package': jss['$id'].rstrip('.json')}
    info.update({'comment': jss['$comment']} if '$comment' in jss else {})
    info.update({'exports': ['$Root']})
    info.update({'config': {
        '$MaxString': 1000,
        '$TypeName': '^[$A-Z][-.$A-Za-z0-9]{0,96}$',
        '$FieldName': '^[$a-z][-_$A-Za-z0-9]{0,63}$',
        '$NSID': '^([A-Za-z][-A-Za-z0-9]{0,31})?$'}})

    nt = []     # Walk nested type definition tree to build type list
    scandef('$Root', jss, nt, jss, jssx)
    for tn, tv in jss['definitions'].items():
        scandef(tn, tv, nt, jss, jssx)

    ntypes = []     # Prune identical type definitions
    for t in nt:
        if t not in ntypes:     # O(n^2) runtime because type definitions aren't hashable
            ntypes.append(t)    # Convert to immutable types if it becomes an issue

    jadn.dump(schema := {'info': info, 'types': ntypes}, outfile)
    print('\n'.join([f'{k:>15}: {v}' for k, v in jadn.analyze(jadn.check(schema)).items()]))


if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(SCHEMA_DIR):
        jsfile = os.path.join(SCHEMA_DIR, f)
        fn, fe = os.path.splitext(f)
        outfile = os.path.join(OUT_DIR, fn) + '.jadn'
        try:
            convert_js_to_jadn(jsfile, outfile)
        except (ValueError, IndexError) as e:
            print(f'### {f}: {e}')
            raise




