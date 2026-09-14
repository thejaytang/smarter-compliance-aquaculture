"""One fixed DEV page, native PDFium evidence only; product code is unchanged."""
from pathlib import Path
from hashlib import sha256
from importlib.metadata import version
from collections import Counter
import ctypes, json, re, time, sys, faulthandler
ROOT=Path.cwd();HERE=Path(__file__).resolve().parent
Q=HERE.parents[1];OLD=Q/'structure-diagnostic/native-assembly-comparison/run-2/asc-farm-pdfium'
WINDOW=OLD/'pdf-window-0001.pdf';NATIVE=OLD/'pdf-native-0001.json'
SOURCE=ROOT/'system2/data/inputs/ASC-STD-001-ASC-Farm-Standard-V1.0.1-Aug-2025.pdf'
SITE=ROOT/'system2/.venv/lib/python3.12/site-packages'
hashf=lambda p:sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def save(name,data):
 with (HERE/name).open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2)
FILES=[SOURCE,WINDOW,NATIVE,Path(__file__),ROOT/'system2/src/pdf_extraction/ingest/native_extractor.py',ROOT/'system2/src/pdf_extraction/types.py',ROOT/'system2/config/pdf-intake-positioned.yaml',SITE/'pypdfium2/_helpers/textpage.py',SITE/'pypdfium2_raw/bindings.py',ROOT/'system2/uv.lock']
freeze={'scope':'Only fixed Farm original page 28 (zero-based 27), derivative index 0 of the existing frozen two-page window; no reserved input.','page_index':27,'derivative_page_index':0,'files':{str(p.relative_to(ROOT)):hashf(p) for p in FILES},'rules':'Native character order retained; existing adapter line splitting reproduced exactly; tokens only partition each original line by Unicode whitespace without replacing text. Native typography is evidence, never a heading correctness verdict.','backend':'pypdfium2','pypdfium2_version':version('pypdfium2'),'external_models':False,'ocr':False}
assert freeze['files'][str(SOURCE.relative_to(ROOT))]=='3b0cdf01f72b518710d5af9c1d8ccaa653c381f45053c7b20a102e06c1de4b20'
save('freeze.json',freeze)
faulthandler.dump_traceback_later(30,repeat=True)
t=time.monotonic()
import pypdfium2 as pdfium
import pypdfium2_raw as raw
native=read(NATIVE);baseline=native['pages'][0]
assert native['original_page_indices'][0]==27
chars=[];lines=[];newlines=[];discarded=[];current=[]
def bbox_union(items):
 boxes=[c['bbox_pdf'] for c in items if c['bbox_pdf'] is not None]
 if not boxes:return None
 left=min(b[0] for b in boxes);bottom=min(b[1] for b in boxes);right=max(b[2] for b in boxes);top=max(b[3] for b in boxes)
 return [max(0.,min(left,width)),max(0.,min(height-top,height)),max(0.,min(right,width)),max(0.,min(height-bottom,height))]
def flush(reason):
 global current
 text=''.join(c['text'] for c in current);normalized=re.sub(r'[ \t]+',' ',text).strip();box=bbox_union(current)
 if normalized and box is not None and box[2]>box[0] and box[3]>box[1]:
  tokens=[];offsets=[];pos=0
  for c in current:offsets.append((pos,pos+len(c['text']),c));pos+=len(c['text'])
  for m in re.finditer(r'\s+|\S+',text):
   members=[c for a,b,c in offsets if a<m.end() and b>m.start()]
   tokens.append({'type':'separator' if m[0].isspace() else 'word','text':m[0],'source_character_indices':[c['index'] for c in members],'text_start':m.start(),'text_end':m.end(),'bbox_points':bbox_union(members),'font_names':sorted({c['font_name'] for c in members if c['font_name']}),'font_sizes':sorted({c['font_size'] for c in members if c['font_size']>0})})
  lines.append({'text':normalized,'raw_text':text,'bbox_points':box,'source_character_indices':[c['index'] for c in current],'split_reason':reason,'tokens':tokens})
 else:discarded.extend(c['index'] for c in current)
 current=[]
