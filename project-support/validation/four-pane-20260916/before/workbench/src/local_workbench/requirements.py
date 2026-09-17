"""Human-directed, source-bound requirement splitting; no semantic inference."""
from copy import deepcopy
import hashlib
import json
import uuid
from .collaboration import named, now

FIELDS = ('Subject', 'Modal Verb', 'Main Verb', 'Object')
RELATIONS = ('conditions', 'exceptions', 'subrequirement')


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def ensure_labels(doc):
    labels = doc.setdefault('labels', {})
    ordered = sorted(doc['units'], key=lambda i: (doc['spans'][i][0], -doc['spans'][i][1], i))
    for identity in ordered:
        if identity not in labels:
            prefix = 'C' if doc['roles'][identity] == 'condition' else 'R'
            used = [int(x[1:]) for x in labels.values() if x.startswith(prefix)]
            labels[identity] = prefix + str(max(used, default=0) + 1)
    return doc


def unit(text):
    return dict(id=str(uuid.uuid4()), text=text, **{k: None for k in FIELDS + RELATIONS})


def leaves(group):
    if group is None:
        return []
    if not isinstance(group, list) or len(group) < 2:
        raise ValueError('A combination needs a quantity and at least one child.')
    count = len(group) - 1
    q = group[0]
    bounds = [q, q] if type(q) is int else q
    if not isinstance(bounds, list) or len(bounds) != 2 or any(type(n) is not int for n in bounds) or not 0 <= bounds[0] <= bounds[1] <= count:
        raise ValueError('Use an exact count or an inclusive range within the number of direct children.')
    result = []
    for child in group[1:]:
        if isinstance(child, str):
            result.append(child)
        else:
            result.extend(leaves(child))
    if len(result) != len(set(result)):
        raise ValueError('A unit can appear only once in the same combination.')
    return result


def append(group, identity):
    if group is None:
        return [1, identity]
    result = deepcopy(group)
    # Preserve an explicit non-all quantity when appending another choice.
    if type(result[0]) is int and result[0] == len(result) - 1:
        result[0] += 1
    result.append(identity)
    return result


def remove(group, identity):
    if group is None:
        return None
    children = []
    for child in group[1:]:
        value = remove(child, identity) if isinstance(child, list) else child
        if value is not None and value != identity:
            children.append(value)
    if not children:
        return None
    q = deepcopy(group[0])
    # A structural edit resets this group's quantity to all remaining children;
    # the UI displays the result and allows an explicit new quantity.
    if len(children) != len(group) - 1:
        q = len(children)
    return [q, *children]


