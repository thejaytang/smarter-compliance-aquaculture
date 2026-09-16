"""Local, versioned downstream vocabulary. Empty until explicitly configured."""
import json
from .collaboration import named, now, encoded
from .check_design import IDENTIFIER, OPERATORS

SCHEMA='site-field-catalog/1'
TYPES=('string','integer','double','boolean')


def allowed_operators(kind):
    ops=set(OPERATORS)
    if kind!='string':ops-={'contains','not_contains','begins_with','ends_with','is_empty','is_not_empty'}
    if kind=='boolean':ops&={'equal','not_equal','is_null','is_not_null','in','not_in'}
    return ops


def validate(fields):
    if not isinstance(fields,list) or len(fields)>500:raise ValueError('Use at most 500 catalog fields.')
    seen=set()
    for f in fields:
        if not isinstance(f,dict) or set(f)!={'field','label','type','operators','description'}:raise ValueError('Catalog fields need a mapping, label, type, operators and description.')
        key=f['field'];kind=f['type'];ops=f['operators']
        if not isinstance(key,str) or len(key)>200 or not IDENTIFIER.fullmatch(key) or key in seen:raise ValueError('Each catalog mapping must be a unique table.column identifier.')
        seen.add(key)
        if kind not in TYPES or not isinstance(ops,list) or not ops or any(not isinstance(o,str) for o in ops) or len(set(ops))!=len(ops) or not set(ops)<=allowed_operators(kind):raise ValueError('Catalog operators must match the field type.')
        if any(not isinstance(f[k],str) or len(f[k])>2000 for k in ('label','description')) or not f['label'].strip():raise ValueError('Give each field a readable label.')
    return fields


class Catalog:
    def __init__(self,c):
        self.c=c
        with c.db() as db:db.execute('CREATE TABLE IF NOT EXISTS site_field_catalog(revision INTEGER PRIMARY KEY, body TEXT NOT NULL)')
    def read(self):
        with self.c.db() as db:row=db.execute('SELECT body FROM site_field_catalog ORDER BY revision DESC LIMIT 1').fetchone()
        return json.loads(row[0]) if row else dict(schema=SCHEMA,revision=0,fields=[],actor=None)
    def save(self,actor,req):
        fields=validate(req.get('fields'));actor=named(actor)
        with self.c.lock,self.c.db() as db:
            db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT MAX(revision) FROM site_field_catalog').fetchone()[0] or 0
            if req.get('revision')!=old:raise ValueError('The catalog changed. Reload it before saving.')
            doc=dict(schema=SCHEMA,revision=old+1,fields=fields,actor=actor,updated_at=now())
            db.execute('INSERT INTO site_field_catalog VALUES(?,?)',(old+1,encoded(doc)))
        return doc


def mapping_issues(design,catalog):
    by_id={f['field']:f for f in catalog['fields']};issues=[]
    def walk(n):
        if not n:return
        if 'rules' in n:
            for child in n['rules']:walk(child)
        else:
            field=by_id.get(n['field'])
            if not field or n['type']!=field['type'] or n['operator'] not in field['operators']:
                issues.append(dict(rule_id=n['id'],field=n['field'],message='Mapping is absent from the current catalog or its type/operator changed.'))
    for n in design['groups'].values():walk(n)
    return issues
