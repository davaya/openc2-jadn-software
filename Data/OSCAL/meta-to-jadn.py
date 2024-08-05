import jadn
from lxml import etree
import os
import re
from collections import defaultdict
from jadn.definitions import (TypeName, BaseType, TypeOptions, TypeDesc, Fields, ItemID, ItemValue, ItemDesc,
                              FieldID, FieldName, FieldType, FieldOptions, FieldDesc, OPTION_ID)
from typing import Union

SCHEMA_DIR = os.path.join('oscal-1.1.2', 'metaschema')
OUT_DIR_PACKAGE = '../../Out/Package'
SYS = '.'       # Separator character used in generated type names

PREFIXES = {    # Pre-define short prefixes for OSCAL prefix names (last component of namespace)
    'oscal-catalog': 'cat',
    'oscal-profile': 'prf',
    'oscal-component-definition': 'cmp',
    'oscal-ssp': 'ssp',
    'oscal-ap': 'ap',
    'oscal-ar': 'ar',
    'oscal-poam': 'poam',
    'oscal-metadata': 'm',
    'oscal-control-common': 'cc',
    'oscal-implementation-common': 'ic',
    'oscal-assessment-common': 'ac',
    '': 'c',
}
BLANK_PREFIX_NAME = 'oscal-common'

CONFIG = {
    '$MaxString': 1000,     # TODO: Add JADN config item $MaxDesc
    '$Sys': '.',            # TODO: Change JADN default $SYS
    '$TypeName': '^[$A-Z][-.$A-Za-z0-9]{0,96}$',
    '$FieldName': '^[$a-z][-_$A-Za-z0-9]{0,63}$',
}

