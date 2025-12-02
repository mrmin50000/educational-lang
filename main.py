import sys
import json
from typing import Any, Dict
from lark import Lark, Transformer, v_args, UnexpectedInput, UnexpectedToken

grammar = r"""
    ?start: (constant_def | dict_entry)*

    constant_def: IDENT "=" value ";"
    dict_entry: IDENT ":" value ";"

    ?value: dict
          | number
          | constant_ref

    dict: "{" (dict_item ";")* "}"
    dict_item: IDENT ":" value

    constant_ref: "#" "(" IDENT ")"
    number: SIGNED_INT

    IDENT: /[a-z][a-z0-9_]*/
    COMMENT: /--\[\[[\s\S]*?\]\]/

    %import common.SIGNED_INT
    %import common.WS
    %ignore WS
    %ignore COMMENT
"""

class ConfigTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.constants: Dict[str, Any] = {}
        self.errors = []
        self.defined_constants = set()
    
    def number(self, items):
        return int(items[0])
    
    def IDENT(self, token):
        return str(token)
    
    def dict_item(self, items):
        key, value = items
        return (key, value)
    
    @v_args(inline=True)
    def dict(self, *items):
        result = {}
        for key, value in items:
            if key in result:
                line = getattr(key, 'line', 'unknown')
                self.errors.append(f"Duplicate key '{key}' in dictionary at line {line}")
            result[key] = value
        return result
    
    @v_args(inline=True)
    def constant_ref(self, name):
        if name not in self.constants:
            line = getattr(name, 'line', 'unknown')
            self.errors.append(f"Undefined constant '{name}' used at line {line}")
            return None
        return self.constants[name]
    
    @v_args(inline=True)
    def constant_def(self, name, value):
        if name in self.defined_constants:
            line = getattr(name, 'line', 'unknown')
            self.errors.append(f"Constant '{name}' redefined at line {line}")
        else:
            self.constants[name] = value
            self.defined_constants.add(name)
        return None
    
    @v_args(inline=True)
    def dict_entry(self, key, value):
        return (key, value)
    
    def start(self, items):
        result = {}
        for item in items:
            if item is not None:
                if isinstance(item, tuple):
                    key, value = item
                    result[key] = value
        return result

class ConfigParser:
    def __init__(self, text: str):
        self.text = text
        self.parser = Lark(grammar, parser='lalr', propagate_positions=True)
        self.transformer = ConfigTransformer()
        self.errors = []
    
    def parse(self) -> Dict[str, Any]:
        try:
            tree = self.parser.parse(self.text)
            result = self.transformer.transform(tree)
            
            self.errors = self.transformer.errors
            
            return result
            
        except UnexpectedInput as e:
            if isinstance(e, UnexpectedToken):
                expected = {t for t in e.expected if t.isupper()}
                self.errors.append(
                    f"Unexpected token '{e.token}' at line {e.line}, column {e.column}. "
                    f"Expected one of: {', '.join(sorted(expected)) if expected else 'END OF INPUT'}"
                )
            else:
                self.errors.append(f"Parse error: {e}")
            return {}
        
        except Exception as e:
            self.errors.append(f"Unexpected error: {e}")
            return {}

def main():
    input_text = sys.stdin.read()
    
    parser = ConfigParser(input_text)
    result = parser.parse()
    
    if parser.errors:
        for err in parser.errors:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    main()
