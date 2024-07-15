import jadn
import json
import os
from collections import defaultdict
from jadn.definitions import (TypeName, BaseType, TypeOptions, TypeDesc, Fields, ItemID, ItemValue, ItemDesc,
                              FieldID, FieldName, FieldType, FieldOptions, FieldDesc, has_fields)
from typing import Union

SPLIT = True    # Split set of combined schemas into packages, otherwise process each combined schema
SCHEMA_DIR = os.path.join('oscal-1.1.2', 'json', 'schema')
OUT_DIR = '../../Out'
DEBUG = False
SYS = '.'   # Separator character used in generated type names
D = [(f'${n}' if DEBUG else '') for n in range(10)]


def typedefname(jsdef: str) -> str:
    """
    Infer type name from a JSON Schema definition
    """
    assert isinstance(jsdef, str), f'Not a type definition name: {jsdef}'
    ns = prefix['']     # use default
    if d := jss['definitions'].get(jsdef, ''):
        if (ref := d.get('$id', d.get('$ref', None))):
            if len(x := ref.split('_')) == 3:
                ns = prefix[x[1]]
                name = {x[2].capitalize()}
            elif ref.startswith ('#/definitions'):    # primitive, add common namespace
                name = ref.removeprefix("#/definitions")
            elif ref == '#json-schema-directive':     # ignore, we don't use it
                pass
            else:
                print(f'unexpected typedefname {jsdef} {ref}')
        if ':' in jsdef:  # qualified definition name
            name = maketypename('', jsdef.split(':', maxsplit=1)[1]) + D[1]
        if ref := d.get('$ref', ''):
            name = ref.removeprefix('#/definitions/')
    else:
        name = jsdef
    return f'{ns}:{name}'     # Exact type name or none


def typerefname(jsref: dict) -> str:
    """
    Infer a type name from a JSON Schema property reference
    """
    if (t := jsref.get('type', '')) in ('string', 'integer', 'number', 'boolean', 'binary'):
        return t.capitalize() + D[4]    # Built-in type
    if ref := jsref.get('$ref', ''):
        if len(x := ref.split('_')) == 3:
            ns = prefix[x[1]]
            return f'{ns}:{x[2].capitalize()}'
        td = jssx.get(ref, ref)
        if ':' in td:
            return maketypename('', td.split(':', maxsplit=1)[1]) + D[6]  # Extract type name from $id
    return ''


def maketypename(tn: str, name: str) -> str:
    """
    Convert a type and property name to type name
    """
    tn = typedefname(tn)
    name = f'{tn}${name}' if tn else name.capitalize()
    return name + '1' if jadn.definitions.is_builtin(name) else name


def is_defined(items: dict) -> bool:
    return '$ref' in items or items.get('type', '') in {'string', 'integer', 'number', 'boolean'}


def add_type(id: str, iid: str, type: tuple, type_list: list[tuple]) -> None:
    if SYS in type[TypeName]:
        id = id if id else iid.get('$iid', None)
    if (id, type) not in tuple(type_list):
        type_list.append((id, type))
    else:
        pass


def freeze_type(t: list[list]) -> tuple[tuple]:    # Freeze a JADN type to make hashable
    def ff(f: list[list]) -> tuple:    # Freeze field
        if len(f) == 3:
            return tuple([f[ItemID], f[ItemValue], f[ItemDesc]])
        return tuple([f[FieldID], f[FieldName], f[FieldType], tuple(f[FieldOptions]), f[FieldDesc]])
    return tuple([t[TypeName], t[BaseType], tuple(t[TypeOptions]), t[TypeDesc], tuple([ff(k) for k in t[Fields]])])


def unfreeze_type(t: Union[list, tuple]) -> list[list]:  # Unfreeze a JADN type
    def uf(f: Union[list, tuple]) -> list[list]:    # Unfreeze field
        if len(f) == 3:
            return [f[ItemID], f[ItemValue], f[ItemDesc]]
        return [f[FieldID], f[FieldName], f[FieldType], list(f[FieldOptions]), f[FieldDesc]]
    return [t[TypeName], t[BaseType], list(t[TypeOptions]), t[TypeDesc], [uf(k) for k in t[Fields]]]


