"""Literal row metadata; numbering never decides Requirement classification."""
import re


def project(texts):
    first = texts[0] if texts else ''
    code = r'\d+(?:\.\d+){2,}[a-z]?'
    standalone = re.fullmatch(code + r'(?:\s*[&,;]\s*' + code + r')*', first.strip())
    inline = None if standalone else re.match(r'^\s*((?:\d+\.)+\d+[a-z]?)\s+', first)
    fields = {'body': first[inline.end():] if inline else '\n'.join(texts),
              'criteria': '\n'.join(texts[1:]) if inline else ''}
    if inline:
        fields['identifier'] = inline.group(1)
    else:
        # A standalone hierarchical number is its own source cell, not a
        # missing body. Keep that cell in the complete body as well as exposing
        # the exact printed label. Two-component decimals and dates are not
        # inferred to be clause labels. Combined printed labels stay combined.
        if standalone:
            fields['identifier'] = first.strip()
    return fields, bool(inline)
