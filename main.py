import sys
import re
import json
from typing import Any, Dict, Union

class ConfigParser:
    def __init__(self, text: str):
        self.text = text
        self.tokens = self.tokenize(text)
        self.pos = 0
        self.constants: Dict[str, Any] = {}
        self.errors = []

    def tokenize(self, text: str) -> list:
        text = re.sub(r'--\[\[.*?\]\]', '', text, flags=re.DOTALL)

        token_spec = [
            ('NUMBER',   r'[+-]?([1-9][0-9]*|0)'),
            ('IDENT',    r'[a-z][a-z0-9_]*'),
            ('HASH',     r'#'),
            ('LPAREN',   r'\('),
            ('RPAREN',   r'\)'),
            ('LBRACE',   r'\{'),
            ('RBRACE',   r'\}'),
            ('COLON',    r':'),
            ('SEMICOLON', r';'),
            ('EQUALS',   r'='),
            ('SKIP',     r'[ \t\n\r]+'),
            ('MISMATCH', r'.'),
        ]
        tok_regex = '|'.join(f'(?P<{pair[0]}>{pair[1]})' for pair in token_spec)
        tokens = []
        for mo in re.finditer(tok_regex, text, re.DOTALL):
            kind = mo.lastgroup
            value = mo.group()
            if kind == 'SKIP':
                continue
            elif kind == 'MISMATCH':
                line = text[:mo.start()].count('\n') + 1
                self.errors.append(f"Unexpected character '{value}' at line {line}")
            else:
                tokens.append((kind, value, mo.start()))
        return tokens


