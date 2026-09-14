"""Located, narrow document-context genres; not a no-keyword negative rule."""
import re

SUPPORT = re.compile(
    r'For (?:any )?(?:questions|queries) (?:regarding|about|on) [^.!?;\n]+'
    r',\s*please contact [A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\.?', re.I)
AUTHOR_START = re.compile(r'(?:\d+\s+)?[A-Z][A-Za-z’\'\-]+,\s*(?:[A-Z]\.\s*)+')
YEAR = re.compile(r'\b(?:19|20)\d{2}[a-z]?\.\s+')
JOURNAL_END = re.compile(
    r'\S.+\.\s+[A-Z][A-Za-z &’\'\-]+\s+\d+(?:\s*\(\d+\))?,\s*'
    r'\d+\s*[–-]\s*\d+\.\s+https?://\S+\s*$', re.S)


def signals(text):
    value=text.strip()
    category=None
    if SUPPORT.fullmatch(value):
        category='support_contact'
    elif AUTHOR_START.match(value):
        year=YEAR.search(value)
        if year and JOURNAL_END.fullmatch(value[year.end():]):
            category='bibliographic_reference'
    if not category:return []
    start=text.index(value)
    return [dict(category=category,text=value,start=start,end=start+len(value))]
