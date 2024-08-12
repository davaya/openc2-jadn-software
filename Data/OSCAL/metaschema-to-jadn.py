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


def e_typename(element: etree.Element, pathmap: dict) -> str:
    return 'SYS'.join(pathmap[element]).capitalize()


def e_attrs(e: etree.Element) -> dict:
    return {k: v for k, v in e.items()}


def e_text(e: etree.Element) -> str:
    return (e.text.strip() if e.text else '') + e.tail.strip()


def e_mtext(element: etree.Element) -> str:
    s = etree.tostring(element).decode()
    if m := re.match(r'^<(\w*)[^>]*>((.|\n)+)<\/\1>', s):
        return m.group(2).strip()
    return s


"""
def make_jadn_flag(element: etree.Element, types: list) -> None:
    tag = etree.QName(element.tag).localname
    attrs = {k: v for k, v in element.items()}
    txt = (element.text.strip() if element.text else '') + element.tail.strip()

    # Generate type definition

    type_name = attrs.pop('name').capitalize()
    fields = ((1, 'alias', attrs.pop('as-type').capitalize(), (), ''), )
    td = (type_name, 'Choice', ('CA', ), str(attrs), fields)
    types.append(td)
"""


def get_doc(element: etree.Element) -> dict:
    doc = {}
    for e in element:
        if not isinstance(e.tag, str):
            continue
        tag = etree.QName(e.tag).localname
        # assert {tag} & {'formal-name', 'description', 'root-name', 'remarks', 'example'}
        attrs = {k: v for k, v in e.items()}
        txt = e_text(e)
        if len(e) == 0:
            doc.update({tag: txt})
        else:
            doc.update({tag: e_mtext(e)})
    return doc


def make_jadn_type(element: etree.Element, pathmap: dict, types: list) -> None:
    """
    Generate JADN package and type definitions from Metaschema element tree

    Path is the Metaschema type name plus the generated sequence of field names for anonymous types
    Schema is the JADN package with package info and type definitions
    Uses root level namespace prefix list and element-to-pathname map to generate type names
    """
    tag = etree.QName(element.tag).localname
    attrs = {k: v for k, v in element.items()}
    txt = (element.text.strip() if element.text else '') + element.tail.strip()

    anon_types = []
    if tag == 'define-assembly':
        name = attrs.pop('name')
        base_type = 'Record'
        type_options = []
        type_desc = ''
        fields = []
        doc = get_doc(element)
        for e in element:
            if not isinstance(e.tag, str):
                continue
            f_tag = etree.QName(e.tag).localname
            f_attrs = {k: v for k, v in e.items()}
            f_txt = e_text(e)
            if {f_tag} & {'formal-name', 'description', 'root-name', 'remarks', 'example'}:
                pass
            elif {f_tag} & {'assembly', 'field', 'flag'}:
                tn = f_attrs.pop('ref')
            elif f_tag == 'define-assembly':
                fields.append((len(fields), 'define-assembly', 'Foo', (), ''))
            elif f_tag == 'define-field':
                fields.append((len(fields), 'define-field', 'Bar', (), ''))
            elif f_tag == 'define-flag':
                fopts = ('[1', ) if (req := f_attrs.pop('required', '')) == 'yes' else ()
                assert req == 'yes' or req == ''
                fields.append((len(fields) + 1, f_attrs.pop('name'), f_attrs.pop('as-type'), fopts, get_doc(e), ))
                assert len(f_attrs) == 0
            elif f_tag == 'model':
                pass
            elif f_tag == 'constraint':
                pass
            else:
                raise ValueError(f'unexpected element for field: "{f_tag}" ({len(element)}): {f_attrs} - "{f_txt}"')

        td = (e_typename(element, pathmap), base_type, tuple(type_options), type_desc, tuple(fields))
        anon_types.append(td)

    elif tag == 'define-field':
        pass
    elif tag == 'define-flag':
        pass
    else:
        raise ValueError(f'unexpected element for JADN type "{tag}" ({len(element)}): {attrs} - "{txt}"')

    types += anon_types

    """
    # Collect fields
    anon_types = []
    fields = []
    for e in element:
        if not isinstance(e.tag, str):
            continue
        f_tag = etree.QName(e.tag).localname
        f_attrs = {k: v for k, v in e.items()}
        f_txt = e_text(e)
        f_desc = {}
        if {f_tag} & {'formal-name', 'description', 'root-name'}:
            assert len(f_attrs) == 0
            t_desc.update({f_tag: f_txt})
        elif {f_tag} & {'remarks', 'example'}:
            assert len(f_attrs) == 0
            t_desc.update({f_tag: e_mtext(e)})
        elif {f_tag} & {'json-value-key', 'use-name'}:
            pass    # do what?
        else:
            assert f_txt == ''
            if {f_tag} & {'assembly', 'field', 'flag'}:
                assert f_attrs.get('ref')
            elif f_tag == 'define-assembly':
                anon_types.append(e)
            elif f_tag == 'define-field':
                anon_types.append(e)
            elif f_tag == 'define-flag':
                type_name = e_typename(f_attrs.pop('name'), pathmap)
                fields = ((1, 'alias', e_typename(f_attrs.pop('as-type'), pathmap), (), get_doc(e)),)
                td = (type_name, 'Choice', ('CA',), str(t_attrs), fields)
                types.append(td)
            else:
                assert len(f_attrs) == 0
                if {f_tag} & {'model', 'constraint'}:
                    pass
                else:
                    p = etree.QName(element.tag).localname
                    raise ValueError(f'unprocessed tag "{p}/{f_tag}" ({len(e)}) - {f_attrs} - {f_txt}')

    td = (e_typename(element, pathmap), base_type, tuple(type_options), type_desc, tuple(fields))
    types.append(td)

    for e in anon_types:
        make_jadn_type(e, pathmap, types)
    """
    """
    children = []
    for e in element:
        if isinstance(e.tag, str):
            tag = etree.QName(e.tag)
            fa = {k: v for k, v in e.items()}
            assert tag.localname not in fa
            txt = (e.text.strip() if e.text else '') + e.tail.strip()
            if len(e) == 0:
                if href := fa.pop('href', ''):
                    fa.update({tag.localname: href})
                    assert txt == ''
                else:
                    fa.update({tag.localname: txt})
                    txt = ''
            elif {tag.localname} & {'description', 'remarks'}:
                fa.update({tag.localname: get_text(e)})
            elif {tag.localname, } & {'enum', 'allowed-values'}:
                # txt = get_text(e)
                pass
            else:
                assert txt == ''
                if tag.localname == 'define-flag':
                    fa = {'name': fa['as-type']}
                elif {tag.localname} & {'assembly', 'field', 'flag'}:
                    if 'ref' in fa:
                        rn = fa.pop('ref')
                        fa.update({rn: rn.capitalize()})
                    children.append(e)
                elif {tag.localname} & {
                        'model', 'constraint', 'example',
                        'choice', 'is-unique'}:
                    path = path + (tag.localname,)
                    fa.update({'name': tag.localname})
                    children.append(e)
                elif name := fa.pop('name', ''):
                    assert {tag.localname} & {'define-assembly', 'define-field'}
                    fa.update({tag.localname: name})
                    base_name = name.capitalize() if etree.QName(element).localname == 'METASCHEMA' else name
                    children.append(e)
                else:
                    raise ValueError(f'unprocessed tag {tag.localname} - {fa}')
            fields.append((fa, txt))
    """