def scandef(type_name: str, tv: dict, type_list: list):
    global seen, rseen, prefix
    """
    Process nested type definitions, add to type list
    """
    basetype = ''
    fields = []
    global idlist, rflist
    idlist.add(id := tv.get('$id', None))
    rflist.add(ref := tv.get('$ref', None))
    iid = tv.get('$iid', None)
    iid = {'$iid': id} if id else {'$iid': iid} if iid else {}  # Create "inherited $id" for generated types
    if ref:
        if len(x := ref.split('_')) == 3:
            if x[1] not in prefix:
                prefix.update({x[1]: f'n{len(prefix) + 1}'})
        dn = typedefname(rn := jssx.get(ref, ref))
        if ref not in rseen:
            tva = jss['definitions'][dn if dn in jss['definitions'] else rn]
            scandef(dn, tva, type_list)
            rseen.update((ref,))

        # Construct "Alias" type using degenerate untagged union
        if type_name not in seen and SYS not in type_name and ':' not in type_name and type_name != 'json-schema-directive':
            print(f'  alias {type_name} -> {dn}')
            seen.update({type_name: tv})
            tdesc = tv.get('description', tv.get('title', ''))
            add_type(id, iid, (type_name, 'Choice', ('CA', ), tdesc, ((1, 'alias', dn, (), ''), )), type_list)
        return dn

    elif (vtype := tv.get('type', '')) in {'string', 'integer', 'number', 'boolean'}:
        basetype = vtype.capitalize()

    elif vtype == 'object':
        if type_name not in seen:
            seen.update({type_name: tv})
            basetype = 'Record'
            for k, v in tv.get('properties', {}).items():
                fields.append((k, scandef(f'{type_name}.{k}', v | iid, type_list), v))

    elif vtype == 'array':
        if isinstance(items := tv.get('items', {}), dict):
            fields.append((scandef(f'{type_name}', items | iid, type_list)))
            return fields[0]
        elif isinstance(items, list):
            for n, v in enumerate(items):
                scandef(f'{type_name}.{n}', v | iid, type_list)
            print(f'- {type_name}: ArrayX')

    elif enum := tv.get('enum', []):
        basetype = 'Enumerated'
        for v in enum:
            fields.append(v)

    elif cc := [c for c in ('anyOf', 'allOf', 'oneOf') if c in tv][0]:
        basetype = 'Choice'
        for n, v in enumerate(tv[cc]):
            fields.append(scandef(f'{type_name}.{n}', v | iid, type_list))

    else:
        raise ValueError(f'- {type_name}: Unexpected type: {vtype}: {tv}')

    if basetype:
        td = make_jadn_type(type_name, basetype, fields, tv)
        if SYS in type_name:   # if generated type and built-in with no options, optimize it out.
            if td[BaseType] in {'String', 'Integer', 'Number', 'Boolean'} and len(td[TypeOptions]) == 0:
                return td[BaseType]
        add_type(id, iid, td, type_list)
        return td[TypeName]


def make_jadn_type(type_name: str, basetype: str, flist: list, tv: dict):
    tnroot, tnpath = type_name.split(SYS, maxsplit=1) if SYS in type_name else (type_name, '')
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
            if fv.get('type', '') == 'array':
                fopts.append(f']{fv.get("maxItems", 0)}')
            fields.append((n, k, v, fopts, fdesc))

    elif basetype == 'ArrayOf':
        topts = [f'{{{tv["minItems"]}'] if 'minItems' in tv else []
        topts.append(f'}}{tv["maxItems"]}') if 'maxItems' in tv else '}0'
        topts.append(f'*{flist[0]}')

    elif basetype == 'Enumerated':
        for n, f in enumerate(flist, start=1):
            fields.append((n, f, ''))

    elif basetype == 'Choice':
        cc = [c for c in ('anyOf', 'allOf', 'oneOf') if c in tv][0]
        topts = [{
            'anyOf': 'CO',
            'allOf': 'CA',
            'oneOf': 'CX'
        }[cc]]
        for n, v in enumerate(flist, start=1):
            fields.append((n, f'c{n}', v, [], ''))

    elif basetype == 'String':  # process string opts
        if x := tv.get('format', ''):
            topts.append(f'/{x}')
        if x := tv.get('pattern', ''):
            topts.append(f'%{x}')
    elif basetype == 'Integer':
        pass # process integer opts
    elif basetype == 'Number':
        pass # process number opts
    elif basetype == 'Boolean':
        pass # done - no opts on boolean
    elif basetype:
        raise ValueError(f'unsupported type {basetype}')

    td = (typename, basetype, tuple(topts), tdesc, tuple(fields))
    return td