"""

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


def un_namespace_names(names: list, ns: str) -> None:
    for n, na in enumerate(names):
        names[n] = na.removeprefix(ns + ':')


def un_namespace_type(t: list, ns: str) -> None:
    t[TypeName] = t[TypeName].removeprefix(ns + ':')
    for f in t[Fields]:
        f[FieldType] = f[FieldType].removeprefix(ns + ':')
        if len(f) > FieldOptions:
            for n, fo in enumerate(f[FieldOptions]):    # TODO: check for double option
                f[FieldOptions][n] = fo[0] + fo[1:].removeprefix(ns + ':')


def sort_types(schema: dict) -> dict:
    deps, refs = jadn.build_deps(schema)
    # Remove self-referencing dependencies
    for k, v in deps.items():
        if k in v:
            print(f'    self-loop: {k}')
            deps[k].remove(k)
    ndeps = {}
    for k, v in deps.items():
        ndeps[k] = [i for i in v if ':' not in i]
    tx = {k[TypeName]: k for k in schema['types']}
    tlist = [tx[t] for t in jadn.topo_sort(ndeps, schema['info']['roots']) if t in tx]
    return {'info': schema['info'], 'types': tlist}


def make_info(ns_prefix: str, ns_ref: str, prefixes: dict, all_types: set) -> dict:
    ns_base = ns_ref.rsplit('/', maxsplit=1)[0] + '/'
    types = [k for k in all_types if k[TypeName].startswith(prefixes[ns_prefix] + ':')]
    deps, refs = jadn.build_deps({'types': types})
    info = {
        'package': ns_base + ns_prefix,
        'roots': sorted([k.removeprefix(prefixes[ns_prefix] + ':') for k in set(deps) - refs]),
    }
    px = {v: k for k, v in prefixes.items()}
    if ns_list := {k.split(':', maxsplit=1)[0] for k in refs - set(deps)}:
        info.update({'namespaces': [[k, ns_base + px[k]] for k in ns_list]})
    info.update({'config': CONFIG})
    return info


class JADN:
    """ """
    Build a JADN schema from JSON Schema definitions
    """ """
    def __init__(self, jss: dict, prefixes: dict):
        self.jss = jss              # JSON-Schema schema
        jd = jss['definitions']     # Index from $id to definition
        self.jsx = {v.get('$id', k): jd[k] for k, v in jd.items()}
        self.ids = set()            # all $id values seen in this schema
        self.refs = set()           # all $ref values seen in this schema (internal ids + external)
        self.aliases = set()        # all types that pass $id to $ref
        self.type_names = set()     # JADN type names
        self.info = {}              # JADN package info
        self.types = []             # JADN types
        self.prefixes = prefixes    # JADN prefix list, supplied or generated when seen
        self.pf_used = set()        # Prefixes seen in this schema
        self.ns_uri = {}            # id to URI
        self.namespace = ''         # JSON Schema namespace of this schema

        self.info = {'package': jss['$id'].removesuffix('-schema.json')}
        self.info.update({k.removeprefix('$'): jss[k] for k in
            ('title', 'description', '$comment', 'version', 'copyright', 'license') if k in jss})

        if 'properties' in jss:     # Single root
            self.info.update({'roots': (root := jss['required'][0])})
            assert len(x := jss['properties'][root]['$ref'].split('_')) == 3
            self.namespace = x[1]
        elif 'oneOf' in jss:        # Multiple roots
            roots = []
            for k in jss['oneOf']:
                roots.append(root := k['required'][0])
            self.info.update({'roots': roots})

    def set_prefixes(self, prefixes: dict[str, str]):
        self.prefixes = prefixes

    def get_info(self) -> dict:
        """ """
        Build package info and return JADN schema
        """ """
        info = self.info
        p = info['package'].rsplit('/', maxsplit=1)[0] + '/'
        info.update({'namespaces':
            [[v, p + (k if k else BLANK_PREFIX_NAME)] for k, v in self.prefixes.items() if k in self.pf_used]})
        roots = [k['properties'][k['required'][0]] for k in jss.get('oneOf', []) + [jss] if 'required' in k]
        info.update({'roots': [self._make_tn('', k, [], '') for k in roots]})
        self.add_info(info)
        return info

    def get_types(self) -> list:
        return [unfreeze_type(k) for k in self.types]

    def add_info(self, info: dict) -> None:
        """ """
        Add checks later.
        {
            "package": {"type": "#/definitions/Namespace"},
            "version": {"type": "string"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "comment": {"type":  "string"},
            "copyright": {"type": "string"},
            "license": {"type": "string"},
            "namespaces": {"$ref": "#/definitions/Namespaces"},
            "roots": {"$ref": "#/definitions/Roots"},
            "config": {"$ref": "#/definitions/Config"}
        }
        """ """
        for k, v in info.items():   # Build JADN package information
            if k in {'package', 'version', 'title', 'description', 'comment', 'copyright', 'license',
                     'namespaces', 'roots', 'config', 'type_docs'}:
                self.info.update({k: v})
            else:
                raise ValueError(f'Unrecognized package info: {k}: {v}')

    def _make_tn(self, jsn: str, jsd: dict, path: list[str], cur_type: str) -> str:
        """ """
        Create JADN type names from Metaschema-specific JSON Schema $id's

        jsn: string name default when no $id is available
        jsd: JSON Schema definition
        path: fieldname path from #definition for anonymous types
        cur_type: current #definition for anonymous types
        """ """
        jtn = jsd.get('$id', jsd.get('$ref', cur_type))
        jtn = '#/definitions/Json-schema-directive' if jtn == '#json-schema-directive' else jtn     # fix special case
        ps = SYS + SYS.join(path) if path else ''   # convert path array to string
        if len(x := jtn.split('_')) == 3:   # Metaschema-style qualified names: '#assembly_oscal-ap_assessment-plan'
            self.prefixes.update({x[1]: f'n{len(self.prefixes) + 1 :02d}'} if x[1] not in self.prefixes else {})
            self.pf_used |= {x[1], }
            return f'{self.prefixes[x[1]]}:{x[2].capitalize()}{ps}'
        elif jtn.startswith('#/definitions/') or (jtn := jsn):
            if jss.get(tn := jtn.removeprefix('#/definitions/'), '') != tn:
                self.pf_used |= {'', }
                return f'{self.prefixes[""]}:{tn + ps}'  # Primitives
            raise ValueError(f'unexpected definition {jtn}')
        return jtn     # return root URI unchanged

    def add_type(self, jsn: str, jsd: dict, path: list[str], cur_type: str) -> str:
        jst = jsd.get('type', None)
        tid = jsd.get('$id', None)
        ref = jsd.get('$ref', None)
        self.ids |= {tid, } if tid else set()
        self.refs |= {ref, } if ref else set()
        if (k := jsd.get('$id', jsd.get('$ref', cur_type))) != cur_type:
            cur_type = k
            path = []

        type_name = self._make_tn(jsn, jsd, path, cur_type)
        if type_name in self.type_names:
            return type_name
        base_type = ''      # JADN BaseType
        type_opts = []      # JADN TypeOptions
        type_desc = jsd.get('description', jsd.get('title', ''))
        fields = []         # JADN Fields

        if ref:
            if tid:
                rn = self._make_tn(jsn, {}, [], ref)     # force ref instead of id
                # Generate alias type using single-field untagged union
                td = (type_name, 'Choice', tuple(['CA']), type_desc, ((1, 'alias', rn, tuple(), ''), ))
                self.types.append(td)
                self.type_names |= {type_name}
                self.aliases |= {tid, }
            return type_name

        if jst == 'object':
            base_type = 'Record'
            req = jsd.get('required', [])
            for n, (k, v) in enumerate(jsd.get('properties', {}).items(), start=1):
                f_type = self.add_type(jsn, v, path + [k], cur_type)
                f_opts = [OPTION_ID['minc'] + '0'] if k not in req else []
                f_desc = v.get('description', '')
                if v.get('type', '') == 'array':
                    f_opts.append(f']{v.get("maxItems", 0)}')
                fields.append((n, k, f_type, tuple(f_opts), f_desc))

        elif jst == 'array':
            if isinstance(items := jsd.get('items', {}), dict):
                base_type = 'ArrayOf'
                if x := jsd.get('minItems', 0):
                    type_opts.append(OPTION_ID['minv'] + str(x))
                if x := jsd.get('maxItems', 0):
                    type_opts.append(OPTION_ID['maxv'] + str(x))
                if '$ref' in items:
                    i_type = self._make_tn(jsn, items, [], cur_type)
                    type_name = i_type
                    base_type = ''
                else:
                    i_type = self.add_type(jsn, items, path, cur_type)
                    if i_type == type_name:
                        base_type = ''
                type_opts.append(OPTION_ID['vtype'] + i_type)

            elif isinstance(items, list):
                base_type = 'Array'
                for n, v in enumerate(items):
                    pass    # TODO: process Array like Record
                    # flist.append((str(n), v, scandef(v, path + [f'n{n}'])))

        elif jse := jsd.get('enum', None):
            base_type = 'Enumerated'
            for n, v in enumerate(jse, start=1):
                fields.append((n, v, ''))

        elif cc := [c for c in ('anyOf', 'allOf', 'oneOf') if c in jsd]:
            type_opts = [{'anyOf': 'CO', 'allOf': 'CA', 'oneOf': 'CX'}[cc[0]]]
            base_type = 'Choice'
            for n, v in enumerate(jsd[cc[0]], start=1):
                f_type = self.add_type(jsn, v, path + [str(n)], cur_type)
                f_opts = []
                f_desc = v.get('description', '')
                fields.append((n, f'c{n}', f_type, tuple(f_opts), f_desc))

        elif jst in {'string', 'integer', 'number', 'boolean'}:
            base_type = str(jst).capitalize()  # There is no "binary" type in JSON Schema
            if base_type == 'String':  # process string opts
                if x := jsd.get('format', ''):
                    type_opts.append(f'{OPTION_ID["format"]}{x}')
                if x := jsd.get('pattern', ''):
                    type_opts.append(f'{OPTION_ID["pattern"]}{x}')
            elif base_type == 'Integer':
                pass # process integer opts
            elif base_type == 'Number':
                pass # process number opts
            elif base_type == 'Boolean':
                pass # done - no opts on boolean
            elif base_type:
                raise ValueError(f'unsupported type {base_type}')
            if path:    # Don't create JADN built-in types
                return base_type

        if base_type:
            td = (type_name, base_type, tuple(type_opts), type_desc, tuple(fields))
            self.types.append(td)
        return type_name
    """