def get_props(element: etree.Element) -> dict:
    props = {}
    imports = []
    for e in element:
        if not isinstance(e.tag, str):
            continue
        tag = etree.QName(e.tag).localname
        attrs = {k: v for k, v in e.items()}
        txt = e_text(e)
        if {tag} & {'formal-name', 'description', 'root-name'}:
            assert len(attrs) == 0
            props.update({tag: txt})
        elif {tag} & {'remarks', 'example'}:
            assert len(attrs) == 0
            props.update({tag: e_mtext(e)})
        elif {tag} & {'json-value-key', 'use-name'}:
            pass
        else:
            assert txt == ''
            if {tag} & {'assembly', 'field', 'flag'}:
                assert attrs.get('ref')
            elif {tag} & {'define-assembly', 'define-field', 'define-flag'}:
                pass
            elif tag == 'import':
                assert len(n := attrs['href'].split('_')) > 1
                imports.append(n[0] + '-' + n[1])   # TODO: read namespace from imported file
            else:
                assert len(attrs) == 0
                if {tag} & {'model', 'constraint'}:
                    pass
                else:
                    p = etree.QName(element.tag).localname
                    raise ValueError(f'unprocessed tag "{p}/{tag}" ({len(e)}) - {attrs} - {txt}')

    props.update({'$imports': imports})
    return props


def make_jadn(element: etree.Element, pathmap: dict) -> dict:

    fld = {}
    imports = []
    root_types = []
    for e in element:
        if not isinstance(e.tag, str):
            continue
        tag = etree.QName(e.tag).localname
        if {tag} & {'short-name', 'schema-name', 'schema-version', 'namespace', 'json-base-uri'}:
            fld.update({tag: e_text(e)})
        elif tag == 'remarks':
            fld.update({tag: e_mtext(e)})
        elif tag == 'import':
            assert len(n := e.get('href').split('_')) > 1
            imports.append(n[0] + '-' + n[1])  # TODO: read namespace from imported file
        elif {tag} & {'define-assembly', 'define-field', 'define-flag'}:
            root_types.append(e)
        else:
            raise ValueError(f'unrecognized root element "{tag}" ({len(e)}): {e_attrs(e)}, "{e_text(e)}"')

    pkg_ns = f'{fld["json-base-uri"]}/{fld["schema-version"]}/'
    info = {     # TODO: pop, omit empty, and check unprocessed
        'package': pkg_ns + fld['short-name'],
        'title': fld['schema-name'],
        'description': fld['remarks'],
        'namespaces': [(PREFIXES[k], pkg_ns + k) for k in imports],
        'roots': [e.get('name').capitalize() for e in root_types]
    }

    types = []
    for e in root_types:
        make_jadn_type(e, pathmap, types)

    return {'info': info, 'types': types}


def flatten_elements(element: etree.Element, path: tuple, ep_list: list) -> None:
    """
    Generate flattened path names for anonymous elements
    """
    path = () if etree.QName(element.tag).localname == 'METASCHEMA'\
        else path + (element.get('name', ''), )
    ep_list.append((element, path))

    for e in element:
        if isinstance(e.tag, str):
            tag = etree.QName(e.tag).localname
            if {tag} & {'define-assembly', 'define-field', 'model'} or (tag == 'define-flag' and len(path) == 0):
                flatten_elements(e, path, ep_list)


if __name__ == '__main__':
    os.makedirs(OUT_DIR_PACKAGE, exist_ok=True)
    for f in os.listdir(SCHEMA_DIR):
        metaschema_file = os.path.join(SCHEMA_DIR, f)
        print(f'\n=== {metaschema_file}')
        tree = etree.parse(metaschema_file)

        path = ()
        ep_list = []
        flatten_elements(tree.getroot(), path, ep_list)
        ep_map = {k[0]: k[1] for k in ep_list}
        assert len(ep_map) == len(ep_list)

        schema = make_jadn(tree.getroot(), ep_map)
        pass

        fname, fext = os.path.splitext(f)


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