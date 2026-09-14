from copy import deepcopy
import unittest
from local_workbench.collaboration import Collaboration


class AttributionDisplayTests(unittest.TestCase):
    def material(self):
        return {'id':'m1','revision':4,'source':{'content_hash':'h'},'source_stale':False,
            'blocks':[{'id':'b1','type':'text','text':'Reviewed text','source_refs':[{'scope_id':'page:1'}]}],
            'checked_scope':['page:1'],
            'review_checks':{'page:1':{'actor':'Ana Jokic','at':'2026-09-12T00:00:00+00:00','source_hash':'h'}},
            'collaboration_provenance':[{'path':'/blocks/b1/text','origin':'human','actor':'Daniel Restad',
                'status':'human_reviewed','reviewer':'Ana Jokic','reviewers':['Ana Jokic']}]}

    def annotate(self, material):
        collaboration=object.__new__(Collaboration)
        collaboration.mode='coordinator';collaboration.get=lambda *args:None
        return collaboration.annotate('Weijie Tang',material)['collaboration']['provenance'][0]

    def test_withdrawn_check_or_old_source_does_not_display_human_review_complete(self):
        for change in ('cleared_scope','wrong_hash','missing_actor','missing_time','stale_source'):
            material=self.material()
            if change=='cleared_scope':material['checked_scope']=[]
            if change=='wrong_hash':material['review_checks']['page:1']['source_hash']='old'
            if change=='missing_actor':material['review_checks']['page:1']['actor']=''
            if change=='missing_time':material['review_checks']['page:1']['at']=''
            if change=='stale_source':material['source_stale']=True
            original=deepcopy(material)
            with self.subTest(change=change):
                record=self.annotate(material)
                self.assertEqual(record['status'],'human_unreviewed')
                self.assertNotIn('reviewer',record);self.assertNotIn('reviewers',record)
                self.assertEqual(material,original)

    def test_real_current_check_names_reviewer_without_relabelling_contributor(self):
        record=self.annotate(self.material())
        self.assertEqual(record['status'],'human_reviewed')
        self.assertEqual(record['actor'],'Daniel Restad')
        self.assertEqual(record['reviewers'],['Ana Jokic'])

    def test_image_original_range_also_requires_its_own_active_check(self):
        material=self.material()
        material['blocks'][0].update(type='image',image={'source_ref':{'scope_id':'page:2'}})
        self.assertEqual(self.annotate(material)['status'],'human_unreviewed')
        material['checked_scope'].append('page:2')
        material['review_checks']['page:2']=dict(material['review_checks']['page:1'],actor='Daniel Restad')
        record=self.annotate(material)
        self.assertEqual(record['status'],'human_reviewed')
        self.assertEqual(record['reviewers'],['Ana Jokic','Daniel Restad'])
