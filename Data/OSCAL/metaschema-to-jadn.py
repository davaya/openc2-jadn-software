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

BLANK_PREFIX_NAME = 'http://csrc.nist.gov/ns/oscal/1.0/1.1.2/oscal-common'
PREFIXES = {    # Define short prefixes for OSCAL namespaces
    'http://csrc.nist.gov/ns/oscal/1.0/1.1.2/oscal-catalog': 'cat',                 # Control Layer
    'http://csrc.nist.gov/ns/oscal/1.0/1.1.2/oscal-profile': 'prf',                 # Control Layer
    'http://csrc.nist.gov/ns/oscal/1.0/1.1.2/oscal-component-definition': 'cmp',    # Implementation Layer
    'http://csrc.nist.gov/ns/oscal/1.0/1.1.2/oscal-ssp': 'ssp',                     # Implementation Layer
    'http://csrc.nist.gov/ns/oscal/1.0/1.1.2/oscal-ap': 'ap',                       # Assessment Layer
    'http://csrc.nist.gov/ns/oscal/1.0/1.1.2/oscal-ar': 'ar',                       # Assessment Layer
    'http://csrc.nist.gov/ns/oscal/1.0/1.1.2/oscal-poam': 'poam',                   # Assessment Layer
    'http://csrc.nist.gov/ns/oscal/1.0/1.1.2/oscal-metadata': 'm',
    'http://csrc.nist.gov/ns/oscal/1.0/1.0.4/oscal-control-common': 'cc',           # 1.0.4, really?
    'http://csrc.nist.gov/ns/oscal/1.0/1.1.2/oscal-implementation-common': 'ic',
    'http://csrc.nist.gov/ns/oscal/1.0/1.1.2/oscal-assessment-common': 'ac',
    BLANK_PREFIX_NAME: 'c',                                                         # Primitives
}

CONFIG = {
    '$MaxString': 1000,     # TODO: Add JADN config item $MaxDesc
    '$Sys': '.',            # TODO: Change JADN default $SYS
    '$TypeName': '^[$A-Z][-.$A-Za-z0-9]{0,96}$',
    '$FieldName': '^[$a-z][-_$A-Za-z0-9]{0,63}$',
}

FLAG_TYPE = {
    'base64': ('Binary', ['/b64'], 'Binary data encoded using the Base 64 encoding algorithm as defined by RFC4648.'),
    'boolean': ('Boolean', [], 'A binary value that is either: true or false.'),
    'date': ('String', ["%^(((2000|2400|2800|(19|2[0-9](0[48]|[2468][048]|[13579][26])))-02-29)|(((19|2[0-9])[0-9]{2})-02-(0[1-9]|1[0-9]|2[0-8]))|(((19|2[0-9])[0-9]{2})-(0[13578]|10|12)-(0[1-9]|[12][0-9]|3[01]))|(((19|2[0-9])[0-9]{2})-(0[469]|11)-(0[1-9]|[12][0-9]|30)))(Z|(-((0[0-9]|1[0-2]):00|0[39]:30)|\\+((0[0-9]|1[0-4]):00|(0[34569]|10):30|(0[58]|12):45)))?$"], 'A string representing a 24-hour period with an optional timezone.'),
    'dateTime-with-timezone': ('String', ["/date-time", "%^(((2000|2400|2800|(19|2[0-9](0[48]|[2468][048]|[13579][26])))-02-29)|(((19|2[0-9])[0-9]{2})-02-(0[1-9]|1[0-9]|2[0-8]))|(((19|2[0-9])[0-9]{2})-(0[13578]|10|12)-(0[1-9]|[12][0-9]|3[01]))|(((19|2[0-9])[0-9]{2})-(0[469]|11)-(0[1-9]|[12][0-9]|30)))T(2[0-3]|[01][0-9]):([0-5][0-9]):([0-5][0-9])(\\.[0-9]+)?(Z|(-((0[0-9]|1[0-2]):00|0[39]:30)|\\+((0[0-9]|1[0-4]):00|(0[34569]|10):30|(0[58]|12):45)))$"], 'A string representing a point in time with a required timezone.'),
    'integer': ('Integer', [], 'A whole number value'),
    'nonNegativeInteger': ('Integer', ['{0'], 'An integer value that is equal to or greater than 0.'),
    'positiveInteger': ('Integer', ['{1'], 'An integer value that is greater than 0.'),
    'string': ('String', ['%^\S(.*\S)?$'], 'A non-empty string with leading and trailing whitespace disallowed. Whitespace is: U+9, U+10, U+32 or [ \n\t]+'),
    'token': ('String', ['%^(\p{L}|_)(\p{L}|\p{N}|[.\-_])*$'], 'A non-colonized name as defined by XML Schema Part 2: Datatypes Second Edition. https://www.w3.org/TR/xmlschema11-2/#NCName.'),
    'uuid': ('Binary', ['/uuid'], 'A type 4 ("random" or "pseudorandom") or type 5 UUID per RFC 4122.'),
    'uri': ('String', ['/uri', '%^[a-zA-Z][a-zA-Z0-9+\-.]+:.+$'], 'A universal resource identifier (URI) formatted according to RFC3986.'),
    'uri-reference': ('String', ['/uri-reference'], 'A URI Reference, either a URI or a relative-reference, formatted according to section 4.1 of RFC3986.'),
}

