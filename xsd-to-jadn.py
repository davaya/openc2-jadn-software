import argparse
import jadn
import os
from collections import defaultdict
from jadn.definitions import TypeName, CoreType, TypeOptions, Fields, FieldType
from lxml import etree
from typing import List

# SCHEMA_DIR = os.path.join('Data', 'NIEM', 'niem5.2')
OUTPUT_DIR = 'Out'
SYS = '.'   # Character used in system-generated TypeNames


def typedefname(jsdef: str, jss: dict) -> str:
    """
    Infer type name from a JSON Schema definition
    """
    assert isinstance(jsdef, str), f'Not a type definition name: {jsdef}'
    if d := jss.get('definitions', jss.get(jsdef, '')):
        if ':' in jsdef:  # qualified definition name
            return maketypename('', jsdef.split(':', maxsplit=1)[1], jss)
        if ref := d.get('$ref', ''):
            return ref.removeprefix('#/definitions/')
    return jsdef.removeprefix('#/definitions/')     # Exact type name or none


def typerefname(jsref: dict, jss: dict, jssx: dict) -> str:
    """
    Infer a type name from a JSON Schema property reference
    """
    if (t := jsref.get('type', '')) in ('string', 'integer', 'number', 'boolean'):
        return t.capitalize()    # Built-in type
    if ref := jsref.get('$ref', ''):
        td = jssx.get(ref, ref)
        if td.startswith('#/definitions/'):  # Exact type name
            return td.removeprefix('#/definitions/')
        if ':' in td:
            return maketypename('', td.split(':', maxsplit=1)[1], jss)  # Extract type name from $id
        if td2 := jss.get('definitions', {}).get(td, {}):
            return typerefname(td2, jss)
    return ''


def singular(name: str) -> str:
    """
    Guess a singular type name for the anonymous items in a plural ArrayOf type
    """
    """
    if name.endswith('ies'):
        return name[:-3] + 'y'
    elif name.endswith('es'):
        n = -2 if name[-4:-3] == 's' else -1
        return name[:n]
    elif name.endswith('s'):
        return name[:-1]
    """
    return name + '-item'


def maketypename(tn: str, name: str, jss) -> str:
    """
    Convert a type and property name to type name
    """
    tn = typedefname(tn, jss)
    name = f'{tn}.{name}' if tn else name.capitalize()      # $Sys = "."
    return name + '1' if jadn.definitions.is_builtin(name) else name


def scandef(tn: str, tv: dict, nt: list, jss: dict, jssx: dict):
    """
    Process anonymous type definitions, generate pathname, add to list nt
    """

    if not (td := define_jadn_type(tn, tv, jss, jssx)):
        return
    nt.append(td)
    if tv.get('type', '') == 'object':
        for k, v in tv.get('properties', {}).items():
            if v.get('$ref', '') or v.get('type', '') in ('string', 'number', 'integer', 'boolean'):     # Not nested
                pass
            elif v.get('type', '') == 'object':
                scandef(maketypename(tn, k, jss), v, nt, jss, jssx)
            elif v.get('type', '') == 'array':
                scandef(maketypename('', k, jss), v, nt, jss, jssx)
                if len(vt := v.get('items', {})) != 1 or vt.get('type', '') not in ('string', 'number', 'integer', 'boolean'):
                    scandef(singular(maketypename('', k, jss)), v['items'], nt, jss, jssx)
            elif v.get('anyOf', '') or v.get('allOf', ''):
                scandef(maketypename(tn, k, jss), v, nt, jss, jssx)
            elif typerefname(v, jss, jssx):
                print('  nested property type:', f'{td[TypeName]}.{k}', v)

        if not tn:
            print(f'  nested type: "{tv.get("title", "")}"')
    elif (tc := tv.get('anyOf', '')) or (tc := tv.get('allOf', '')):
        for n, v in enumerate(tc, start=1):
            scandef(maketypename(tn, n, jss), v, nt, jss, jssx)
    pass


def define_jadn_type(tn: str, tv: dict, jss: dict, jssx: dict) -> list:
    topts = []
    tdesc = tv.get('description', '')
    fields = []
    if (jstype := tv.get('type', '')) == 'object':
        coretype = 'Record'
        req = tv.get('required', [])
        for n, (k, v) in enumerate(tv.get('properties', {}).items(), start=1):
            fopts = ['[0'] if k not in req else []
            fdesc = v.get('description', '')
            if v.get('type', '') == 'array':
                ftype = maketypename('', k, jss)
                idesc = jss.get('definitions', {}).get(jssx.get(v['items'].get('$ref', ''), ''), {}).get('description', '')
                fdesc = fdesc if fdesc else v['items'].get('description', idesc)
            elif v.get('type', '') == 'object':
                ftype = maketypename(tn, k, jss)
            elif ref := v.get('$ref', ''):
                if ref == '#':  # TODO: replace this monkey hack with proper reference logic
                    ftype = tn
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
                raise ValueError(f'  empty field type {tn}.{k}')
            fields.append(fdef)
    elif (td := tv.get('anyOf', '')) or (td := tv.get('allOf', '')):
        coretype = 'Choice'
        # topts = ['<', '∪'] if 'allOf' in tv else ['<']    # TODO: update Choice in JADN library
        # topts = ['∪'] if 'allOf' in tv else []
        for n, v in enumerate(td, start=1):
            fd = typerefname(v, jss)
            ftype = fd if fd else maketypename(tn, n, jss)
            fdef = [n, f'c{n}', ftype, [], '']
            fields.append(fdef)
    elif td := tv.get('enum', ''):
        coretype = 'Enumerated'
        for n, v in enumerate(td, start=1):
            fields.append([n, v, ''])
    elif jstype == 'array':     # TODO: process individual items
        coretype = 'ArrayOf'
        topts = [f'{{{tv["minItems"]}'] if 'minItems' in tv else []
        topts.append(f'}}{tv["maxItems"]}') if 'maxItems' in tv else []
        ref = jss.get('definitions', {}).get(jssx.get(tv['items'].get('$ref', ''), ''), {})
        tr = typerefname(ref, jss, jssx)
        tr = tr if tr else typerefname(tv['items'], jss, jssx)
        tr = tr if tr else singular(tn)
        topts.append(f'*{tr}')
    elif jstype in ('string', 'integer', 'number', 'boolean'):
        if p := tv.get('pattern', ''):
            topts.append(f'%{p}')
        coretype = jstype.capitalize()
    else:
        return []

    return [typedefname(tn, jss), coretype, topts, tdesc, fields]