FIELDS = {
    'ALL': {
        'short-name', 'remarks', 'define-assembly', 'define-field', 'define-flag'
    },
    'METASCHEMA': {
        'schema-name', 'schema-version', 'namespace',
        'json-base-uri', 'import'
    }
}
"""
'code'
'enum'
'group-as'
'has-cardinality'
'key-field'
'matches'
"""


def prettyprint(element, **kwargs):
    xml = etree.tostring(element, pretty_print=True, **kwargs)
    print(xml.decode(), end='')


def make_jadn_type(name: str, path: list, tag: str, attr: dict, fields: list) -> list:
    pass
    return [name, path, tag, attr, fields]


def get_text(element: etree.Element) -> str:
    s = etree.tostring(element).decode()
    if m := re.match(r'^<(\w*)[^>]*>((.|\n)+)<\/\1>', s):
        return m.group(2).strip()
    return s


def make_ms_typedef(element: etree.Element, base_name: str, path: list, types: list) -> None:
    at = {k: v for k, v in element.items()}
    fields = []
    children = []
    for e in element:
        if isinstance(e.tag, str):
            assert (t := etree.QName(e.tag)).namespace == root_ns
            fa = {k: v for k, v in e.items()}
            txt = (e.text.strip() if e.text else '') + e.tail.strip()
            if len(e) == 0:
                if 'href' in fa:
                    fa = {t.localname: fa['href']}
                    assert txt == ''
                else:
                    fa = {t.localname: txt}
                    txt = ''
            else:
                if 'name' in fa:
                    assert txt == ''
                    base_name = fa['name']
                    fa = {t.localname: fa['name']}
                    children.append(e)
                elif t.localname in (
                        'model', 'constraint', 'assembly', 'field', 'flag',
                        'allowed-values', 'enum', 'choice', 'is-unique'
                    ):
                    if t.localname == 'enum':
                        txt = get_text(e)
                    else:
                        assert txt == ''
                        assert path
                        fa = base_name + SYS + SYS.join(path)
                        children.append(e)
                else:
                    assert t.localname in ('description', 'remarks')
                    fa = {t.localname: get_text(e)}
                    txt = ''
            fields.append((fa, txt))
    jadn_type = make_jadn_type(base_name, path, element.tag, at, fields)
    types.append(jadn_type)
    for e in children:
        make_ms_typedef(e, base_name, path + [etree.QName(e.tag).localname], types)
    pass