GEN_ATTRS = {'$doc', '$group-as', '$constraint'}

ALLOWED_ATTRS = {
    'define-assembly': {'name', 'min-occurs', 'max-occurs', 'deprecated'},
    'define-field': {'name', 'as-type', 'min-occurs', 'max-occurs', 'in-xml', 'scope', 'deprecated'},
    'define-flag': {'name', 'as-type', 'required', 'default', 'deprecated'},
    'assembly': {'ref', 'min-occurs', 'max-occurs'},
    'field': {'ref', 'min-occurs', 'max-occurs', 'in-xml'},
    'flag': {'ref', 'required'}
}


def make_typeref(path: list) -> str:
    if info['package'] in (msf := type_defs.get(path[0], [])):
        return SYS.join(path).capitalize()
    if len(msf) > 1:
        p = {k for k in msf} & {k for k in info['namespaces']}
        assert len(p) <= 1
    ns = BLANK_PREFIX_NAME if len(msf) == 0 else msf[0] if len(msf) == 1 else p.pop()
    return PREFIXES[ns] + ':' + SYS.join(path).capitalize()


def make_typename(path: list) -> str:
    return SYS.join(path).capitalize()


def e_attrs(e: etree.Element) -> dict:
    return {k: v for k, v in e.items()}


def e_text(element: etree.Element, text_type: str='line') -> str:
    if isinstance(element.tag, str) and (tag := etree.QName(element.tag).localname):
        if text_type == 'line':   # fix ad-hoc logic to use text_type (line vs. multiline markup)
            s = (t.strip() if (t := element.text) else '') + element.tail.strip()
        # elif len(element) == 1:
            # s = (element.text + (t if (t := element[0].text) else '') + element[0].tail).strip()
        else:
            s = etree.tostring(element).decode()
            if m := re.match(r'^<(\w*)[^>]*>((.|\n)+)<\/\1>', s):
                return m.group(2).strip()
        return s
    return ''


def get_documentation(element: etree.Element) -> dict:
    doc = {}
    for e in element:
        if isinstance(e.tag, str):
            tag = etree.QName(e.tag).localname
            if {tag} & {'formal-name', 'description', 'root-name', 'remarks', 'example'}:
                assert len(e.items()) == 0  # No attributes
                doc.update({tag: e_text(e) if len(e) == 0 else e_text(e, 'multiline')})
    return doc


def get_group_name(element: etree.Element) -> str:
    if etree.QName(element.tag).localname == 'group-as':
        return element.get('name')
    for e in element:
        if isinstance(e.tag, str) and etree.QName(e.tag).localname == 'group-as':
            return e.get('name')
    return ''


def get_constraint(element: etree.Element) -> dict:
    if etree.QName(element.tag).localname == 'constraint':
        for e in element:
            if not isinstance(e.tag, str):
                continue
            if (ctag := etree.QName(e.tag).localname) == 'is-unique':
                pass
            elif ctag == 'allowed-values':
                pass  # generate Enumerated items
            elif ctag == 'has-cardinality':
                pass
            elif ctag == 'matches':
                pass
            elif ctag == 'index':
                pass
            elif ctag == 'expect':
                pass
            elif ctag == 'index-has-key':
                pass
            else:
                raise ValueError(f'unknown constraint {ctag}')

