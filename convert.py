import argparse
import os
from jadn import load, dump, check, analyze, topts_s2d, ftopts_s2d, opts_d2s
from jadn.convert import jidl_load, jidl_dump, markdown_dump, diagram_dump
from definitions import TypeName, CoreType, TypeOptions, TypeDesc, Fields
from definitions import ItemID, ItemValue, ItemDesc
from definitions import FieldID, FieldName, FieldType, FieldOptions, FieldDesc
from lxml import etree as ET

OUTPUT_DIR = 'Out'


def xasd_dumps(schema: dict):
    xasd = '<?xml version="1.0" encoding="UTF-8"?>\n<Schema>\n'
    if meta := schema.get('meta'):
        xasd += '  <Metadata\n'
        xasd += '\n'.join([f'{4*" "}{k}="{v}"' for k, v in meta.items() if isinstance(v, str)]) + '>\n'
        for k, v in meta.items():
            if k == 'roots':
                xasd += f'{4 * " "}<{k.capitalize()}>\n'
                for v in meta[k]:
                    xasd += f'{6 * " "}<TypeName>{v}</TypeName>\n'
                xasd += f'{4 * " "}</{k.capitalize()}>\n'
            elif k == 'namespaces':
                xasd += f'{4 * " "}<{k.capitalize()}>\n'
                for v in meta[k]:
                    xasd += f'{6 * " "}<PrefixNs prefix="{v[0]}">{v[1]}</PrefixNs>\n'
                xasd += f'{4 * " "}</{k.capitalize()}>\n'
            elif k == 'config':
                xasd += f'{4 * " "}<{k.capitalize()}>\n'
                for k2, v in meta[k].items():
                    xasd += f'{6 * " "}<{k2.strip("$")}>{v}</{k2.strip("$")}>\n'
                xasd += f'{4 * " "}</{k.capitalize()}>\n'
    xasd += '  </Metadata>\n'
    xasd += '  <Types>\n'
    for td in schema['types']:
        to = [f' {k}="{v}"' for k, v in topts_s2d(td[TypeOptions], td[CoreType]).items()]
        (ln, end) = ('\n', '    ') if td[Fields] else ('', '')
        xasd += f'{4*" "}<Type name="{td[TypeName]}" type="{td[CoreType]}"{"".join(to)}>{td[TypeDesc]}{ln}'
        for f in td[Fields]:
            if td[CoreType] == 'Enumerated':
                xasd += f'{6*" "}<Item id="{f[ItemID]}" value="{f[ItemValue]}">{f[ItemDesc]}</Item>\n'
            else:
                fo, to = ftopts_s2d(f[FieldOptions], f[FieldType])
                fopts = "".join([f' {k}="{v}"' for k, v in (to | fo).items()])
                xasd += f'{6*" "}<Field id="{f[FieldID]}" name="{f[FieldName]}" type="{f[FieldType]}"{fopts}>{f[FieldDesc]}</Field>\n'
        xasd += f'{end}</Type>\n'
    xasd += '  </Types>\n'
    xasd += '</Schema>\n'
    return xasd


def xasd_dump(schema: dict, fp: str):
    with open(fp, 'w', encoding='utf8') as f:
        f.write(xasd_dumps(schema))


def get_meta(el: ET.Element) -> dict:
    meta = {k: v for k, v in el.items()}
    for e in el:
        if e.tag == 'Roots':
            meta['roots'] = [v.text for v in e]
        elif e.tag == 'Namespaces':
            meta['namespaces'] = [[v.get('prefix'), v.text] for v in e]
        elif e.tag == 'Config':
            meta['config'] = {'$' + v.tag: v.text for v in e}
    return meta

def get_type(e: ET.Element) -> list:
    assert e.tag == 'Type'
    at = {k: v for k, v in e.items()}
    fields = []
    for f in e:
        assert f.tag == 'Field'
        fa = {k: v for k, v in f.items()}
        if f.tag == 'Field':
            fields.append([int(fa.pop('id')), fa.pop('name'), fa.pop('type'), opts_d2s(fa), f.text.strip()])
        elif f.tag == 'Item':
            fields.append([int(fa.pop('id')), fa.pop('value'), f.text.strip()])

    type = [at.pop('name'), at.pop('type'), opts_d2s(at), e.text.strip(), fields]
    return type


def xasd_load(file_path: str) -> dict[str, dict | list]:
    tree = ET.parse(file_path)
    root = tree.getroot()
    assert root.tag == 'Schema'
    assert len(root) == 2
    meta = {}
    types = []
    for element in root:
        if element.tag == 'Metadata':
            meta = get_meta(element)
        elif element.tag == 'Types':
            for el in element:
                types.append(get_type(el))

    return {'meta': meta, 'types': types}


def main(input: str, output_dir: str, fmt: str, recursive: bool) -> None:
    """
    Translate schema between JADN and equivalent formats
    """
    # print(f'Installed JADN version: {jadn.__version__}\n')
    os.makedirs(output_dir, exist_ok=True)

    def convert(path: str, infile: str):
        fn, ext = os.path.splitext(infile)
        if ext in ('.jadn', '.jidl', '.xasd'):
            with open(os.path.join(path, infile)) as fp:
                schema = {
                    '.jadn': load,
                    '.jidl': jidl_load,
                    '.xasd': xasd_load
                }[ext](fp)

            print(os.path.join(path, infile))
            print('\n'.join([f'{k:>15}: {v}' for k, v in analyze(check(schema)).items()]))

            if fmt in ('jadn', 'jidl', 'xasd', 'md', 'dot'):
                {
                    'jadn': dump,
                    'jidl': jidl_dump,
                    'xasd': xasd_dump,
                    'md': markdown_dump,
                    'dot': diagram_dump
                }[fmt](schema, os.path.join(OUTPUT_DIR, f'{fn}.{fmt}'))

    if os.path.isfile(input):
        path, file = os.path.split(input)
        convert(path, file)
    else:
        for path, dirs, files in os.walk(input):
            if not recursive:
                dirs.clear()
            for file in files:
                convert(path, file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Convert JADN schemas to a different format.')
    parser.add_argument('-o', metavar='fmt', default='jadn',
                        help='output format')
    parser.add_argument('-r', action='store_true', help='recursive directory search')
    parser.add_argument('schema_dir')
    parser.add_argument('output_dir', nargs='?', default=OUTPUT_DIR)
    args = parser.parse_args()
    print(args)
    main(args.schema_dir, args.output_dir, args.o, args.r)