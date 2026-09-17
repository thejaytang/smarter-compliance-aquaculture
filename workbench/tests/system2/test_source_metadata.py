from pathlib import Path
import tempfile
import unittest
from pdf_extraction.intake.source_metadata import inspect

class SourceMetadataTests(unittest.TestCase):
 def test_html_title_publisher_version_and_classification(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'document.html';p.write_text('<html><title>Website navigation</title><script>Wrong metadata</script><h1>Act relating to aquaculture</h1><p>Publisher: Fisheries ministry</p><p>Version: 2026</p></html>')
   r=inspect(p);self.assertEqual(r['fields']['source_title'],'Act relating to aquaculture');self.assertEqual(r['fields']['issuer'],'Fisheries ministry');self.assertEqual(r['fields']['version'],'2026');self.assertEqual(r['fields']['folder_code'],'A_Public_Authority')
 def test_unknown_publisher_and_version_are_not_invented(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'document.html';p.write_text('<h1>Project document</h1><p>2026 somewhere in text.</p>')
   r=inspect(p)['fields'];self.assertEqual(r['issuer'],'');self.assertEqual(r['version'],'');self.assertEqual(r['folder_code'],'Z_Pending_Classification')

 def test_content_profile_has_review_evidence_without_fabricated_permission_or_currency(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'law.html';p.write_text('<html lang="en"><h1>Regulation on aquaculture in Norway</h1><p>Publisher: Fisheries ministry</p><p>Version: 2.1</p><p>Effective date: 2026-01-01</p><p>This regulation applies to aquaculture. Operators shall keep water and fish welfare records.</p></html>')
   r=inspect(p,official_url='https://example.org/law',retrieved=True);f=r['fields'];i=r['inspection']
   self.assertEqual(f['document_type'],'Regulation');self.assertEqual(f['jurisdiction'],'Norway');self.assertEqual(f['authoritative_language'],'English');self.assertEqual(f['effective_date'],'2026-01-01');self.assertIn('aquaculture',f['inclusion_rationale'])
   self.assertEqual(i['dimensions']['traceability']['rating'],'HIGH');self.assertEqual(i['dimensions']['access_permission']['rating'],'UNKNOWN');self.assertEqual(f['access_permission'],'');self.assertEqual(f['provenance_status'],'UNVERIFIED');self.assertEqual(i['dimensions']['version_currency']['rating'],'MEDIUM');self.assertTrue(all(v['confidence'] is None for v in i['dimensions'].values()))
   self.assertIn('Operators shall',i['summary'])
 def test_native_pdf_inspection_reads_beyond_five_pages_and_reports_blank_pages(self):
  from reportlab.pdfgen import canvas
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'law.pdf';c=canvas.Canvas(str(p));c.setTitle('Aquaculture regulation')
   for n in range(6):
    if n!=3:c.drawString(40,760,'Publisher: Fisheries ministry' if n==5 else 'Operators shall check fish welfare.')
    c.showPage()
   c.save();r=inspect(p);self.assertEqual(r['fields']['issuer'],'Fisheries ministry');self.assertEqual(r['inspection']['coverage']['inspected_units'],6);self.assertEqual(r['inspection']['coverage']['unreadable_units'],[4]);self.assertEqual(r['inspection']['status'],'partial')
 def test_spreadsheet_inspects_later_sheets_of_uploaded_original(self):
  from openpyxl import Workbook
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'source.xlsx';w=Workbook();w.active.append(['Aquaculture checklist']);w.create_sheet('Details').append(['Publisher: Fish company']);w.save(p);w.close();r=inspect(p);self.assertEqual(r['inspection']['coverage']['inspected_units'],2);self.assertIn('scope_relevance',r['inspection']['dimensions'])
 def test_access_page_is_a_failure_not_a_source_profile(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'denied.html';p.write_text('<h1>Access denied</h1><p>Please enable cookies.</p>')
   with self.assertRaisesRegex(ValueError,'access or error page'):inspect(p)