def make_jadn_type(name: str, path: list[str], element: etree.Element, attr: dict, fields: list, types: list) -> None:
    """
    Generate type definitions from child elements
    """
    type_name = element.tag.capitalize() + SYS + SYS.join(path)
    base_type = ''
    type_options = []
    type_desc =  ''
    fields = []
    types.append((type_name, base_type, type_options, type_desc, fields))


class JADNPackage:
    def __init__(self, meta: dict = None):
        self.meta = {}
        self.types = []

        if meta:
            self.meta = meta    # TODO: validate each entry

        def pkg(self):          # Return JADN Schema Package
            return {'meta': self.meta, 'types': self.types}






        def get_annotation(pkg):
            pass
        def get_attribute(pkg):
            pass
        def get_element(pkg):
            pass
        dispatch = {
            'annotation': get_annotation,
            'attribute': get_attribute,
            'element': get_element,
        }

        for n, element in enumerate(root, start=1):
            tag = etree.QName(element.tag).localname
            attrs = {k: v for k, v in element.items()}
            dispatch[tag](self)

            if tag == 'annotation':
                for e in element:
                    etag = etree.QName(e.tag).localname
                    {   'documentation': get_documentation(e),
                        'appinfo': get_appinfo(e)}[etag]


def get_documentation(self, e: etree.Element) -> str:
    assert len(e) == 0
    assert len(e.attrib) == 0
    assert len(e.items()) == 0
    assert len(e.tail.strip()) == 0
    return e.text.strip()

def get_appinfo(self, e) -> None:
    return


def xsd_to_jadn(root: etree.Element) -> JADNPackage:
    pkg = JADNPackage()
    tag = etree.QName(root.tag).localname
    attrs = {k: v for k, v in root.items()}

    meta = {}
    meta['package'] = attrs['targetNamespace']
    meta['version'] = attrs['version']
    meta['roots'] = [tag.capitalize()]
    meta['namespaces'] = [(k, v) for k, v in root.nsmap.items()]

    return pkg.pkg

"""
def make_jadn(root: etree.Element) -> dict:

    def walk(path: List[etree.Element]) -> None:
        for n, e in enumerate(path[-1], start=1):
            ecount['.'.join([etree.QName(v).localname for v in path])] += 1
            tag = etree.QName(e.tag)
            attrs = {k: v for k, v in e.items()}
            val = f'{e.text.strip() if e.text else ""}'
            print(f'{n:>{2*len(path)}} {len(e)} {tag} {attrs} {val}')
            walk(path + [e])

    pkg = JADNPackage()
    ecount = defaultdict(int)
    walk([root])
    for n, (k, v) in enumerate(ecount.items(), start=1):
        print(f'{n:=4} {k} = {v}')
    return pkg.schema()
"""

def main(schema_dir: str, output_dir: str) -> None:
    """
    Create a JADN type from each definition in a JSON Schema
    """
    print(f'Installed JADN version: {jadn.__version__}\n')
    os.makedirs(output_dir, exist_ok=True)

    for dirpath, dirnames, filenames in os.walk(schema_dir):
        for f in filenames:
            fn, ext = os.path.splitext(f)
            if ext in ('.xsd', ):
                schema_path = os.path.join(dirpath, f)
                tree = etree.parse(schema_path)
                schema = xsd_to_jadn(tree.getroot())
                jadn.dump(schema.pkg, os.path.join(OUTPUT_DIR, f'{fn}.jadn'))
                print('\n'.join([f'{k:>15}: {v}' for k, v in jadn.analyze(jadn.check(schema.pkg)).items()]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('schema_dir')
    parser.add_argument('output_dir', nargs='?', default=OUTPUT_DIR)
    args = parser.parse_args()
    print(args)
    main(args.schema_dir, args.output_dir)

"""
    from lxml import etree

    schema_file = "path/to/your/schema.xsd"
    schema_doc = etree.parse(schema_file)
    schema = etree.XMLSchema(schema_doc)
    
    xml_file = "path/to/your/document.xml"
    xml_doc = etree.parse(xml_file)

    try:
        schema.assertValid(xml_doc)
        print("XML is valid according to the schema.")
    except etree.DocumentInvalid as e:
        print("XML validation error:", 
"""