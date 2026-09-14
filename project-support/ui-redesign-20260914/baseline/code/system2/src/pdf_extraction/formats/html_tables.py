"""HTML table geometry. Preserve source spans; invalid geometry abstains explicitly."""
from ..contracts.html import HtmlCell, HtmlTable


def build_table(table, ids):
    rows=[r for r in table.find_all('tr') if r.find_parent('table') is table]
    cells=[]; issues=[]; occupied=set(); width=0
    # A row group is an explicit section or a consecutive run of direct tr children.
    group_ends={}
    for ri in range(len(rows)-1,-1,-1):
        group_ends[ri]=(group_ends[ri+1] if ri+1<len(rows) and rows[ri+1].parent is rows[ri].parent else ri+1)
    for ri,row in enumerate(rows):
        column=0
        for cell in row.find_all(['td','th'],recursive=False):
            try:
                rs=int(cell.get('rowspan',1)); cs=int(cell.get('colspan',1))
                if rs==0: rs=group_ends[ri]-ri
                if not 1<=rs<=group_ends[ri]-ri or not 1<=cs<=1000:
                    raise ValueError()
            except (TypeError,ValueError):
                issues.append('invalid_or_unsupported_span:'+ids[id(cell)])
                cells.append(HtmlCell(node_id=ids[id(cell)],row=ri,column=None,rowspan=None,colspan=None,is_header=cell.name=='th'))
                continue
            while (ri,column) in occupied: column+=1
            if any((r,c) in occupied for r in range(ri,ri+rs) for c in range(column,column+cs)):
                issues.append('overlapping_span:'+ids[id(cell)])
            occupied.update((r,c) for r in range(ri,ri+rs) for c in range(column,column+cs))
            cells.append(HtmlCell(node_id=ids[id(cell)],row=ri,column=column,rowspan=rs,colspan=cs,is_header=cell.name=='th'))
            column+=cs; width=max(width,column)
    return HtmlTable(node_id=ids[id(table)],row_count=len(rows),column_count=None if issues else width,cells=cells,issues=issues)
