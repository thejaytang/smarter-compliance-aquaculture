"""Independent relationship checks rebuilt from worksheet XML, never parser output."""
import re

N='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def source_relationship_issues(part, root):
    def box(ref):
        if not re.fullmatch(r'[A-Z]{1,3}[1-9][0-9]{0,6}(:[A-Z]{1,3}[1-9][0-9]{0,6})?',ref):
            return None
        corners=[]
        for coord in ref.split(':'):
            col=re.match(r'[A-Z]+',coord).group()
            x=sum((ord(c)-64)*26**i for i,c in enumerate(reversed(col)));y=int(coord[len(col):])
            if x>16384 or y>1048576:return None
            corners.append((x,y))
        left,top=corners[0];right,bottom=corners[-1]
        return (left,top,right,bottom) if left<=right and top<=bottom else None
    issues=[];groups={}
    for cell in root.findall('./'+N+'sheetData/'+N+'row/'+N+'c'):
        f=cell.find(N+'f')
        if f is None or f.get('t')!='shared':continue
        key=f.get('si','');label=part+'#'+cell.get('r')
        if not key.isdecimal():issues.append('shared_formula_index_invalid:'+label)
        else:groups.setdefault(key,[]).append((cell.get('r'),f))
    for members in groups.values():
        origins=[f for _,f in members if f.text]
        for coord,_ in members:
            label=part+'#'+coord
            if not origins:issues.append('shared_formula_anchor_missing:'+label)
            elif len(origins)>1:issues.append('shared_formula_anchor_ambiguous:'+label)
            else:
                ref=box(origins[0].get('ref',''));point=box(coord)
                if ref is None:issues.append('shared_formula_anchor_range_invalid:'+label)
                elif not (ref[0]<=point[0]<=ref[2] and ref[1]<=point[1]<=ref[3]):
                    issues.append('shared_formula_outside_anchor_range:'+label)
    previous=[]
    for merge in root.findall('./'+N+'mergeCells/'+N+'mergeCell'):
        ref=merge.get('ref','');bounds=box(ref)
        if bounds is None:issues.append('invalid_merge_range:'+part+'#'+ref);continue
        for other in previous:
            if not (bounds[2]<other[0] or other[2]<bounds[0] or bounds[3]<other[1] or other[3]<bounds[1]):
                issues.append('overlapping_merge:'+part+'#'+ref);break
        previous.append(bounds)
    return issues
