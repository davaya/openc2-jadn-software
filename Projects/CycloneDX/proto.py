"""
Translate JADN to Protobuf 3
"""
import json
from lark import Lark

from datetime import datetime
from typing import NoReturn, Tuple, Union
from urllib.parse import urlparse
from jadn.definitions import TypeName, BaseType, TypeOptions, TypeDesc, Fields, INFO_ORDER,\
                         ItemID, FieldID, FieldName, FieldOptions, FieldDesc
from jadn.utils import cleanup_tagid, get_optx, fielddef2jadn, raise_error, typestr2jadn, topts_s2d, ftopts_s2d

# PROTO -> JADN _type regexes
p_tname = r'\s*([-$\w]+)'               # _type _name
p_assign = r'\s*='                      # _type assignment operator
p_tstr = r'\s*(.*?)\s*\{?'             # _type definition
p_tdesc = r'(?:\s*\/\/\s*(.*?)\s*)?'    # _optional _type description

# PROTO -> JADN _field regexes
p_id = r'\s*(\d+)'  # _field ID
p_fname = r'\s+([-:$\w]+\/?)?'  # _field _name with dir/ option (colon is deprecated, allow for now)
p_fstr = r'\s*(.*?)'  # _field definition or Enum value
p_range = r'\s*(?:\[([.*\w]+)\]|(optional))?'  # Multiplicity
p_desc = r'\s*(?:\/\/\s*(.*?)\s*)?'  # _field description, including field name if .id option


def proto_style() -> dict:
    # Return default column positions
    return {
        'comment_pre': True,     # If True, comments on separate line preceding type or field.  If false, inline.
    }


# Convert URI to java-style reversed internet domain name
def uri_to_revid(uri: str) -> str:
    u = urlparse(uri)
    return '.'.join(u.netloc.split(':')[0].split('.')[::-1] + u.path.replace('.', '-').split('/')[1:])


# Convert java-style reversed domain to URI (specify the number of domain components, default=2)
def revid_to_uri(revid: str, hostlen: int=2) -> str:
    o = revid.split('.')
    return f'http://{".".join(o[:hostlen][::-1])}/{"/".join(o[hostlen:])}'


def proto_dumps(schema: dict, style: dict = None) -> str:
    """
    Convert JADN schema to Protobuf 3

    :param dict schema: JADN schema
    :param dict style: Override default column widths if specified
    :return: Protobuf text
    :rtype: str
    """
    w = proto_style()
    if style:
        w.update(style)   # Override any specified column widths

    text = 'syntax = "proto3";\n'
    info = schema['info'] if 'info' in schema else {}
    mlist = [k for k in INFO_ORDER if k in info]
    for k in mlist + list(set(info) - set(mlist)):              # Display info elements in fixed order
        if k == 'package':
            text += f'package {uri_to_revid(info[k])};\n'
        else:
            text += f'// {k:>{w["info"]}}: {json.dumps(info[k])}\n'  # TODO: wrap to page width, parse continuation

    for td in schema['types']:
        topts = topts_s2d(td[TypeOptions])
        if td[TypeDesc]:
            text += f'// {td[TypeDesc]}\n'
        if td[BaseType] in ('Record', 'Map', 'Array'):
            text += f'message {td[TypeName]} {{  // ${td[BaseType]} {topts}\n'
        elif td[BaseType] == 'Enumerated':
            text += f'enum {td[TypeName]} {{  // ${topts}\n'
        else:
            text += f'// ${td[TypeName]}({td[BaseType]}) {topts}\n'

        for fd in td[Fields] if len(td) > Fields else []:       # TODO: constant-length types
            fopts, ftopts = ftopts_s2d(fd[FieldOptions])
            if fd[FieldDesc]:
                text += f'// {fd[FieldDesc]}\n'

        if td[BaseType] in ('Record', 'Map', 'Array', 'Enumerated', 'Choice'):
            text += '}\n\n'
    return text


def proto_dump(schema: dict, fname: Union[bytes, str, int], source='', style=None) -> NoReturn:
    with open(fname, 'w', encoding='utf8') as f:
        if source:
            f.write(f'/* Generated from {source}, {datetime.ctime(datetime.now())} */\n\n')
        f.write(proto_dumps(schema, style))


