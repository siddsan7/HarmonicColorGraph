"""Syntax shared by corpus token queries and assistant tool identifiers."""

import re

_NUMERAL = r"[b#]?(?:VII|III|VI|IV|II|V|I|vii|iii|vi|iv|ii|v|i)"
_QUALITY = r"(?:maj7|sus2|sus4|h7|o7|7|o|\+|5)?"
_CORE = rf"(?:{_NUMERAL}{_QUALITY}|(?:V|vii|subV){_QUALITY}/{_NUMERAL})"

CORE_TOKEN = re.compile(rf"^[Mm]:{_CORE}$")
FUNCTION_ID = re.compile(rf"^(?:function:)?[Mm]:{_CORE}$")
BARE_ROMAN = re.compile(rf"^{_CORE}$")