def make_jadn_type(element: etree.Element, path: list, types: list) -> None:
    """
    Generate JADN package and type definitions from Metaschema element tree

    Path is the Metaschema type name plus the generated sequence of field names for anonymous types
    Schema is the JADN package with package info and type definitions
    Uses root level namespace prefix list and element-to-pathname map to generate type names
    """
    def field_opts(f: dict) -> tuple:
        if req := f.pop('required', ''):
            minc = {'no': '0', 'yes': '1'}[req]
        else:
            minc = f.pop('min-occurs', '0')
        maxc = f.pop('max-occurs', '1')
        fopts = [f'{jadn.definitions.OPTION_ID["minc"]}{minc}']
        fopts += [f'{jadn.definitions.OPTION_ID["maxc"]}{maxc}'] if maxc != 'unbounded' else []
        if default := f.pop('default', ''):
            fopts += [f'{jadn.definitions.OPTION_ID["default"]}{default}']
        ignore = f.pop('in-xml', f.pop('in-json', ''))
        assert set(f) - GEN_ATTRS - {'deprecated'} == set()
        return tuple(fopts)

    def get_fields(element: etree.Element) -> list:
        flds = []
        for e in element:
            if not isinstance(e.tag, str):
                continue
            f_tag = etree.QName(e.tag).localname
            f_attrs = {k: v for k, v in e.items()}
            f_attrs.update({'$group-as': v} if (v := get_group_name(e)) else {})
            f_attrs.update({'$constraint': v} if (v := get_constraint(e)) else {})
            doc = get_documentation(e)
            f_txt = doc.get('description', doc.get('formal-name', ''))
            f_attrs.update({'$doc': doc} if doc else {})
            if f_tag == 'model':
                assert f_attrs == {}
                assert f_txt == ''
                flds += get_fields(e)
            elif {f_tag} & {'formal-name', 'use-name', 'root-name', 'description', 'remarks', 'example'}:
                assert set(f_attrs) - GEN_ATTRS == set()
                type_info.update({f_tag: f_txt})
            elif {f_tag} & {'define-assembly', 'define-field', 'define-flag', 'assembly', 'field', 'flag'}:
                assert set(f_attrs) - ALLOWED_ATTRS[f_tag] - GEN_ATTRS == set()
                flds.append((e, f_attrs))
            elif {f_tag} & {'group-as', 'constraint'}:
                pass    # not a field - already processed in lookahead
            elif f_tag == 'choice':
                assert f_attrs == {}
                assert f_txt == ''
                assert etree.QName(element).localname == 'model'
                if len(element) == 1:   # Single choice in a model is a type
                    flds.append((e, f_attrs))
                else:   # Not a field or type. Insert "choice" field selection option into containing assembly
                    pass
            elif f_tag == 'prop':
                assert len(e) == 0
                assert f_txt == ''
                assert set(f_attrs) == {'name', 'value'}
            elif {f_tag} & {'json-value-key'}:
                pass    # ignore - external threat ID
            else:
                raise ValueError(f'unexpected element for field: "{f_tag}" ({len(element)}): {f_attrs} - "{f_txt}"')
        return flds

    tag = etree.QName(element.tag).localname
    attrs = {k: v for k, v in element.items()}
    doc = get_documentation(element)
    txt = doc.get('description', doc.get('formal-name', ''))
    anon_types = []
    type_info = {}
    if tag == 'define-assembly':
        # Collect info for fields
        flds = get_fields(element)

        # Build JADN type
        if len(flds) == 1 and etree.QName((e := flds[0][0])).localname == 'choice':
            base_type = 'Choice'    # if model has 1 element, it is a Choice type, not a Record with field constraints
            flds = get_fields(e)
        else:
            base_type = 'Record'
        type_options = []
        type_desc = type_info.get('description', type_info.get('formal_name', ''))
        fields = []
        for n, (e, att) in enumerate(flds, start=1):
            etag = etree.QName(e).localname
            if fname := att.pop('name', ''):
                p = [at] if (at := att.pop('as-type', '')) else path + [fname]
                ftype = make_typeref(p)
                anon_types.append((e, p))
            elif fname := att.pop('ref', ''):
                ftype = make_typeref([att.pop('as-type', fname)])
            elif etag == 'choice':
                anon_types.append((e, path))
                break
            else:
                raise ValueError(f'unexpected field type {tag}/{n}: {etag} ({len(e)} - {att})')
            fname = att.pop('$group-as', fname)
            d = att.get('$doc', {})
            fdoc = d.get('description', d.get('formal-name', ''))
            fields.append((n, fname, ftype, field_opts(att), fdoc))
        # doc = get_documentation(element)
        td = (make_typename(path), base_type, tuple(type_options), type_desc, tuple(fields))
        types.append(td)

    elif tag == 'choice':
        type_info = {}
        flds = get_fields(element)

        # Build JADN type
        base_type = 'Choice'
        type_options = []
        type_desc = type_info.get('description', type_info.get('formal_name', ''))
        fields = []
        for n, (e, att) in enumerate(flds, start=1):
            etag = etree.QName(e).localname
            if etag == 'define-assembly':
                fname = att.pop('name')
                anon_types.append((e, path + [fname]))
                ftype = make_typename(path + [fname])
            else:
                assert etag == 'assembly'
                fname = att.pop('ref')
                ftype = fname
            fields.append((n, fname, ftype, field_opts(att), ''))
        td = (make_typename(path), base_type, tuple(type_options), type_desc, tuple(fields))
        types.append(td)

    elif tag == 'define-field':
        assert set(attrs) - ALLOWED_ATTRS[tag] - GEN_ATTRS == set()
        # assert get_fields(element) == []    # How can a field (threat-id) contain flags?

    elif tag == 'define-flag':
        type_name = make_typeref([flag_type := attrs.pop('as-type', 'string')])
        base_type, type_options, type_desc = FLAG_TYPE[flag_type]
        # assert len(element) == 0
        type_info = {}
        assert get_fields(element) == []
        assert set(attrs) - ALLOWED_ATTRS[tag] - {'scope'} == set()
        td = (type_name, base_type, tuple(type_options), type_desc, ())
        if td not in types:
            types.append(td)

    elif {tag} & {'assembly', 'field', 'flag'}:
        pass

    else:
        raise ValueError(f'unexpected element for JADN type "{tag}" ({len(element)}): {attrs} - "{txt}"')

    for e, p in anon_types:
        make_jadn_type(e, p, types)