# Convert PROTO to JADN
def proto_loads(text: str) -> dict:
    proto_parser = Lark(r"""
    LETTER: "A".."Z" | "a".."z"
    DECIMAL_DIGIT: "0".."9"
    OCTAL_DIGIT: "0".."7"
    HEX_DIGIT: "0".."9" | "A".."F" | "a".."f"
    
    ident: LETTER (LETTER | DECIMAL_DIGIT | "_")*
    full_ident: ident ("." ident)*
    message_name: ident
    enum_name: ident
    field_name: ident
    oneof_name: ident
    map_name: ident
    service_name: ident
    rpc_name: ident
    message_type: [ "." ] (ident ".")* message_name
    enum_type: [ "." ] (ident ".")* enum_name
    
    int_lit: decimal_lit | octal_lit | hex_lit
    decimal_lit: ["-"] ("1".."9") (decimal_digit)*
    octal_lit: ["-"] "0" (octal_digit)*
    hex_lit: ["-"] "0" ( "x" | "X" ) hex_digit (hex_digit)*
    
    float_lit: ["-"] ( decimals "." [ decimals ] [ exponent ] | decimals exponent | "."decimals [ exponent ] ) | "inf" | "nan"
    decimals: ["-"] decimal_digit (decimal_digit)*
    exponent: ( "e" | "E" ) [ "+" | "-" ] decimals
    
    str_lit: str_lit_single { str_lit_single }
    str_lit_single: ( "'" (char_value)* "'" ) | ( '"' (char_value)* '"' )
    char_value: hex_escape | oct_escape | char_escape | unicode_escape | unicodeLong_escape | /[^\0\n\\]/
    hex_escape: '\' ( "x" | "X" ) hex_digit [ hex_digit ]
    oct_escape: '\' octal_digit [ octal_digit [ octal_digit ] ]
    char_escape: '\' ( "a" | "b" | "f" | "n" | "r" | "t" | "v" | '\' | "'" | '"' )
    unicode_escape: '\' "u" hex_digit hex_digit hex_digit hex_digit
    unicodeLong_escape: '\' "U" ( "000" hex_digit hex_digit hex_digit hex_digit hex_digit |
                              "0010" hex_digit hex_digit hex_digit hex_digit
    
    empty_statement: ";"
    constant: full_ident | ( [ "-" | "+" ] int_lit ) | ( [ "-" | "+" ] float_lit ) |
                str_lit | bool_lit | Message_value

    syntax: "syntax" "=" ("'" "proto3" "'" | '"' "proto3" '"') ";"
    import: "import" [ "weak" | "public" ] str_lit ";"
    package: "package" full_ident ";"
    
    option: "option" option_name  "=" constant ";"
    option_name: ( ident | bracedFull_ident ) { "." ( ident | bracedFull_ident ) }
    bracedFull_ident: "(" ["."] full_ident ")"
    option_namePart: { ident | "(" ["."] full_ident ")" }
    
    type: "double" | "float" | "int32" | "int64" | "uint32" | "uint64"
      | "sint32" | "sint64" | "fixed32" | "fixed64" | "sfixed32" | "sfixed64"
      | "bool" | "string" | "bytes" | message_type | enum_type
    fieldNumber: int_lit;

    field: [ "repeated" ] type field_name "=" fieldNumber [ "[" field_options "]" ] ";"
    field_options: field_option { ","  field_option }
    field_option: option_name "=" constant

    oneof: "oneof" oneof_name "{" { option | oneof_field } "}"
    oneof_field: type field_name "=" fieldNumber [ "[" field_options "]" ] ";"

    map_field: "map" "<" key_type "," type ">" map_name "=" fieldNumber [ "[" field_options "]" ] ";"
    key_type: "int32" | "int64" | "uint32" | "uint64" | "sint32" | "sint64" |
          "fixed32" | "fixed64" | "sfixed32" | "sfixed64" | "bool" | "string"

    reserved: "reserved" ( ranges | str_field_names ) ";"
    ranges: range { "," range }
    range:  int_lit [ "to" ( int_lit | "max" ) ]
    str_field_names: str_field_name { "," str_field_name }
    str_field_name: "'" field_name "'" | '"' field_name '"'

    enum: "enum" enum_name enumBody
    enumBody: "{" { option | enum_field | empty_statement | reserved } "}"
    enum_field: ident "=" [ "-" ] int_lit [ "[" enum_value_option { ","  enum_value_option } "]" ]";"
    enum_value_option: option_name "=" constant

    message: "message" message_name messageBody
    messageBody: "{" { field | enum | message | option | oneof | map_field |
    reserved | empty_statement } "}"

    service: "service" service_name "{" { option | rpc | empty_statement } "}"
    rpc: "rpc" rpc_name "(" [ "stream" ] message_type ")" "returns" "(" [ "stream" ]
    message_type ")" (( "{" {option | empty_statement } "}" ) | ";")

    proto: [syntax] { import | package | option | topLevelDef | empty_statement }
    topLevelDef: message | enum | service

    """, start='proto')

    tree = proto_parser.parse(text)
    print(tree.pretty())

    info = {}
    types = []

    return {'info': info, 'types': types} if info else {'types': types}


def proto_load(fname: Union[bytes, str, int]) -> dict:
    with open(fname, 'r') as f:
        return proto_loads(f.read())


__all__ = [
    'proto_dump',
    'proto_dumps',
    'proto_load',
    'proto_loads',
    'proto_style'
]
