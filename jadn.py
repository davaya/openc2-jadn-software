import copy
import json
from definitions import TYPE_OPTIONS, FIELD_OPTIONS, CoreType, TypeOptions, Fields, FieldOptions
from typing import TextIO, Any
from numbers import Number


class JADN:
    OPTS = (TYPE_OPTIONS | FIELD_OPTIONS)
    OPTX = {v[0]: k for k, v in OPTS.items()}
    F = {'/', }     # Full-key options (e.g., /format)

    def __init__(self):
        self.schema = None
        self.source = None
        return

    def loads(self, jadn_str: str) -> None:
        """
        Load a schema instance from a string in JSON format
        """
        self.schema = _load(self, json.loads(jadn_str))
        self.source = None

    def load(self, fp: TextIO) -> None:
        """
        Load a schema instance from a file-like object containing JADN data in JSON format
        :param fp: a TextIO reference to an open file

        Example:
            jd = JADN()
            with open('file.jadn', 'r', encoding='utf-8') as fp:
                jd.load(fp)
        """
        self.loads(fp.read())
        self.source = fp

    def dumps(self, strip: bool = True) -> str:
        """
        Return a schema instance as a string containing JADN data in JSON format
        """
        scc = {'meta': self.schema['meta'], 'types': copy.deepcopy(self.schema['types'])}
        return _pprint(_strip_trailing_defaults(scc), strip=strip)

    def dump(self, fp: TextIO, strip: bool = True) -> None:
        """
        Store a schema instance in a file-like object containing JADN data in JSON format

        :param fp: a TextIO reference to an open file
        :param strip: Bool, if True do not store empty trailing fields, default=True

        Example:
            jd = a JADN schema instance from a previous load in any format
            with open('file.jadn', 'w', encoding='utf-8') as fp:
                jd.dump(fp)
        """
        fp.write(self.dumps(strip=strip))

#========================================================
# Private support methods and functions
#========================================================

def _load(self, json: dict) -> dict:
    """
    Convert a dict from JSON data to JADN instance.  For each type definition,
    fill in missing defaults and convert options from string list to dict.

    :param json: {meta, types} in serialized format
    :return: {meta, types} in logical format
    """
    d = [None, None, [], '', []]    # [TypeName, CoreType, TypeOptions, TypeDesc, Fields]
    f = [None, None, None, [], '']  # [FieldId, FieldName, FieldType, FieldOptions, FieldDesc]
    for td in json['types']:
        td += d[len(td):len(d)]
        td[TypeOptions] = _opts_load(self, td[TypeOptions])
        for fd in td[Fields]:
            if td[CoreType] in {'Array', 'Map', 'Record', 'Choice'}:
                fd += f[len(fd):len(f)]
                fd[FieldOptions] = _opts_load(self, fd[FieldOptions])
    return json


def _opts_load(self, tstrings: list[str]) -> dict[str, str]:
    """
    Convert JSON-serialized TypeOptions and FieldOptions to dicts
    """
    def opt(s: str) -> tuple[str, str]:
        return s if s[0] in self.F else self.OPTS[ord(s[:1])][0], '' if s[:1] in self.F else s[1:]
    return dict(opt(s) for s in tstrings)


def _schema_opts_dump(self) -> None:
    pass


def _opts_dump(self, opts: dict[str, str]) -> list[str]:
    """
    Convert TypeOptions and FieldOptions to JSON-serialized strings
    """
    def strs(k: str, v: str) -> str:
        return chr(self.OPTX[k]) + v if k in self.OPTX else k
    return [strs(k, v) for k, v in opts.items()]


def _check(schema: dict) -> dict:
    return schema


def _strip_trailing_defaults(schema: dict) -> dict:
    """
    Remove empty trailing arrays and strings from JSON-serialized schema

    :param schema: JADN schema in JSON format
    :return: JADN schema in JSON format with trailing default values omitted
    """
    tdef = [None, None, [], '', []]
    for td in schema['types']:
        fdef = [None, None, ''] if td[CoreType] == 'Enumerated' else [None, None, None, [], '']
        for fd in td[Fields]:
            while fd and fd[-1] == fdef[len(fd)-1]:
                fd.pop()
        while td and td[-1] == tdef[len(td)-1]:
            td.pop()
    return schema


def _pprint(val: Any, level: int = 0, indent: int = 2, strip: bool = False) -> str:
    """
    Prettyprint a JSON-serialized schema in compact format

    :param val: JSON string to be formatted
    :param level: Indentation level, default = 0 for external calls
    :param indent: Number of spaces per level, default = 2
    :param strip: Remove empty lines between types, boolean default = False
    :return: Formatted JSON string
    """
    if isinstance(val, (Number, type(''))):
        return json.dumps(val, ensure_ascii=False)

    sp = level * indent * ' '
    sp2 = (level + 1) * indent * ' '
    sep2 = ',\n' if strip else ',\n\n'
    if isinstance(val, dict):
        sep = ',\n' if level > 0 else sep2
        lines = sep.join(f'{sp2}"{k}": {_pprint(val[k], level + 1, indent, strip)}' for k in val)
        return f'{{\n{lines}\n{sp}}}'
    if isinstance(val, list):
        sep = ',\n' if level > 1 else sep2
        nest = val and isinstance(val[0], list)  # Not an empty list
        if nest:
            vals = [f"{sp2}{_pprint(v, level, indent, strip)}" for v in val]
            spn = level * indent * ' '
            return f"[\n{sep.join(vals)}\n{spn}]"
        vals = [f"{_pprint(v, level + 1, indent, strip)}" for v in val]
        return f"[{', '.join(vals)}]"
    return '???'


if __name__ == '__main__':
    """
    j = JADN()
    print(len(j.OPTS), j.OPTS)
    print(len(j.OPTX), j.OPTX)

    opts_s = ['[0', ']-1', 'q', '/ipv4', '/d3']
    opts_d = j._opts_load(opts_s)
    print(opts_d)
    opts_s2 = j._opts_dump(opts_d)
    print(opts_s2)
    assert opts_s2 == opts_s
    """

    jd = JADN()
    with open('Projects/JADN/jadn_v2.0_schema.jadn') as fp:
        jd.load(fp)