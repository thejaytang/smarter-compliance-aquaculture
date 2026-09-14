"""Regressions for original grid loss and blank-cell OCR fabrication."""
import cv2
import numpy as np
from PIL import Image
from pdf_extraction.config import TableSettings
from pdf_extraction.layout.detector import detect_table_boxes
from pdf_extraction.layout.marginals import MarginalAnnotation,apply_repeating_marginals
from pdf_extraction.parsers.table import TableParser
from pdf_extraction.types import LayoutRegion,OCRPage,OCRWord,PixelBox,RenderedPage


def test_large_ruled_table_is_not_discarded_as_page_frame(tmp_path):
    arr=np.full((800,600,3),255,np.uint8)
    for x in [35,145,325,565]:cv2.line(arr,(x,50),(x,710),(0,90,90),2)
    for y in [50,160,330,520,710]:cv2.line(arr,(35,y),(565,y),(0,90,90),2)
    path=tmp_path/'table.png';Image.fromarray(arr).save(path)
    boxes=detect_table_boxes(path,TableSettings())
    assert any(b.contains_center(PixelBox(300,400,301,401)) and b.area>600*800*.6 for b in boxes)
    frame=np.full((800,600,3),255,np.uint8)
    cv2.rectangle(frame,(30,40),(570,740),(0,0,0),2);Image.fromarray(frame).save(path)
    assert detect_table_boxes(path,TableSettings())==[]


def test_repeated_words_inside_table_keep_their_grid_and_single_ownership(tmp_path):
    page=RenderedPage(0,tmp_path/'page.png',600,800,600,800,0)
    words=[OCRWord('site','Site name',1,PixelBox(200,60,300,73)),OCRWord('dose','Dosage',1,PixelBox(60,145,120,160))]
    original_box=PixelBox(40,50,560,300)
    table=LayoutRegion('table','table',original_box,.75,word_ids=['site','dose'])
    annotation=MarginalAnnotation(0,'header',(200,60,300,73),'Site name',('native-site',))
    regions=apply_repeating_marginals([table],page,OCRPage(0,words,'native-text-layer'),[annotation])
    assert len(regions)==1
    assert regions[0].bbox==original_box
    assert regions[0].word_ids==['site','dose']


def parse_empty_grid(tmp_path,ink=False):
    image=np.full((260,420,3),255,np.uint8)
    for x in [10,210,410]:cv2.line(image,(x,10),(x,250),(0,0,0),2)
    for y in [10,130,250]:cv2.line(image,(10,y),(410,y),(0,0,0),2)
    if ink:cv2.putText(image,'0',(40,70),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,0),2)
    path=tmp_path/'grid.png';Image.fromarray(image).save(path)
    class CropOCR:
        calls=0
        def recognize_crop(self,image):self.calls+=1;return ('0' if ink else 'a'),.8
    ocr=CropOCR();parser=TableParser(TableSettings(backend='native',img2table_enabled=False,gmft_enabled=False),ocr)
    page=RenderedPage(0,path,420,260,420,260,0)
    result=parser.parse(page,LayoutRegion('table','table',PixelBox(0,0,420,260),.75),OCRPage(0,[],'tesseract'),tmp_path/'crops','table')
    return result,ocr


def test_empty_ruled_cells_do_not_create_crop_ocr_text(tmp_path):
    result,ocr=parse_empty_grid(tmp_path)
    assert result.data.row_count==2 and result.data.column_count==2
    assert all(not c.content.resolved_text for c in result.data.cells)
    assert ocr.calls==0


def test_scanned_ink_without_native_words_still_reaches_crop_ocr(tmp_path):
    result,ocr=parse_empty_grid(tmp_path,ink=True)
    assert ocr.calls==1
    assert [c.content.resolved_text for c in result.data.cells if c.content.resolved_text]==['0']


def test_pale_grid_rules_are_not_inferred_as_merged_cells():
    from pdf_extraction.parsers.table import _merged_cell_specs
    arr=np.full((205,305,3),255,np.uint8)
    for x in [2,152,302]:cv2.line(arr,(x,2),(x,202),(225,225,225),2)
    for y in [2,102,202]:cv2.line(arr,(2,y),(302,y),(225,225,225),2)
    assert _merged_cell_specs(arr,[2,152,302],[2,102,202])==[(0,0,1,1),(0,1,1,1),(1,0,1,1),(1,1,1,1)]
    # Missing only the lower vertical divider makes one actual two-column span.
    arr[106:199,150:155]=255
    assert _merged_cell_specs(arr,[2,152,302],[2,102,202])==[(0,0,1,1),(0,1,1,1),(1,0,1,2)]


def test_unused_header_grid_division_is_compacted_without_changing_spans():
    from pdf_extraction.parsers.table import _compact_grid_specs
    # A spurious line inside a shaded header creates an unused row boundary;
    # both header cells span it. The later real two-column span must survive.
    specs=[(0,0,2,1),(0,1,2,1),(2,0,1,1),(2,1,1,1),(3,0,1,2)]
    actual,xs,ys=_compact_grid_specs(specs,[0,100,200],[0,20,60,100,150])
    assert xs==[0,100,200] and ys==[0,60,100,150]
    assert actual==[(0,0,1,1),(0,1,1,1),(1,0,1,1),(1,1,1,1),(2,0,1,2)]
