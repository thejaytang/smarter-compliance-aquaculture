"""Presentation-only normalization of generated source Excel snapshots."""
from copy import copy
from math import ceil
from pathlib import Path
import os
import tempfile
import textwrap
from xml.etree import ElementTree as ET
from zipfile import ZipFile

FONT_ORDER = 'b i strike condense extend outline shadow u vertAlign sz color name family charset scheme'.split()


def prepare_output(workbook, config):
    """Preserve values/formulas, repair invalid inherited views and readable row height."""
    for sheet in workbook:
        for attribute in ('horizontalDpi','verticalDpi'):
            if getattr(sheet.page_setup,attribute)==0:setattr(sheet.page_setup,attribute,None)
        for view in sheet.views.sheetView:
            # Repeated freeze-panes assignments in older exports duplicated panes.
            unique={selection.pane:selection for selection in view.selection}
            view.selection=list(unique.values())
    sheet=workbook[config['sheet_name']]
    header=config.get('header_row',2)
    columns={c.value:c.column for c in sheet[header] if c.value}
    sheet.row_dimensions[header].height=max(sheet.row_dimensions[header].height or 15,36)
    for cell in sheet[header]:
        style=copy(cell.alignment);style.wrap_text=True;style.vertical='top';cell.alignment=style
    filename_column=columns.get('stored_filename')
    if filename_column is None:return
    identity_column=columns.get('source_id',1)
    for row in range(config.get('data_start_row',3),sheet.max_row+1):
        if not sheet.cell(row,identity_column).value:continue
        cell=sheet.cell(row,filename_column)
        style=copy(cell.alignment);style.wrap_text=True;style.vertical='top';cell.alignment=style
        width=sheet.column_dimensions[cell.column_letter].width or 13
        # Conservative character estimate; native Excel verifies representative files.
        capacity=max(8,int((width-2)*.82*11/(cell.font.sz or 11)))
        lines=sum(max(1,len(textwrap.wrap(line,capacity,break_long_words=True,break_on_hyphens=False)))
                  for line in str(cell.value or '').split('\n'))
        # Excel can break at the source-ID hyphen before wrapping the long filename.
        # Reserve that extra line, observed on PA012 in native Excel.
        if lines>1 and '-' in str(cell.value):lines+=1
        height=ceil(lines*(cell.font.sz or 11)*1.35+6)
        sheet.row_dimensions[row].height=max(sheet.row_dimensions[row].height or 15,min(409,height))


def normalize_font_order(path):
    """Emit the SDK-compatible order without removing or changing font properties."""
    path=Path(path)
    fd,name=tempfile.mkstemp(prefix='.font-order-',suffix='.xlsx',dir=path.parent);os.close(fd)
    temporary=Path(name)
    try:
        with ZipFile(path) as source,ZipFile(temporary,'w') as target:
            for item in source.infolist():
                data=source.read(item.filename)
                if item.filename=='xl/styles.xml':
                    root=ET.fromstring(data)
                    fonts=root.find('{*}fonts')
                    for font in fonts if fonts is not None else []:
                        names=[element.tag.rsplit('}',1)[-1] for element in font]
                        if any(name not in FONT_ORDER for name in names):
                            raise ValueError('Unsupported font element; generated output was not published')
                        font[:]=sorted(font,key=lambda e:FONT_ORDER.index(e.tag.rsplit('}',1)[-1]))
                    data=ET.tostring(root,encoding='utf-8')
                target.writestr(item,data)
        os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)
