import unittest
from types import SimpleNamespace
from local_workbench.server import Application


class ExtractionReadTests(unittest.TestCase):
    def test_read_never_syncs_policy_or_generates_workbook(self):
        app = object.__new__(Application)
        calls = []
        def call(command, **kwargs):
            calls.append((command, kwargs))
            return {'documents': []}
        app.system2 = SimpleNamespace(call=call)
        app.sync_policy = lambda: self.fail('A display read must not apply policy or export Excel')
        app.workbook_status = {'status': 'refreshing'}
        result = app.extraction_state(view='unit', document_id='document', unit_id='unit')
        self.assertEqual(calls, [('state', {'view':'unit','document_id':'document','unit_id':'unit'})])
        self.assertEqual(result['workbook']['status'], 'refreshing')