if __name__ == '__main__':
    os.makedirs(OUT_DIR_PACKAGE, exist_ok=True)
    sp = defaultdict(lambda: defaultdict(list))     # Package schemas
    for f in os.listdir(SCHEMA_DIR):
        metaschema_file = os.path.join(SCHEMA_DIR, f)
        fn, fe = os.path.splitext(f)
        print(f'\n=== {metaschema_file}')
        tree = etree.parse(metaschema_file)
        root = tree.getroot()
        print(root.tag, len(root))
        root_ns = etree.QName(root.tag).namespace
        path, types = [], []
        make_ms_typedef(root, '', path, types)
        pass

"""
        try:
            # Convert JSON Schema to JADN schema
            jv = JADN(jss, PREFIXES)  # JADN schema instance
            for jsn, jsd in jss['definitions'].items():
                jv.add_type(jsn, jsd, [], '')  # Add rest of the definition and anonymous types
        except (ValueError, IndexError) as e:
            print(f'### Error: {f}: {e}')
            raise

        all_types |= {t for t in jv.types}
        ns = jv.info['package'].rsplit('/', maxsplit=1)[1]
        jv.add_info({'config': CONFIG})
        sc[ns]['pf_used'] = jv.pf_used
        sc[ns]['ids'] = jv.ids
        sc[ns]['refs'] = jv.refs
        sc[ns]['types'] = jv.types                  # keep frozen types
        sc[ns]['info'] = (info := jv.get_info())    # build current info
        print(f'JSON schema: {info.get("title", "")} {info.get("comment", "")}')
        print(f'{len(jv.ids):2} ids, {len(jv.aliases):2} aliases, {len(jv.refs):2} refs,',
              f'{len(jv.pf_used):2} namespaces, {len(jv.types):3} types')

        schema = {'info': info, 'types': jv.get_types()}
        deps, refs = jadn.build_deps(schema)
        unref = (set(deps) - refs) or ''
        undef = (refs - set(deps)) or ''
        print(f'undefined: {len(undef)} {undef}')
        print(f'unreferenced: {len(unref)} {unref}')

        outfile = os.path.join(OUT_DIR_COMBINED, fn) + '.jadn'
        jadn.dump(schema, outfile)

        px = {v: (k if k else BLANK_PREFIX_NAME) for k, v in jv.prefixes.items()}
        for t in jv.types:
            ns, tn = t[TypeName].split(':', maxsplit=1)
            (sp[px[ns]][tn]).append(t)

    ################
    # Split combined schemas into package schemas
    ################

    # List anonymous types that could be elevated to named level

    print('\nAnonymous Types:')
    for ns, tlist in sp.items():
        if ns in sc:
            tnames = defaultdict(list)
            for td in tlist:
                tn = td.split(SYS, maxsplit=1)
                if len(tn) > 1 and SYS not in tn[1]:
                    tnames[tn[1]].append(td)
            for k, v in tnames.items():
                if len(v) == 1:
                    print(f'  May replace {ns}:{v[0]} with {ns}:{k.capitalize()}')
                else:
                    print(f'  Can\'t replace {ns}:{v} with {ns}:{k.capitalize()}')

    print('\nNamespaces:')
    for k, v in jv.prefixes.items():
        print(f'{v:>6}: http:.../{k if k else BLANK_PREFIX_NAME}')

    print('\nAliases:')
    for ns, tlist in sp.items():
        for k, td in tlist.items():
            if td[0][BaseType] == 'Choice' and (f := td[0][Fields][0])[FieldName] == 'alias':
                print(f'  alias {td[0][TypeName]} -> {f[FieldType]}')

    print('\nNon-qualified Name Collisions:')
    nqn = defaultdict(list)     # Find non-qualified name collisions
    for ns, tlist in sp.items():
        for tn, td in tlist.items():
            nqn[tn].append({tn: td})
            if (nt := len(set(td))) > 1:    # check for type definition conflicts (should not happen)
                if tn != '$Root':
                    raise ValueError(f'{ns}:{tn:30} - {nt} defs: {set(td)}')
    for tn, td in nqn.items():
        if len(td) > 1:
            print(f'  {[k[tn][0][TypeName] for k in td]}')

    print('\nSchemas:')
    pf = {(k if k else BLANK_PREFIX_NAME): v for k, v in jv.prefixes.items()}
    for ns, tlist in sp.items():
        if ns in sc:
            info = sc[ns]['info']
            print(f'  Package: {info["package"]}')
        else:
            info = make_info(ns, sc[list(sc)[0]]['info']['package'], pf, all_types)
            print(f'  Package: {info["package"]}  (derived)')

        types = [unfreeze_type(v[0]) for k, v in tlist.items()]
        un_namespace_names(info.get('roots', []), pf[ns])
        for t in types:
            un_namespace_type(t, pf[ns])
        if t := [i for i in info.get('namespaces', []) if i[0] != pf[ns]]:
            info['namespaces'] = t
        outfile = os.path.join(OUT_DIR_PACKAGE, ns) + '.jadn'
        jadn.dump(sort_types({'info': info, 'types': types}), outfile)
    """