class Requirements:
    def __init__(self, collaboration):
        self.c = collaboration
        with self.c.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS requirement_sessions(
                    id TEXT PRIMARY KEY, actor TEXT NOT NULL, material_id TEXT NOT NULL,
                    revision INTEGER NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS requirement_steps(
                    session_id TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT NOT NULL,
                    action TEXT NOT NULL, at TEXT NOT NULL, PRIMARY KEY(session_id,revision));
                CREATE TABLE IF NOT EXISTS requirement_requests(
                    actor TEXT NOT NULL, id TEXT NOT NULL, digest TEXT NOT NULL, response TEXT NOT NULL,
                    PRIMARY KEY(actor,id));
                CREATE TABLE IF NOT EXISTS requirement_units(
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, actor TEXT NOT NULL,
                    material_id TEXT NOT NULL, text TEXT NOT NULL, chapter TEXT NOT NULL,
                    source TEXT NOT NULL);
            ''')

    def material(self, actor, identity):
        return self.c.read_material(named(actor), identity)

    def listing(self, actor, material_id):
        actor = named(actor)
        with self.c.db() as db:
            rows = db.execute('SELECT body FROM requirement_sessions WHERE actor=? AND material_id=? ORDER BY rowid', (actor, material_id)).fetchall()
        return {'sessions': [self.summary(json.loads(r[0])) for r in rows]}

    @staticmethod
    def summary(doc):
        return {k: doc[k] for k in ('id', 'revision', 'phase', 'text', 'chapter', 'block_id')}

    def load(self, db, actor, identity):
        row = db.execute('SELECT body FROM requirement_sessions WHERE id=? AND actor=?', (identity, actor)).fetchone()
        if row is None:
            raise ValueError('This splitting session is not available to the selected reviewer.')
        return ensure_labels(json.loads(row[0]))

    @staticmethod
    def stale(doc, material):
        block = next((b for b in material.get('blocks', []) if b['id'] == doc['block_id']), None)
        return (not block or block.get('text') != doc['text'] or block.get('source_refs', []) != doc['source_refs'] or material.get('source') != doc['source']
                or bool(material.get('source_stale')))

    def read(self, actor, identity):
        actor = named(actor)
        with self.c.db() as db:
            doc = self.load(db, actor, identity)
            doc['steps'] = [{'revision': r[0], 'action': r[1], 'at': r[2]} for r in db.execute(
                'SELECT revision,action,at FROM requirement_steps WHERE session_id=? ORDER BY revision DESC LIMIT 50', (identity,))]
        doc['stale'] = bool(self.stale(doc, self.material(actor, doc['material_id'])))
        return doc

    def search(self, actor, query):
        actor = named(actor)
        if not isinstance(query, str) or len(query) > 300:
            raise ValueError('Use a shorter search.')
        pattern = '%' + query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        with self.c.db() as db:
            rows = db.execute("""SELECT id,session_id,material_id,text,chapter,source FROM requirement_units
                WHERE actor=? AND (text LIKE ? ESCAPE '\\' OR chapter LIKE ? ESCAPE '\\' OR id=?)
                ORDER BY rowid DESC LIMIT 50""", (actor, pattern, pattern, query)).fetchall()
        return {'units': [dict(zip(('id', 'session_id', 'material_id', 'text', 'chapter', 'source'), r)) for r in rows]}

    def apply(self, actor, request):
        actor = named(actor)
        allowed = {'request_id', 'action', 'session_id', 'expected_revision', 'material_id', 'material_revision',
                   'block_id', 'unit_id', 'at', 'start', 'end', 'field', 'target_id', 'path', 'indices',
                   'quantity', 'phase', 'history_revision'}
        if not isinstance(request, dict) or set(request) - allowed:
            raise ValueError('Only splitting controls are accepted. Source text and reviewer identity are server-owned.')
        rid = str(uuid.UUID(request['request_id']))
        digest = hashlib.sha256(encode(request).encode()).hexdigest()
        action = request.get('action')
        with self.c.lock, self.c.db() as db:
            prior = db.execute('SELECT digest,response FROM requirement_requests WHERE actor=? AND id=?', (actor, rid)).fetchone()
            if prior:
                if prior[0] != digest:
                    raise ValueError('This request ID was already used for another step.')
                return json.loads(prior[1])
            if action == 'start':
                material = self.material(actor, request['material_id'])
                if material['revision'] != request.get('material_revision') or material.get('source_stale'):
                    raise ValueError('The saved source content changed. Reopen it before starting a new passage.')
                block = next((b for b in material['blocks'] if b['id'] == request['block_id']), None)
                if not block or block.get('role') == 'document_information' or block.get('type') not in ('text', 'heading') or not block.get('text', '').strip():
                    raise ValueError('Select a saved text passage first.')
                if len(block['text']) > 100000:
                    raise ValueError('This passage is too large. Split the source content into paragraphs first.')
                root = unit(block['text'])
                # Headings are extracted content, not a separately managed chapter registry.
                headings = []
                for b in material['blocks']:
                    if b.get('type') == 'heading':
                        level = b.get('level', 1)
                        while headings and headings[-1][0] >= level:
                            headings.pop()
                        headings.append((level, str(b.get('numbering', '')) + ' ' + b.get('text', '')))
                    if b['id'] == block['id']:
                        break
                doc = dict(id=str(uuid.uuid4()), material_id=material['id'], revision=0, phase='relationships',
                           block_id=block['id'], text=block['text'], source=deepcopy(material['source']),
                           source_refs=deepcopy(block.get('source_refs', [])), material_revision=material['revision'],
                           chapter=' / '.join(h[1].strip() for h in headings), title=material.get('title', ''),
                           roots=[1, root['id']], units={root['id']: root},
                           spans={root['id']: [0, len(block['text'])]}, done=[], roles={root['id']: 'requirement'},
                           field_spans={}, reference_evidence={})
            else:
                doc = self.load(db, actor, request.get('session_id', ''))
                if doc['revision'] != request.get('expected_revision'):
                    return {'status': 'conflict', 'error': 'A newer splitting step is saved. Reload before editing.', 'document': doc}
                if self.stale(doc, self.material(actor, doc['material_id'])):
                    raise ValueError('The source passage changed. This history is retained. Start a new session from the current saved passage.')
                self.edit(db, actor, doc, request)
            # Source adapters may write their own workspace metadata. Resolve them
            # before taking the SQLite write lock, then recheck the revision atomically.
            db.execute('BEGIN IMMEDIATE')
            replay = db.execute('SELECT digest,response FROM requirement_requests WHERE actor=? AND id=?', (actor, rid)).fetchone()
            if replay:
                if replay[0] != digest:
                    raise ValueError('This request ID was already used for another step.')
                return json.loads(replay[1])
            if action != 'start':
                current = self.load(db, actor, doc['id'])
                if current['revision'] != request.get('expected_revision'):
                    return {'status': 'conflict', 'error': 'A newer splitting step is saved. Reload before editing.', 'document': current}
            ensure_labels(doc)
            self.validate(db, actor, doc)
            doc['revision'] += 1
            doc['saved_at'] = now()
            body = encode(doc)
            db.execute('INSERT INTO requirement_sessions VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,body=excluded.body',
                       (doc['id'], actor, doc['material_id'], doc['revision'], body))
            db.execute('INSERT INTO requirement_steps VALUES(?,?,?,?,?)', (doc['id'], doc['revision'], body, action, doc['saved_at']))
            db.execute('DELETE FROM requirement_units WHERE session_id=?', (doc['id'],))
            for u in doc['units'].values():
                db.execute('INSERT INTO requirement_units VALUES(?,?,?,?,?,?,?)', (u['id'], doc['id'], actor, doc['material_id'], u['text'], doc['chapter'],
                           encode(dict(source=doc['source'], source_refs=doc['source_refs'], block_id=doc['block_id'], span=doc['spans'][u['id']], material_revision=doc['material_revision']))))
            result = {'status': 'saved', 'document': doc}
            db.execute('INSERT INTO requirement_requests VALUES(?,?,?,?)', (actor, rid, digest, encode(result)))
            return result

    def edit(self, db, actor, doc, r):
        action = r['action']
        if action == 'restore':
            row = db.execute('SELECT body FROM requirement_steps WHERE session_id=? AND revision=?', (doc['id'], r.get('history_revision'))).fetchone()
            if row is None:
                raise ValueError('Choose a saved step from this session.')
            old_revision = doc['revision']
            doc.clear(); doc.update(json.loads(row[0])); doc['revision'] = old_revision
            return
        if action == 'phase':
            phase = r.get('phase')
            if phase not in ('relationships', 'fields', 'complete'):
                raise ValueError('Unknown splitting step.')
            if phase == 'complete' and set(doc['done']) != set(doc['units']):
                raise ValueError('Finish each unit before completing this passage.')
            doc['phase'] = phase
            return
        if doc['phase'] == 'complete':
            raise ValueError('Reopen the fields step before changing completed splitting work.')
        u = doc['units'].get(r.get('unit_id'))
        if action == 'done':
            if not u:
                raise ValueError('Choose a requirement unit.')
            if not any(u[k] for k in FIELDS + RELATIONS) and doc['roles'][u['id']] == 'requirement':
                raise ValueError('Assign the stated fields or relationships before finishing this requirement.')
            if u['id'] not in doc['done']:
                doc['done'].append(u['id'])
            return
        if action in ('assign', 'extract'):
            if not u:
                raise ValueError('Choose a requirement unit.')
            start, end = r.get('start'), r.get('end')
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(u['text']) or not u['text'][start:end].strip():
                raise ValueError('Select an exact nonempty passage in the unit text.')
            field = r.get('field')
            if action == 'assign':
                if field not in FIELDS:
                    raise ValueError('Choose a main format field.')
                u[field] = u['text'][start:end]
                doc['field_spans'].setdefault(u['id'], {})[field] = [start, end]
            else:
                if field not in RELATIONS:
                    raise ValueError('Choose a relationship field.')
                child = unit(u['text'][start:end])
                offset = doc['spans'][u['id']][0]
                doc['units'][child['id']] = child
                doc['spans'][child['id']] = [offset + start, offset + end]
                doc['roles'][child['id']] = 'condition' if field == 'conditions' else 'requirement'
                if field == 'conditions':
                    doc['done'].append(child['id'])
                u[field] = append(u[field], child['id'])
        elif action == 'clear':
            if not u or r.get('field') not in FIELDS:
                raise ValueError('Choose a field to clear.')
            u[r['field']] = None
            doc['field_spans'].get(u['id'], {}).pop(r['field'], None)
        elif action == 'split':
            if not u:
                raise ValueError('Choose the unit to split.')
            at = r.get('at')
            if type(at) is not int or not 0 < at < len(u['text']) or not u['text'][:at].strip() or not u['text'][at:].strip():
                raise ValueError('Place the cursor between two nonempty parts of the passage.')
            if any(u[k] for k in FIELDS + RELATIONS):
                raise ValueError('This unit already contains work. Restore a prior step before changing its boundary.')
            children = [unit(u['text'][:at]), unit(u['text'][at:])]
            begin = doc['spans'][u['id']][0]
            for child, span in zip(children, ([begin, begin+at], [begin+at, begin+len(u['text'])])):
                doc['units'][child['id']] = child
                doc['spans'][child['id']] = span
                doc['roles'][child['id']] = doc['roles'][u['id']]
                if doc['roles'][child['id']] == 'condition':
                    doc['done'].append(child['id'])
            doc.setdefault('labels', {})[children[0]['id']] = doc.get('labels', {}).get(u['id'], 'R1')
            doc['labels'].pop(u['id'], None)
            replacement = [2, *[c['id'] for c in children]]
            def replace(group):
                if group is None:
                    return None
                children = []
                changed = False
                for c in group[1:]:
                    if c == u['id']:
                        children.extend(replacement[1:]); changed = True
                    else:
                        children.append(replace(c) if isinstance(c, list) else c)
                return [len(children) if changed else group[0], *children]
            doc['roots'] = replace(doc['roots'])
            for other in doc['units'].values():
                for field in RELATIONS:
                    other[field] = replace(other[field])
            del doc['units'][u['id']]; del doc['spans'][u['id']]; del doc['roles'][u['id']]
            doc['done'] = [x for x in doc['done'] if x != u['id']]
        elif action == 'link':
            field, target = r.get('field'), r.get('target_id')
            if not u or field not in RELATIONS or target == u['id']:
                raise ValueError('Choose a different unit and a relationship field.')
            if target not in doc['units']:
                row = db.execute('SELECT source,text,session_id FROM requirement_units WHERE id=? AND actor=?', (target, actor)).fetchone()
                if row is None:
                    raise ValueError('Choose an existing requirement ID from the search results.')
                target_doc = self.load(db, actor, row[2])
                if self.stale(target_doc, self.material(actor, target_doc['material_id'])):
                    raise ValueError('The referenced passage changed. Use a current requirement instead.')
                doc['reference_evidence'][target] = dict(source=json.loads(row[0]), text=row[1], session_id=row[2], revision=target_doc['revision'])
            if target in leaves(u[field]):
                raise ValueError('This unit is already linked in that field.')
            u[field] = append(u[field], target)
            if target in leaves(doc['roots']):
                doc['roots'] = remove(doc['roots'], target)
        elif action in ('quantity', 'group', 'ungroup', 'unlink'):
            field = r.get('field')
            if field == 'roots':
                container = doc
            elif u and field in RELATIONS:
                container = u
            else:
                raise ValueError('Choose a combination.')
            group = container[field]
            path = r.get('path', [])
            if not isinstance(path, list) or len(path) > 20:
                raise ValueError('Invalid nesting path.')
            for index in path:
                if type(index) is not int or not isinstance(group, list) or not 1 <= index < len(group) or not isinstance(group[index], list):
                    raise ValueError('This nested combination changed. Reload it.')
                group = group[index]
            if not isinstance(group, list):
                raise ValueError('Choose a nonempty combination.')
            if action == 'quantity':
                group[0] = r.get('quantity')
            else:
                indices = r.get('indices')
                if not isinstance(indices, list) or not indices or any(type(i) is not int or not 1 <= i < len(group) for i in indices) or len(set(indices)) != len(indices):
                    raise ValueError('Choose direct children in this combination.')
                selected = [group[i] for i in sorted(indices)]
                if action == 'group':
                    if len(selected) < 2:
                        raise ValueError('Select at least two children to group.')
                    value = [len(selected), *selected]
                elif action == 'ungroup':
                    if len(selected) != 1 or not isinstance(selected[0], list):
                        raise ValueError('Select one nested group to expand.')
                    value = selected[0][1:]
                else:
                    # Detached local units return to the outer level rather than disappearing.
                    for child in selected:
                        for identity in leaves(child) if isinstance(child, list) else [child]:
                            if identity in doc['units'] and identity not in leaves(doc['roots']):
                                doc['roots'] = append(doc['roots'], identity)
                    value = None
                children = []
                for i, child in enumerate(group[1:], 1):
                    if i == min(indices) and value is not None:
                        children.extend(value if action == 'ungroup' else [value])
                    if i not in indices:
                        children.append(child)
                if not children:
                    if path:
                        raise ValueError('Keep a child in a nested group, or restore a previous step.')
                    container[field] = None
                else:
                    group[:] = [len(children), *children]
        else:
            raise ValueError('Unknown splitting operation.')
        if u:
            doc['done'] = [x for x in doc['done'] if x != u['id']]

    def validate(self, db, actor, doc):
        if not doc['units'] or len(doc['units']) > 1000:
            raise ValueError('A passage must contain 1 to 1000 units.')
        all_docs = [json.loads(r[0]) for r in db.execute('SELECT body FROM requirement_sessions WHERE actor=? AND id<>?', (actor, doc['id']))]
        all_docs.append(doc)
        graph = {}
        for item in all_docs:
            for identity, u in item['units'].items():
                graph[identity] = sum((leaves(u[f]) for f in RELATIONS), [])
        for identity, u in doc['units'].items():
            start, end = doc['spans'][identity]
            if doc['text'][start:end] != u['text']:
                raise ValueError('Unit text must remain an exact source span.')
            for f in FIELDS:
                if u[f] is not None and u[f] not in u['text']:
                    raise ValueError('Field text must be copied from this unit.')
        visiting, visited = set(), set()
        def visit(identity):
            if identity not in graph:
                raise ValueError('A linked unit would be lost. Keep its boundary or remove its incoming links first.')
            if identity in visiting:
                raise ValueError('This link creates a circular requirement relationship.')
            if identity in visited:
                return
            visiting.add(identity)
            for child in graph[identity]:
                visit(child)
            visiting.remove(identity); visited.add(identity)
        for identity in graph:
            visit(identity)
        reachable = set()
        def reach(identity):
            if identity in reachable:
                return
            reachable.add(identity)
            for child in graph[identity]:
                reach(child)
        for identity in leaves(doc['roots']):
            reach(identity)
        if not set(doc['units']) <= reachable:
            raise ValueError('Every local unit must remain connected to the outer requirements.')
