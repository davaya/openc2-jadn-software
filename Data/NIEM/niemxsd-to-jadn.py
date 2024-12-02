import jadn
from lxml import etree
import os
import re
import typing

from collections import defaultdict
from jadn.definitions import (TypeName, BaseType, TypeOptions, TypeDesc, Fields, ItemID, ItemValue, ItemDesc,
                              FieldID, FieldName, FieldType, FieldOptions, FieldDesc, OPTION_ID)
from typing import Union

NIEM_XSD_DIR = 'NIEM5.2'
OUT_DIR = '../../Out'
SYS = '.'       # Separator character used in generated type names


def make_jadn_info(element: etree.Element, attr: dict, fields: list, info: dict) -> None:
    """
    Generate package info from root element
    """
    assert etree.QName(element).localname == 'METASCHEMA'
    assert attr == {'abstract': 'yes'}
    ir = {}
    imports = []
    roots = []
    for (fd, txt) in fields:
        assert txt == ''
        for k, v in fd.items():
            if k in ('schema-name', 'schema-version', 'short-name', 'namespace', 'json-base-uri', 'remarks'):
                ir.update({k: v})
            elif k in 'import':
                assert len(n := v.split('_')) > 2
                imports.append(n[0] + '-' + n[1])
            elif k in 'define-assembly':
                roots.append(v)
            elif k in ('define-field', 'define-flag'):
                pass
            else:
                print(f'# Undefined root item {k}: {v}')
    pkg_ns = f'{ir["json-base-uri"]}/{ir["schema-version"]}/'
    info.update({
        'package': pkg_ns + ir['short-name'],
        'title': ir['schema-name'],
        'description': ir['remarks'],
        'namespaces': [(k, pkg_ns + k) for k in imports],
        'roots': [k.capitalize() for k in roots]
    })


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


def get_text(element: etree.Element) -> str:
    s = etree.tostring(element).decode()
    if m := re.match(r'^<(\w*)[^>]*>((.|\n)+)<\/\1>', s):
        return m.group(2).strip()
    return s


def make_ms_schema(element: etree.Element, base_name: str, path: list, schema: dict) -> None:
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
    if etree.QName(element).localname == 'METASCHEMA':
        make_jadn_info(element, at, fields, schema['info'])
    else:
        make_jadn_type(base_name, path, element, at, fields, schema['types'])
    for e in children:
        make_ms_schema(e, base_name, path + [etree.QName(e.tag).localname], schema)
    pass


class JADNPackage:
    def __init__(self):
        self.meta = {}
        self.types = []


def make_jadn(element: etree.Element) -> JADNPackage:
    pkg = JADNPackage()

    def walk(element: etree.Element, level: int) -> None:
        for n, e in enumerate(element, start=1):
            tag = etree.QName(e.tag).localname
            attrs = {k: v for k, v in e.items()}
            print(f'{n:>{2*level}} {len(e)} {tag} {attrs}')
            walk(e, level+1)

    walk(element, 0)
    return pkg


if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in os.listdir(NIEM_XSD_DIR):
        fn, fe = os.path.splitext(fname := os.path.join(NIEM_XSD_DIR, f))
        print(f'\n=== {fname}')
        tree = etree.parse(fname)
        root = tree.getroot()
        print(root.tag, len(root))
        root_ns = etree.QName(root.tag).namespace
        pkg = make_jadn(root)
