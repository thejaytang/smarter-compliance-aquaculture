"""Isolated evidence adapter. Keeps current line objects; never imports Docling."""
from dataclasses import asdict
from pathlib import Path
from hashlib import sha256
import ctypes,json,re
import pypdfium2 as pdfium
import pypdfium2_raw as raw
from pdf_extraction.ingest.native_extractor import NativeExtractor
from pdf_extraction.types import NativeObject
VERSION='pdfium-character-word-evidence/experiment-1'
SOURCE_SHA256=sha256(Path(__file__).read_bytes()).hexdigest()

def collect(textpage,width,height,index):
    chars=[];groups=[];newlines=[];discarded=[];current=[]
    def bbox(items):
        boxes=[c['bbox_pdf'] for c in items if c['bbox_pdf'] is not None]
        if not boxes:return None
        return [max(0.,min(min(b[0] for b in boxes),width)),max(0.,min(height-max(b[3] for b in boxes),height)),max(0.,min(max(b[2] for b in boxes),width)),max(0.,min(height-min(b[1] for b in boxes),height))]
    def flush(reason):
        nonlocal current
        text=''.join(c['text'] for c in current);normalized=re.sub(r'[ \t]+',' ',text).strip();box=bbox(current)
        if normalized and box and box[2]>box[0] and box[3]>box[1]:
            tokens=[];offsets=[];pos=0
            for c in current:offsets.append((pos,pos+len(c['text']),c));pos+=len(c['text'])
            for m in re.finditer(r'\s+|\S+',text):
                members=[c for a,b,c in offsets if a<m.end() and b>m.start()]
                tokens.append({'type':'separator' if m[0].isspace() else 'word','text':m[0],'char_indices':[c['index'] for c in members],'text_range':[m.start(),m.end()],'bbox_points':bbox(members),'fonts':sorted({c['font_name'] for c in members if c['font_name']}),'font_sizes':sorted({c['font_size'] for c in members if c['font_size']>0})})
            groups.append({'text':normalized,'raw_text':text,'bbox_points':box,'char_indices':[c['index'] for c in current],'split_reason':reason,'tokens':tokens})
        else:discarded.extend(c['index'] for c in current)
        current=[]
    full=textpage.get_text_range()
    for i in range(textpage.count_chars()):
        text=textpage.get_text_range(i,1)
        try:box=list(map(float,textpage.get_charbox(i)));error=None
        except Exception as e:box=None;error=type(e).__name__+': '+str(e)
        flags=ctypes.c_int();size=int(raw.FPDFText_GetFontInfo(textpage,i,None,0,ctypes.byref(flags)))
        font=None;font_bytes=None;returned=None
        if 0<size<=65536:
            buffer=ctypes.create_string_buffer(size);returned=int(raw.FPDFText_GetFontInfo(textpage,i,buffer,size,ctypes.byref(flags)))
            font=buffer.value.decode('utf-8',errors='replace');font_bytes=buffer.raw.hex()
        c={'id':f'native_p{index:04d}_pdfium_char{i:06d}','index':i,'text':text,'unicode':int(raw.FPDFText_GetUnicode(textpage,i)),'text_index':int(raw.FPDFText_GetTextIndexFromCharIndex(textpage,i)),'generated':int(raw.FPDFText_IsGenerated(textpage,i)),'unicode_map_error':int(raw.FPDFText_HasUnicodeMapError(textpage,i)),'bbox_pdf':box,'bbox_error':error,'font_name':font,'font_size':float(raw.FPDFText_GetFontSize(textpage,i)),'font_flags':flags.value,'font_buffer_required':size,'font_buffer_returned':returned,'font_bytes_hex':font_bytes}
        c['bbox_points']=bbox([c]);chars.append(c)
        if '\r' in text or '\n' in text:flush('native-newline');newlines.append(i);continue
        if box is not None:
            prior=next((c['bbox_pdf'] for c in reversed(current) if c['bbox_pdf'] is not None),None)
            if prior is not None:
                reason='vertical-shift' if abs(box[1]-prior[1])>6 else ('horizontal-reset' if box[0]+1<prior[0] else ('column-gap' if box[0]-prior[2]>8 else None))
                if reason:flush(reason)
        current.append(c)
    flush('page-end')
    words=[]
    for line_idx,line in enumerate(groups):
        for token in line['tokens']:
            if token['type']!='word':continue
            members=token['char_indices'];box=token['bbox_points']
            if not members or box is None:raise ValueError('word_without_preserved_character_geometry')
            identity=f'native_p{index:04d}_pdfium_word{members[0]:06d}_{members[-1]:06d}'
            token['native_word_id']=identity
            words.append(NativeObject(id=identity,text=token['text'],bbox_points=tuple(box),confidence=.95,object_type='word',font_name=token['fonts'][0] if len(token['fonts'])==1 else None,font_key=None,from_ocr=False))
    represented=[i for g in groups for i in g['char_indices']]+newlines+discarded
    invariant={'all_character_indices_accounted_for':sorted(represented)==list(range(len(chars))),'per_char_text_equals_full_text':''.join(c['text'] for c in chars)==full,'token_separator_reconstruction':all(''.join(t['text'] for t in l['tokens'])==l['raw_text'] for l in groups),'word_nonwhitespace_reconstruction':''.join(w.text for w in words)==''.join(c for l in groups for c in l['raw_text'] if not c.isspace())}
    return words,chars,groups,{'invariants':invariant,'full_text':full,'newline_indices':newlines,'discarded_by_original_line_logic':discarded}

class RichNativeExtractor(NativeExtractor):
    GENERATOR_VERSION=VERSION
    GENERATOR_SHA256=SOURCE_SHA256
    def extract(self,pdf_path):
        if self.backend!='pdfium':raise ValueError('experiment_pdfium_only')
        result=super().extract(pdf_path)
        original=[asdict(p) for p in result.pages];evidence=[]
        document=pdfium.PdfDocument(pdf_path)
        try:
            for index,native in enumerate(result.pages):
                page=document[index]
                try:
                    tp=page.get_textpage()
                    try:words,chars,groups,extra=collect(tp,native.width_points,native.height_points,index)
                    finally:tp.close()
                finally:page.close()
                extra['invariants'].update(line_texts_equal=[g['text'] for g in groups]==[w.text for w in native.text_lines],line_bboxes_equal=[g['bbox_points'] for g in groups]==[list(w.bbox_points) for w in native.text_lines])
                if not all(extra['invariants'].values()):raise ValueError('granularity_reconstruction_failed: '+json.dumps(extra['invariants']))
                for g,line in zip(groups,native.text_lines):g['original_native_line_id']=line.id
                native.words=words
                native.characters=[NativeObject(id=c['id'],text=c['text'],bbox_points=tuple(c['bbox_points'] or [0.,0.,0.,0.]),confidence=.95,object_type='character',font_name=c['font_name'],font_key=None,from_ocr=False) for c in chars]
                evidence.append({'local_page_index':index,'original_page_before_enrichment':original[index],'characters':chars,'line_word_groups':groups,**extra})
        finally:document.close()
        out=Path(pdf_path).with_name(Path(pdf_path).stem+'-granularity.json')
        with out.open('x') as f:json.dump({'generator':VERSION,'generator_sha256':SOURCE_SHA256,'backend':result.backend,'version':result.version,'pages':evidence,'scope':'Experimental native granularity; no typography-based heading promotion; text_lines preserved'},f,ensure_ascii=False,indent=2)
        return result
