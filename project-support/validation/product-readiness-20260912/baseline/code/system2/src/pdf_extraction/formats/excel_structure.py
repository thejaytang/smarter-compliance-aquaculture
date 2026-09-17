"""Source-declared merge and shared-formula relationships, without recalculation."""
from collections import defaultdict
import re


def source_relationship_issues(part, cells, merges):
    def rectangle(ref):
        points=ref.split(':')
        if len(points) not in (1,2):raise ValueError()
        bounds=[]
        for point in points:
            match=re.fullmatch(r'([A-Z]{1,3})([1-9][0-9]{0,6})',point)
            if not match:raise ValueError()
            letters,row=match.groups();col=0
            for letter in letters:col=26*col+ord(letter)-64
            if col>16384 or int(row)>1048576:raise ValueError()
            bounds.append((col,int(row)))
        if len(bounds)==1:bounds.append(bounds[0])
        (x1,y1),(x2,y2)=bounds
        if x1>x2 or y1>y2:raise ValueError()
        return x1,y1,x2,y2
    issues=[];groups=defaultdict(list)
    for cell in cells:
        attrs=cell.formula_attributes
        if attrs is not None and attrs.get('t')=='shared':
            si=attrs.get('si','')
            if not si.isdecimal():issues.append('shared_formula_index_invalid:'+cell.locator)
            else:groups[si].append(cell)
    for group in groups.values():
        anchors=[c for c in group if c.formula]
        for cell in group:
            if len(anchors)!=1:
                code='shared_formula_anchor_missing:' if not anchors else 'shared_formula_anchor_ambiguous:'
                issues.append(code+cell.locator);continue
            try:bounds=rectangle(anchors[0].formula_attributes.get('ref',''))
            except ValueError:
                issues.append('shared_formula_anchor_range_invalid:'+cell.locator);continue
            x,y,_,_=rectangle(cell.coordinate)
            if not (bounds[0]<=x<=bounds[2] and bounds[1]<=y<=bounds[3]):
                issues.append('shared_formula_outside_anchor_range:'+cell.locator)
    rectangles=[]
    for ref in merges:
        try:bounds=rectangle(ref)
        except ValueError:
            issues.append('invalid_merge_range:'+part+'#'+ref);continue
        if any(bounds[0]<=r[2] and r[0]<=bounds[2] and bounds[1]<=r[3] and r[1]<=bounds[3] for r in rectangles):
            issues.append('overlapping_merge:'+part+'#'+ref)
        rectangles.append(bounds)
    return issues