def convert_js_to_jadn(jsfile: str, outfile: str, type_list: list[tuple]) -> None:
    global jss, jssx, seen, rseen, prefix
    """
    Create a JADN type from each definition in a Metaschema-generated JSON Schema
    """

    with open(jsfile, encoding='utf-8') as fp:
        jss = json.load(fp)
    assert jss['type'] == 'object', f'Unsupported JSON Schema format {jss["type"]}'
    jssx = {v.get('$id', k): k for k, v in jss['definitions'].items()}      # Index from $id to definition
    assert len(jssx) == len(jss['definitions']), f'$ids {len(jssx)} != defs {len(jss["definitions"])}'
    for k, v in jss['definitions'].items():
        if (id := v.get('$id', None)) and len(x := id.split('_')) == 3:
            if x[1] not in prefix:
                prefix.update({x[1]: f'n{len(prefix) + 1 :02d}'})
        elif id == '#json-schema-directive':    # ignore, not used
            pass
        else:  # primitives don't have $id
            assert id is None
            assert '$ref' not in v

    seen = {}   # Index of $refs to jss definitions
    rseen = set()   # Set of $refs already processed

    info = {'package': jss['$id'].rstrip('.json')}
    for k in 'title', 'description', 'comment':
        if v := jss.get('$' + k, ''):
            info.update({k: v})
    exports = []
    for v in jss.get('oneOf', []):
        exports += [typerefname(v['properties'][k]) for k in v.get('required', '')]
    info.update({'exports': exports if exports else [typerefname(jss['properties'][k]) for k in jss.get('required', '')]})
    info.update({'config': {
        '$MaxString': 1000,
        '$TypeName': '^[$A-Z][-.$A-Za-z0-9]{0,96}$',
        '$FieldName': '^[$a-z][-_$A-Za-z0-9]{0,63}$',
        '$NSID': '^([A-Za-z][-A-Za-z0-9]{0,31})?$'}})

    # Walk nested type definition tree to build type list
    scandef('$Root', jss, type_list)
    for k, v in jss['definitions'].items():
        scandef(k, v, type_list)
    ntx = {t[1][TypeName]: t for t in type_list}
    deps, refs = jadn.build_deps({'types': [t[1] for t in type_list]})
    roots = set(deps) - refs
    print(f'{len(roots)} detected roots: {roots}')

    # Remove self-referencing dependencies
    for k, v in deps.items():
        if k in v:
            print(f'  self-loop: {k} ({len(v)}):{v}')
            deps[k].remove(k)

    # Sort type definitions with designated root first, then collections in dependency order, then primitives
    nt1, nt2 = [], []
    start = k if len(k := info.get('exports', [])) else [ntx.get('$Root')[TypeName]]
    tlist = jadn.topo_sort(deps, start)
    for k in tlist:
        if tdef := ntx.pop(k):
            if tdef[BaseType] == 'Enumerated':
                nt1.append(tdef)
            elif has_fields(tdef[BaseType]):
                nt1.append(tdef)
            else:
                nt2.append(tdef)
    nt3 = [tdef for tdef in ntx.values()]   # include unreferenced types at end
    print(f'{len(ntx)} unreferenced types: { {k for k in ntx} }')

    if not SPLIT:
        schema = {'info': info, 'types': nt1 + nt2 + nt3}
        jadn.dump(schema, outfile)
        try:
            print('\n'.join([f'{k:>15}: {v}' for k, v in jadn.analyze(jadn.check(schema)).items()]))
        except ValueError as e:
            print(f'### {f}: {e}')


