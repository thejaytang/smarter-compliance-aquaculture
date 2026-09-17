"""Predeclared DEV experiment; geometry consistency, not table/heading truth."""
from dataclasses import asdict
VERSION='native-line-grid-consistency/experiment-1'
TOLERANCE_POINTS=1.0
REJECT_RATIO=0.25

def inspect_grid(page,box,xs,ys,specs,outer):
    cells=[{'row':r,'col':c,'rowspan':rs,'colspan':cs,'bbox':[(box.x0+xs[c])/1.5,(box.y0+ys[r])/1.5,(box.x0+xs[c+cs])/1.5,(box.y0+ys[r+rs])/1.5]} for r,c,rs,cs in specs]
    captured=[];suppressed=[]
    for line in page.text_lines or page.words:
        if not line.text.strip():continue
        l,t,r,b=line.bbox_points;cx=(l+r)/2;cy=(t+b)/2
        if outer[0]<=l and outer[1]<=t and r<=outer[2] and b<=outer[3]:suppressed.append(asdict(line))
        owners=[c for c in cells if c['bbox'][0]<=cx<c['bbox'][2] and c['bbox'][1]<=cy<c['bbox'][3]]
        if not owners:continue
        if len(owners)!=1:raise ValueError('experimental_grid_owner_not_unique')
        owner=owners[0];x0,y0,x1,y1=owner['bbox']
        cuts=[max(0.,x0-l) if x0>outer[0]+1e-6 else 0.,max(0.,r-x1) if x1<outer[2]-1e-6 else 0.,max(0.,y0-t) if y0>outer[1]+1e-6 else 0.,max(0.,b-y1) if y1<outer[3]-1e-6 else 0.]
        outside=[max(0.,outer[0]-l),max(0.,outer[1]-t),max(0.,r-outer[2]),max(0.,b-outer[3])]
        captured.append({'line':asdict(line),'owner':owner,'internal_overflow_points':cuts,'crosses_internal_boundary':max(cuts)>TOLERANCE_POINTS,'external_overflow_points':outside})
    crossing=sum(c['crosses_internal_boundary'] for c in captured);ratio=crossing/len(captured) if captured else None
    return {'method':VERSION,'tolerance_points':TOLERANCE_POINTS,'reject_ratio':REJECT_RATIO,'captured_line_denominator':len(captured),'crossing_line_numerator':crossing,'crossing_ratio':ratio,'reject':ratio is not None and ratio>=REJECT_RATIO,'cells':cells,'captured_lines':captured,'original_positioned_line_fallback':suppressed,'interpretation':'Grid inconsistency only; visible-source/table/heading correctness unverified.'}
