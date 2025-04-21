"""
Translate each schema file in Source directory to multiple formats in Out directory
"""
import fire
import jadn
import os
from lark import Lark, Transformer

SCHEMA_DIR = 'Projects'
OUTPUT_DIR = 'Out'
GRAMMAR = 'jidl-grammar.lark'


def main(schema_dir: str = SCHEMA_DIR, output_dir: str = OUTPUT_DIR) -> None:
    print(f'Installed JADN version: {jadn.__version__}\n')
    os.makedirs(output_dir, exist_ok=True)
    with open(GRAMMAR, 'r') as f:
        grammar = f.read()
        parser = Lark(grammar, parser="lalr")  # , transformer=transformer)
    for dirpath, dirnames, filenames in os.walk(schema_dir):
        for f in filenames:
            # print(f'-- {os.path.join(dirpath, f)}')
            fn, ext = os.path.splitext(f)
            if ext in ('.jidl', ):
                path = os.path.join(dirpath, f)
                print(f'{path}')
                with open(path, 'r') as jf:
                    data = jf.read()
                c = parser.parse(data)


if __name__ == '__main__':
    main()