if __name__ == '__main__':
    global jss, jssx, seen, rseen, prefix

    prefix = {'': 'n01'}    # default
    type_list_all = []
    idlist, rflist = set(), set()
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(SCHEMA_DIR):
        jsfile = os.path.join(SCHEMA_DIR, f)
        fn, fe = os.path.splitext(f)
        outfile = os.path.join(OUT_DIR, fn) + '.jadn'
        try:
            print(f'\n=== {jsfile}')
            type_list = []
            convert_js_to_jadn(jsfile, outfile, type_list)
            newt = [t for t in type_list if t not in type_list_all]
            type_list_all += newt
        except (ValueError, IndexError) as e:
            print(f'### Error: {f}: {e}')
            raise

    print(f'\nJSON schema')
    print(f'  {len(idlist):3} ids: {idlist}')
    print(f'  {len(rflist):3} refs: {rflist}')
    idrn, idrp = defaultdict(list), defaultdict(list)
    print('Non-$ids')
    for idr in idlist | rflist:
        if idr and len(x := idr.split('_')) == 3:
            idrn[x[1]].append(x[2])
            idrp[x[2]].append(x[1])
        else:
            print(f'  {x}')

    print('Namespaces:')
    for k, v in idrn.items():
        print(f'  {k:30} {len(v):2} {v}')
    print('Qualified Types:')
    for k, v in idrp.items():
        if len(v) > 1:
            print(f'  {k:30} {v}')

    if SPLIT:
        roots = {}
        ss = defaultdict(dict)
        for k, v in type_list_all:
            if k:
                if len(x := k.split('_')) == 3:
                    ss[x[1]][f'{prefix[x[1]]}:{v[TypeName]}'] = v
                    common = x[1]
                else:
                    assert len(v) == 5 and v[TypeName] == '$Root'
                    pkg = k.rsplit('/', maxsplit=1)
                    t = f"{pkg[1].removesuffix('-schema.json')}"
                    roots[t] = {'package': k.removesuffix('-schema.json'), 'types': v}
                    print(f'  Schema namespace for {k}: {v}')
            else:
                ss['common'][v[TypeName]] = v
                print(f'  No namespace for {k}: {v}')

        k = common.split('-', maxsplit=1)[0] + '-common'
        ss[k] = ss.pop('common')
        for ns in ss:
            if ns in roots:
                info = {'package': roots[ns]['package']}  # id
                info.update({'exports': [roots[ns]['types'][Fields][1][FieldType]]})  # Designated root
            else:
                info = {'package': f'{pkg[0]}/{ns}'}
                # info.update({'exports': []})    # TODO: list DAG roots

            info.update({'config': {
                '$MaxString': 1000,
                '$TypeName': '^[$A-Z][-.$A-Za-z0-9]{0,96}$',
                '$FieldName': '^[$a-z][-_$A-Za-z0-9]{0,63}$',
            }})

            outfile = os.path.join(OUT_DIR, ns) + '.jadn'
            schema = {'info': info, 'types': [unfreeze_type(v) for v in ss[ns].values()]}
            sschema = jadn.sort_types(schema)
            assert len(schema['types']) == len(sschema['types'])
            jadn.dump(sschema, outfile)
            print(f'\n=== {ns}')
            try:
                print('\n'.join([f'{k:>15}: {v}' for k, v in jadn.analyze(jadn.check(schema)).items()]))
            except ValueError as e:
                print(f'### {f}: {e}')


"""
    info = {'package': jss['$id'].rstrip('.json')}
    for k in 'title', 'description', 'comment':
        if v := jss.get('$' + k, ''):
            info.update({k: v})
    exports = []
    for v in jss.get('oneOf', []):
        exports += [typerefname(v['properties'][k]) for k in v.get('required', '')]
    info.update({'exports': exports if exports else [typerefname(jss['properties'][k]) for k in jss.get('required', '')]})
    info.update({'config': {
        '$MaxString': 1000,
        '$TypeName': '^[$A-Z][-.$A-Za-z0-9]{0,96}$',
        '$FieldName': '^[$a-z][-_$A-Za-z0-9]{0,63}$',
        '$NSID': '^([A-Za-z][-A-Za-z0-9]{0,31})?$'}})
"""