doc=pdfium.PdfDocument(WINDOW)
try:
 page=doc[0]
 try:
  width,height=map(float,page.get_size());textpage=page.get_textpage()
  try:
   full_text=textpage.get_text_range()
   for i in range(textpage.count_chars()):
    text=textpage.get_text_range(i,1)
    try:box=list(map(float,textpage.get_charbox(i)));box_error=None
    except Exception as e:box=None;box_error=type(e).__name__+': '+str(e)
    flags=ctypes.c_int();size=int(raw.FPDFText_GetFontInfo(textpage,i,None,0,ctypes.byref(flags)))
    font=None;font_bytes=None;returned_size=None
    if 0<size<=65536:
     buffer=ctypes.create_string_buffer(size)
     returned_size=int(raw.FPDFText_GetFontInfo(textpage,i,buffer,size,ctypes.byref(flags)))
     font_bytes=buffer.raw.hex();font=buffer.value.decode('utf-8',errors='replace')
    obj=raw.FPDFText_GetTextObject(textpage,i)
    char={'index':i,'text':text,'unicode_value':int(raw.FPDFText_GetUnicode(textpage,i)),'text_index':int(raw.FPDFText_GetTextIndexFromCharIndex(textpage,i)),'generated':int(raw.FPDFText_IsGenerated(textpage,i)),'unicode_map_error':int(raw.FPDFText_HasUnicodeMapError(textpage,i)),'bbox_pdf':box,'bbox_error':box_error,'font_size':float(raw.FPDFText_GetFontSize(textpage,i)),'font_name':font,'font_flags':flags.value,'font_buffer_required':size,'font_buffer_returned':returned_size,'font_bytes_hex':font_bytes,'font_weight':int(raw.FPDFText_GetFontWeight(textpage,i)),'text_render_mode':int(raw.FPDFTextObj_GetTextRenderMode(obj)) if obj else None}
    chars.append(char)
    if '\r' in text or '\n' in text:flush('native-newline');newlines.append(i);continue
    if box is not None:
     prior=next((c['bbox_pdf'] for c in reversed(current) if c['bbox_pdf'] is not None),None)
     if prior is not None:
      reason='vertical-shift' if abs(box[1]-prior[1])>6 else ('horizontal-reset' if box[0]+1<prior[0] else ('column-gap' if box[0]-prior[2]>8 else None))
      if reason:flush(reason)
    current.append(char)
   flush('page-end')
  finally:textpage.close()
 finally:page.close()
finally:doc.close()
faulthandler.cancel_dump_traceback_later()
nonspace=[c for c in chars if c['text'].strip()];words=[w for l in lines for w in l['tokens'] if w['type']=='word']
represented=[i for l in lines for i in l['source_character_indices']]+newlines+discarded
invariants={'every_native_character_record_retained':len(chars)==len(set(c['index'] for c in chars)),'all_character_indices_accounted_for':sorted(represented)==list(range(len(chars))),'per_character_join_equals_full_get_text_range':''.join(c['text'] for c in chars)==full_text,'line_texts_equal_existing_adapter':[l['text'] for l in lines]==[b['text'] for b in baseline['text_lines']],'line_bboxes_equal_existing_adapter':[l['bbox_points'] for l in lines]==[b['bbox_points'] for b in baseline['text_lines']],'token_and_separator_partition_preserves_each_raw_line':all(''.join(w['text'] for w in l['tokens'])==l['raw_text'] for l in lines),'nonwhitespace_text_preserved_through_word_grouping':''.join(w['text'] for w in words)==''.join(c for l in lines for c in l['raw_text'] if not c.isspace()),'no_docling_import':not any(k.startswith('docling') for k in sys.modules)}
save('character-evidence.json',{'backend':'pypdfium2','version':version('pypdfium2'),'original_page_index':27,'derivative_page_index':0,'width':width,'height':height,'full_text':full_text,'characters':chars,'newline_indices':newlines,'discarded_by_existing_adapter_indices':discarded})
save('line-word-partition.json',{'lines':lines,'existing_adapter_lines':baseline['text_lines'],'invariants':invariants})
summary={'status':'FEASIBILITY_EVIDENCE_ONLY','elapsed_seconds':time.monotonic()-t,'original_page_index':27,'counts':{'native_characters':len(chars),'nonwhitespace_character_records':len(nonspace),'existing_word_records':len(baseline['words']),'existing_line_records':len(baseline['text_lines']),'existing_character_records':len(baseline['characters']),'whitespace_partition_words':len(words),'nonwhitespace_with_box':sum(c['bbox_pdf'] is not None for c in nonspace),'nonwhitespace_with_font_name':sum(bool(c['font_name']) for c in nonspace),'nonwhitespace_with_positive_font_size':sum(c['font_size']>0 for c in nonspace),'generated_character_records':sum(c['generated']==1 for c in chars),'unicode_map_error_records':sum(c['unicode_map_error']!=0 for c in chars)},'font_names':dict(Counter(c['font_name'] for c in nonspace)),'font_sizes':dict(Counter(c['font_size'] for c in nonspace)),'render_modes':dict(Counter(c['text_render_mode'] for c in nonspace)),'invariants':invariants,'preservation':{str(p.relative_to(ROOT)):hashf(p)==freeze['files'][str(p.relative_to(ROOT))] for p in FILES},'quality_status':'UNMEASURED: no structure/heading/word-accuracy annotation denominator; one active DEV feasibility page.','warning':'Font/render-mode/native text presence cannot establish visible text: covered Criterion text remains unverified. Whitespace partition is not a language-aware word boundary solution.'}
save('summary.json',summary)
print(json.dumps(summary,indent=2))
