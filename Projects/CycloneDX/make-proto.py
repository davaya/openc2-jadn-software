"""
Translate each schema file in Source directory to multiple formats in Out directory
"""
import fire
import jadn
import os
import proto
import shutil

SCHEMA_DIR = 'release'
OUTPUT_DIR = 'Out'


def translate(filename: str, schema_dir: str, output_dir: str) -> None:
    if not os.path.isfile(p := os.path.join(schema_dir, filename)):
        return
    with open(p, encoding='utf8') as fp:
        schema = jadn.load_any(fp)
    print(f'{filename}:\n' + '\n'.join([f'{k:>15}: {v}' for k, v in jadn.analyze(jadn.check(schema)).items()]))

    fn, ext = os.path.splitext(filename)
    jadn.dump(schema, os.path.join(output_dir, fn + '.jadn'))
    jadn.dump(jadn.transform.unfold_extensions(jadn.transform.strip_comments(schema)),
        os.path.join(output_dir, fn + '-core.jadn'))
    jadn.convert.diagram_dump(schema, os.path.join(output_dir, fn + '_ia.dot'),
        style={'format': 'graphviz', 'detail': 'information', 'attributes': True, 'links': True})
    jadn.convert.diagram_dump(schema, os.path.join(output_dir, fn + '_i.puml'),
        style={'format': 'plantuml', 'detail': 'information', 'attributes': False, 'links': False})
    jadn.convert.jidl_dump(schema, os.path.join(output_dir, fn + '.jidl'), style={'desc': 60, 'name': 24})
    jadn.convert.html_dump(schema, os.path.join(output_dir, fn + '.html'))
    jadn.convert.markdown_dump(schema, os.path.join(output_dir, fn + '.md'))
    jadn.translate.json_schema_dump(schema, os.path.join(output_dir, fn + '.json'))


def main(schema_dir: str = SCHEMA_DIR, output_dir: str = OUTPUT_DIR) -> None:
    print(f'Installed JADN version: {jadn.__version__}\n')
    os.makedirs(output_dir, exist_ok=True)
    for f in os.listdir(schema_dir):
        fn, ext = os.path.splitext(f)
        if ext == '.proto':
            try:
                schema = proto.proto_load(os.path.join(schema_dir, f))
            except (ValueError, IndexError) as e:
                print(f'### {f}: {e}')
                raise


if __name__ == '__main__':
    fire.Fire(main)