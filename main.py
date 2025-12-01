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

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_kind: str):
        token = self.peek()
        if token and token[0] == expected_kind:
            self.pos += 1
            return token
        else:
            line = self._get_line_number(token[2]) if token else self._get_line_number(len(self.text))
            self.errors.append(f"Expected token {expected_kind}, got {token[0] if token else 'EOF'} at line {line}")
            return None

    def _get_line_number(self, pos: int) -> int:
        return self.text[:pos].count('\n') + 1

    def parse_value(self) -> Any:
        token = self.peek()
        if not token:
            self.errors.append("Unexpected end of input while parsing value")
            return None

        if token[0] == 'NUMBER':
            self.consume('NUMBER')
            return int(token[1])
        elif token[0] == 'LBRACE':
            return self.parse_dict()
        elif token[0] == 'HASH':
            self.consume('HASH')
            if self.consume('LPAREN'):
                ident_token = self.consume('IDENT')
                if not ident_token:
                    line = self._get_line_number(self.tokens[self.pos][2]) if self.pos < len(self.tokens) else len(self.text)
                    self.errors.append(f"Expected identifier inside #(...) at line {line}")
                    return None
                name = ident_token[1]
                if name not in self.constants:
                    line = self._get_line_number(ident_token[2])
                    self.errors.append(f"Undefined constant '{name}' used at line {line}")
                    return None
                if not self.consume('RPAREN'):
                    line = self._get_line_number(self.tokens[self.pos][2]) if self.pos < len(self.tokens) else len(self.text)
                    self.errors.append(f"Missing closing parenthesis in #(...) at line {line}")
                    return None
                return self.constants[name]
            else:
                line = self._get_line_number(token[2])
                self.errors.append(f"Expected '(' after '#' at line {line}")
                return None
        else:
            line = self._get_line_number(token[2])
            self.errors.append(f"Unexpected token '{token[1]}' while parsing value at line {line}")
            return None