def get_info(element: etree.Element) -> dict:
    fld = {}
    ns_files = []
    root_elements = []
    for e in element:
        if isinstance(e.tag, str) and (tag := etree.QName(e.tag).localname):
            if {tag} & {'short-name', 'schema-name', 'schema-version', 'namespace', 'json-base-uri', 'remarks'}:
                text_type = 'multiline' if tag == 'remarks' else 'line'
                fld.update({tag: e_text(e, text_type)})
            elif tag == 'import':
                ns_files.append(e.get('href'))
            elif {tag} & {'define-assembly', 'define-field', 'define-flag'}:
                root_elements.append(e)
            else:
                raise ValueError(f'unrecognized root element "{tag}" ({len(e)}): {e_attrs(e)}, "{e_text(e)}"')

    pkg_ns = f'{fld["namespace"]}/{fld["schema-version"]}/'
    info = {
        'package': pkg_ns + fld['short-name'],
        '$ns_files': ns_files,
        '$root_elements': root_elements
    }
    info.update({'title': v} if (v := fld.get('schema-name', '')) else {})
    info.update({'description': v} if (v := fld.get('remarks', '')) else {})
    return info


if __name__ == '__main__':
    os.makedirs(OUT_DIR_PACKAGE, exist_ok=True)
    pkg_info = {}
    type_defs = defaultdict(list)
    for ms_file in os.listdir(SCHEMA_DIR):
        ms_path = os.path.join(SCHEMA_DIR, ms_file)
        print(f'\n=== {ms_path}')
        tree = etree.parse(ms_path)
        pkg_info[ms_file] = info = get_info(tree.getroot())
        for t in info['$root_elements']:
            type_defs[t.get('name')].append(info['package'])

    for t, f in type_defs.items():
        if len(f) > 1:
            print(f'{t:>24}: {[v.split("/")[-1:][0] for v in f]}')

    file_pkg = {f: pkg_info[f]['package'] for f in pkg_info}
    for ms_file in os.listdir(SCHEMA_DIR):
        ms_path = os.path.join(SCHEMA_DIR, ms_file)
        tree = etree.parse(ms_path)
        info = get_info(tree.getroot())

        info.update({'namespaces': [(PREFIXES[file_pkg[k]], file_pkg[k]) for k in info.pop('$ns_files')]})

        types = []
        for e in info.pop('$root_elements'):
            make_jadn_type(e, [e.get('name')], types)

        schema = {'info': info, 'types': types}

        # Write schema
        # fname, fext = os.path.splitext(f)
