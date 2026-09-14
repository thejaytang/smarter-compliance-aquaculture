from pathlib import Path
from html import escape
import json, math

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parents[2]
W, H = 7600, 5600
C = {'ink':'#173042','muted':'#526574','paper':'#F4F5F1','white':'#FFFFFF','line':'#ADB9BF',
     's1':'#126B65','a':'#285E8E','b':'#765383','human':'#A15636','gold':'#A5701B','goldbg':'#FFFAEC','off':'#75828A'}
parts=[]; nodes=[]; wires=[]; panels=[]
def esc(t): return escape(str(t))
def box(x,y,w,h,bg='white',border=None,bw=2,r=0,extra='',id=None):
    color=C.get(bg,bg)
    parts.append(f'<div class="shape" {f"id={id}" if id else ""} style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:{color};border:{bw}px solid {C.get(border,border) if border else color};border-radius:{r}px;{extra}"></div>')
def txt(x,y,w,h,t,size=34,color='ink',weight=400,align='left',extra='',label=None):
    parts.append(f'<div class="txt" {f"data-label={label}" if label else ""} style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;font-size:{size}px;color:{C.get(color,color)};font-weight:{weight};text-align:{align};{extra}">{esc(t).replace(chr(10),"<br>")}</div>')
def badge(x,y,t,color='ink',w=72,h=52,size=29):
    box(x,y,w,h,color,r=8);txt(x,y+6,w,h-9,t,size,'white',700,'center')
def wire(points,kind='flow',arrow=True,label=None,lpos=None):
    color={'flow':C['ink'],'review':C['human'],'return':C['human'],'leader':C['line'],'optional':C['off']}[kind]
    thick=5 if kind=='flow' else 3
    dashed=kind in ('return','optional')
    wires.append({'points':points,'kind':kind,'arrow':arrow})
    for (x1,y1),(x2,y2) in zip(points,points[1:]):
        assert x1==x2 or y1==y2, points
        if dashed:
            length=abs(x2-x1)+abs(y2-y1)
            for i in range(0,int(length),23):
                j=min(i+13,length)
                xa=x1+(x2-x1)*i/length; ya=y1+(y2-y1)*i/length
                xb=x1+(x2-x1)*j/length; yb=y1+(y2-y1)*j/length
                box(min(xa,xb)-thick/2,min(ya,yb)-thick/2,max(thick,abs(xb-xa)),max(thick,abs(yb-ya)),color)
        else: box(min(x1,x2)-thick/2,min(y1,y2)-thick/2,max(thick,abs(x2-x1)),max(thick,abs(y2-y1)),color)
    x,y=points[-1];px,py=points[-2]
    if arrow:
        ch='▶' if x>px else '◀' if x<px else '▼' if y>py else '▲'
        txt(x-17,y-19,34,39,ch,31,color,700,'center')
    else: box(x-8,y-8,16,16,color,r=8)
    if label and lpos:
        x,y,w=lpos; box(x-8,y-4,w+16,42,'paper');txt(x,y,w,40,label,26,color,600,'center')
def pin(x,y,n,color): badge(x-34,y-24,n,color,68,48,26)
def node(x,y,w,h,title,sub='',color='ink',ref=None,fill='white'):
    box(x,y,w,h,fill,color,3,13)
    if ref: badge(x+17,y+17,ref,color,67,48,26)
    dx=104 if ref else 24
    txt(x+dx,y+17,w-dx-22,58,title,40,color,700)
    if sub:txt(x+24,y+76,w-48,h-80,sub,29,'muted')
    nodes.append({'title':title,'x':x,'y':y,'w':w,'h':h})
def evaluation(x,y,w,h,scope,rows,method,interpret):
    # A distinctive double-frame evaluation container, with a dark tab and a notched corner.
    box(x,y,w,h,'goldbg','gold',5)
    box(x+12,y+12,w-24,h-24,'goldbg','gold',1)
    box(x+24,y-19,640,61,'gold')
    txt(x+45,y-10,600,46,'MEASUREMENT & EVALUATION',30,'white',700)
    box(x+w-57,y-5,62,53,'white',extra=f'border-left:5px solid {C["gold"]};border-bottom:5px solid {C["gold"]};')
    txt(x+34,y+60,w-68,102,scope,29,'muted',500)
    cy=y+168
    cw=w-68;cols=[0,.47,.68,.84,1]
    labels=['MEASURE','OBSERVED','CRITERION','RESULT']
    for i,l in enumerate(labels):txt(x+34+cw*cols[i],cy,cw*(cols[i+1]-cols[i])-12,40,l,24,'gold',700)
    cy+=47
    for label,result,target,status in rows:
        box(x+34,cy-4,cw,1,'#DCCAA2')
        vals=[label,result,target,status]
        for i,v in enumerate(vals):
            col={'PASS':'#22654A','FAIL':'#A34435','OPEN':'#76674D','REPORT':'#76674D','PENDING':'#76674D'}.get(v,'ink')
            txt(x+34+cw*cols[i],cy+5,cw*(cols[i+1]-cols[i])-13,52,v,29,col,700 if i in(1,3) else 400)
        cy+=59
    cy+=18
    txt(x+34,cy,w-68,40,'HOW IT IS MEASURED',25,'gold',700);cy+=42
    mh=120 if len(method)<235 else 154
    txt(x+34,cy,w-68,mh,method,30,'ink');cy+=mh+15
    box(x+34,cy,w-68,3,'#DCCAA2');cy+=19
    txt(x+34,cy,w-68,h-(cy-y)-28,interpret,29,'muted',500)
def panel(n,x,y,w,h,title,kicker,color,steps,scope,rows,method,interpret,evalh=840):
    panels.append({'id':n,'title':title,'x':x,'y':y,'w':w,'h':h})
    box(x,y,w,h,'white','#C0CBD0',3,18,id='detail-'+n)
    box(x,y,12,h,color,r=5)
    badge(x+38,y+36,n,color,80,62,34)
    txt(x+143,y+33,w-185,42,kicker.upper(),29,color,700)
    txt(x+38,y+108,w-76,125,title,53,'ink',700)
    sy=y+245
    for head,body in steps:
        txt(x+40,sy,w-80,40,head.upper(),26,color,700)
        txt(x+40,sy+42,w-80,95,body,33,'ink');sy+=144
    ey=y+h-evalh-38
    evaluation(x+36,ey,w-72,evalh,scope,rows,method,interpret)

box(0,0,W,H,'paper')
txt(140,65,6000,68,'SMARTER COMPLIANCE / REQUIREMENT WORKSTREAM',43,'s1',700)
txt(140,146,7250,154,'From governed sources to traceable Requirements',110,'ink',700)
txt(145,307,5600,62,'One complete map. Follow the central flow, then zoom into the numbered detail frames.',42,'muted')
txt(5950,65,1500,65,'ARCHITECTURE & EVIDENCE ATLAS',34,'muted',700,'right')
txt(6150,312,1290,56,'Evidence snapshot · 11 Sep 2026',33,'muted',500,'right')

# Outer explanations. Original Q identifiers preserve traceability without introducing code details.
panel('01',140,430,1740,1390,'Govern the source before processing','System1 · source governance','s1',
 [('Process','Intake → retrieve and monitor → govern selection. A named human admits each new candidate.'),('Outcome','Assess authority, scope, version, traceability and permission. Hand off selected originals with evidence; access/body issues stay Pending.')],
 'SCOPE · All 38 source records in the current intake. Preservation is checked separately from source suitability.',
 [('Q01 States explained','38 / 38','100%','PASS'),('Originals preserved','73 / 73','unchanged','PASS'),('Source follow-ups','7 records','explicit','REPORT')],
 'Reconcile every source to a parsed result or an actionable failure. Compare managed-original fingerprints and owning business/history tables before and after the bounded normal-load check.',
 'This proves traceability and preservation. It does not measure authority, completeness of the source pool, or the correctness of every source decision.\nEvidence: intake inventory; normal-load checkpoint 15.',evalh=765)

panel('02',2000,430,1740,1390,'Recover the full source content','System2A · material routing & reconstruction','a',
 [('Process','Profile PDF, supported HTML and XLSX; retain text, order, original numbering and auxiliary content. Scan text requires extraction.')],
 'SCOPE · 31 readable materials; fidelity sample: one real PDF, 8 pages, 275 original regions. Parser 04. Exposed development reference.',
 [('Q02 Readable parsed','31 / 31','≥95%','PASS'),('Q03 Complete regions','64 / 275','≥99%','FAIL'),('Q04 Character error','0.13%','≤1%','PASS'),('Q05 Word error','0.90%','report','REPORT'),('Q06 Critical tokens','211 / 211','100%','PASS'),('Q09 Order pairs','20 / 20','100%','PASS')],
 'Compare all frozen original regions, including missing output. CER = 17 character edits / 12,860 reference characters; WER = 18 word edits / 2,011 words. Check critical tokens and ordered pairs exactly.',
 'Q11 Complete pages: 0/8 (FAIL; report only). Q36 Real scan/mixed/photo quality: UNMEASURED. Complete recovery needs text, structure and relations; 268/275 text-only matches are insufficient. Real-source samples must be evaluated separately.',evalh=950)

panel('03',3860,430,1740,1390,'Preserve tables as coherent objects','System2A · tables, notes & cross-page links','a',
 [('Preserve','Whole table image + title + cells + headers + merged spans + notes. Keep physical page fragments and reading order.'),('Connect','Anchor each title, header, footnote and continuation to its actual scope. B later identifies Requirements inside the table.')],
 'SCOPE · Same frozen PDF sample: 125 body cells, 12 expected relationships and 3 complete logical tables. Parser 04.',
 [('Q07 Exact cell text','123 / 125','≥98%','PASS'),('Q08 Cell positions','125 / 125','≥98%','PASS'),('Q10 Explicit relations','0 / 12','100%','FAIL'),('Q12 Whole tables','0 / 3','report','FAIL')],
 'Match each predefined body cell to reference text and row/column/span position. Check every expected title, note and continuation link. Count a whole table only when content, grid and relationships all agree.',
 'Two cell-text defects remain. Body-cell grid success does not cover footer grids or resolve the missing relationship graph. Manual relation repair is separate functional evidence.',evalh=805)

panel('04',5720,430,1740,1390,'Check the result against the original','System2A · original-side verification','a',
 [('Process','Inspect the original and the extraction together, including areas with no output. Return a located difference, severity and supporting evidence.')],
 'SCOPE · Verifier 6 on the same natural sample. Separately: 12 injected defects and 12 paired unmodified controls.',
 [('Q19 Natural recall','8 / 29','≥90%','FAIL'),('Q20 Critical located','7 / 11','all','FAIL'),('Q21 Finding precision','8 / 33','≥80%','FAIL'),('Q22 Seeded located','12 / 12','12 / 12','PASS'),('Q23 Control false alarms','0 / 12','≤1 control','PASS')],
 'Adjudicate all remaining natural defects from the original. Recall = specific located true findings / all reference defects. Precision = actionable true findings / all actionable prompts. Repeat on each injected/control pair.',
 'A generic warning is not a located error. Natural and injected errors use separate denominators. Separately callable verification does not establish independent accuracy.\nNext: cross-page misses and false/generic prompts.',evalh=950)

panel('05',5920,2040,1540,1750,'Identify Requirements in context','System2B · classification','b',
 [('Input gate','Use accepted A content with complete context, source version, original numbering and location.'),('Decision','Retain Requirement, context, non-Requirement or undetermined. Advisory clauses can be Requirements; negative judgments matter too.'),('Outcome','Keep the original statement, related definitions and conditions with the decision. An A correction triggers affected B re-review.')],
 'SCOPE · Classifier 5; 60 complete units: 41 positives (11 advisory) and 19 negatives. One extra negative is reported separately.',
 [('Q13 Precision','41 / 41','≥95%','PASS'),('Q14 Recall','41 / 41','≥90%','PASS'),('Q15 Advisory recall','11 / 11','≥90%','PASS'),('Q16 Decisive judgments','53 / 60','≥90%','FAIL')],
 'Compare with frozen reference classes. Precision = TP / (TP + FP). Recall = TP / all positive references, including abstained positives. Decisiveness = non-abstained / all units; seven negatives remain undetermined.',
 'B was diagnosed using controlled source-complete A inputs. It does not prove acceptance of raw production A. Separate supplement: 1/1 correct; combined decisiveness 54/61.\nNext: evidence-based resolution of abstentions.',evalh=935)

panel('06',5720,4010,1740,1390,'Keep the parent; make splitting reversible','System2B · provisional subdivision','b',
 [('Process','Preserve the full numbered parent; link generated children to exact accepted source spans and shared context.'),('Boundary','The final split granularity, parent/child delivery and counting need collaborator agreement. Generated labels never replace original numbering.')],
 'SCOPE · 10 real parents and 55 manually selected source spans. Reversible mechanics and production delivery are separate checks.',
 [('Q17 Span bindings','55 / 55','all bindings','PASS'),('Context invalidation','10 / 10','all affected','PASS'),('Q18 Accepted-A delivery','Unmeasured','all bindings','OPEN')],
 'Match selected spans to their source and parent, change parent context and confirm affected children become stale, then test a current accepted-A handoff. Retain one declared parent-or-children counting policy.',
 'Canonical references now bind the 55 spans and 10 parent numbers. All ten real B submissions remain blocked by unaccepted A; delivered subdivision is unmeasured. Automatic semantic split quality is not established.',evalh=775)

panel('07',3860,4010,1740,1390,'Apply evidence-based release gates','Acceptance · confidence & future handoff','b',
 [('Gate','A: text, coverage, structure, order. B: classification, source association, subdivision. Each needs supported confidence; human confirmation is separate.'),('Future','Accepted Requirements feed a reserved System3 interface. Semantic enrichment and Site Model consumer acceptance remain future work.')],
 'SCOPE · A: 8 pages; B: 61 judgments; end-to-end: 1 source. Report each population separately. Production thresholds are unchanged.',
 [('Q24 Safe A release','0 / 8','≥10%','FAIL'),('Q25 Safe B release','0 / 61','≥10%','FAIL'),('Q26 End-to-end release','0 / 1','≥10%','FAIL'),('Q35 Independent holdout','Unmeasured','qualified set','OPEN')],
 'Count evidence-qualified automatic releases over each declared evaluation population. Qualify reliability using independent labels, separate calibration and held-out source sets, with critical-error gates.',
 'The release-qualified subset is zero, so automatic-pass correctness has no sample. Default 95% confidence settings are not measured accuracy. A successful save does not bypass the release gate.',evalh=805)

panel('08',2000,4010,1740,1390,'Save once, preserve history, publish a view','Shared delivery · versioning & Excel','human',
 [('Process','A confirmed decision saves durably with a named actor and receipt. Source or context changes reopen only affected results; old versions remain.'),('Output','Build one consistent, one-way Excel snapshot. A saved decision and a pending, failed or synchronized export have separate visible states.')],
 'SCOPE · Candidate 08; isolated copy of 38 documents / 15,120 review items. Two ordinary exports and one lock/unlock recovery.',
 [('Q32 Ordinary export','13.38 s','≤60 s','PASS'),('Q33 Ordinary export','13.80 s','≤60 s','PASS'),('Q34 Unlock recovery','15.42 s','≤60 s','PASS'),('Q38 Native Excel QA','Unmeasured','visual check','OPEN')],
 'Time from a saved change or unlock to a matching complete workbook, including background wait and serialization. Check event/version readback, replay, stale/conflicting requests, retained history and unchanged originals.',
 'A locked workbook retains the old complete file while decisions continue to save. Export recovery and data readback pass; remaining native Excel visual inspection is Pending by user instruction.',evalh=805)

panel('09',140,4010,1740,1390,'Make human intervention clear and bounded','One workbench · review, repair & burden','human',
 [('Journey','See the requested decision and reason → compare the bound original with effective content → correct or confirm → save → recheck affected results.')],
 'SCOPE · Candidate 08 performance: 38 documents / 15,120 addressable items. Prompt reduction and reviewer effort use separate evidence.',
 [('Q27 Duplicate prompts','42 / 42 removed','≥20% fewer','PASS'),('Q28 Reviewer effort','Unmeasured','timed tasks','OPEN'),('Q29 List read p95','0.310 s · n20','≤1 s','PASS'),('Q30 Cached preview p95','0.763 s · n20','≤2 s','PASS'),('Q31 Saved correction p95','0.658 s · n10','≤2 s','PASS')],
 'Match duplicate prompts by source scope. Rank local request durations; p95 = value at ceil(0.95 × n). For reviewer effort, group overlapping scopes into one task; time active open-to-completion work and record confirm / correct / unresolved outcomes.',
 '15,120 addressable items are not 15,120 independent human tasks. Prompt removal is not measured time saved. Functional scenario evidence is now 16/16 scoped PASS after normal-load checkpoint 15.',evalh=950)

panel('10',140,2040,1540,1750,'Monitor quality; add assistance carefully','Cross-stage support · QA & optional API','off',
 [('Weekly QA design','Monday: 5 System1 sources, 20 A original-side units, 5 B positive/negative judgments. Record short pools and unresolved findings.'),('Optional assistance','Authorised source evidence → bounded cited suggestions → existing checks and human decisions. Local/manual processing remains available.'),('Current boundary','A/B weekly mechanisms were checked in isolation; new normal activation is off. Live providers are disabled. Multi-agent coordination is proposed.')],
 'SCOPE · Weekly checks are monitoring. A future API comparison uses the same frozen samples and reference judgments in both arms.',
 [('Weekly counts','5 / 20 / 5','design counts','REPORT'),('Q37 API benefit','Unmeasured','matched arms','OPEN'),('System3 consumer','Not connected','future review','OPEN')],
 'For weekly QA, sample original areas including missing output and both B classes; deduplicate within stage/week and retain shortfalls. For API evaluation, compare local versus assisted quality, latency, cost and human minutes under identical gates.',
 'No live provider or new schedule is activated by this map. Model votes do not substitute for evidence, calibrated confidence or named decisions.\nIndependent held-out qualification is shown in frame 07.',evalh=875)

# Central operating map.
box(1810,2010,4000,1880,'#F4F5F1','#D9E0E0',2,30)


# Module frames; step descriptions contain no implementation internals.
box(1870,2140,920,960,'#E7F1ED','s1',5,20)
txt(1920,2175,810,68,'System1 · Govern sources',52,'s1',700)
box(2840,2110,2700,1020,'#EAF0F5','#8CA6BA',3,22)
txt(2890,2131,360,43,'SYSTEM2',29,'a',700)
box(2890,2210,1460,890,'#EDF3F7','a',4,17)
txt(2940,2240,1340,66,'A · Reconstruct & verify',51,'a',700)
box(4440,2210,1050,890,'#F2EDF4','b',4,17)
txt(4490,2240,950,66,'B · Identify Requirements',48,'b',700)


node(1920,2320,820,130,'Discover & intake','Existing sources + authorised candidates','s1')
node(1920,2505,820,130,'Retrieve & monitor','Original format · identity · version','s1')
node(1920,2690,820,130,'Govern selection & QA','Evidence + named source decisions','s1')
node(1920,2875,820,140,'Eligible source package','Original + traceability + current selection','s1',fill='#D3E8DF')
for a,b in [(2450,2505),(2635,2690),(2820,2875)]:wire([(2330,a),(2330,b)])

node(2940,2330,1360,140,'Profile & route the material','PDF native / scanned / mixed   •   supported HTML   •   XLSX','a','02')
node(2940,2510,1360,140,'Reconstruct the complete original','Text + order + numbering   •   whole tables + notes   •   images','a','03')
node(2940,2690,1360,140,'Compare directly with the original','Find omissions, changed content, broken structure and relationships','a','04')
node(2940,2870,1360,140,'Content proofreading','Accept current content or route an issue to the shared workbench','a',fill='#DDEAF4')
for a,b in [(2470,2510),(2650,2690),(2830,2870)]:wire([(3620,a),(3620,b)])

node(4490,2330,950,140,'Classify in context','Requirement / context / non-Requirement / unknown','b','05')
node(4490,2510,950,140,'Link parent & subitems','Source spans + shared conditions · provisional','b','06')
node(4490,2690,950,140,'Requirement judgment','Check positive and negative decisions','b')
node(4490,2870,950,140,'Accepted Requirement dataset','Current evidence + decisions + delivery status','b',fill='#E4DBEA')
for a,b in [(2470,2510),(2650,2690),(2830,2870)]:wire([(4965,a),(4965,b)])

# Handoff paths run in the reserved module gutters.
wire([(2740,2945),(2815,2945),(2815,2400),(2940,2400)])
wire([(4300,2940),(4395,2940),(4395,2400),(4490,2400)])
txt(2785,2470,55,380,'S\nO\nU\nR\nC\nE',22,'s1',700,'center')
txt(4360,2470,68,380,'A\n\nP\nA\nS\nS',22,'a',700,'center')

# Future interface has its own faint frame and a visibly interrupted connector.
wire([(5440,2940),(5580,2940)],'optional')
box(5580,2820,230,235,'#E7EBEC','#9EAAB0',3,12)
txt(5594,2842,202,61,'System3',41,'off',700,'center')
txt(5594,2920,202,116,'Semantic\nenrichment\nFUTURE',29,'off',500,'center')

# One human loop spans all three present stages. Separate issue and return arrows.
box(1870,3250,3620,215,'#F5E9E1','human',4,18)
badge(1905,3282,'09','human',78,58,32)
txt(2010,3275,3350,62,'ONE HUMAN WORKBENCH',51,'human',700)
txt(1908,3352,3480,84,'Source decisions   •   Content proofreading   •   Requirement judgment\nDecision + reason + bound original → correction / confirmation → saved history → affected recheck',32,'ink')
for x in (2270,3570,4840):
    wire([(x,3100),(x,3250)],'review')
    wire([(x+115,3250),(x+115,3100)],'return')
txt(2440,3134,340,56,'issues / decisions',25,'human',600)
txt(3730,3134,460,56,'repair → recheck',25,'human',600)
txt(5010,3134,470,56,'review → recheck',25,'human',600)

# A current-version gate and output ownership across the whole map.
box(1870,3540,3620,185,'#E8EDEF','#B3C0C6',3,15)
badge(1905,3570,'08','human',77,57,31)
txt(2010,3557,1660,58,'PRESERVE FACTS & HISTORY',41,'ink',700)
txt(1910,3630,1900,72,'Originals retained · versioned corrections · one-way Excel view',30,'muted')
box(3870,3570,5,120,'#A4B4BE')
badge(3910,3570,'07','b',77,57,31)
txt(4010,3557,1410,58,'RELEASE ONLY CURRENT RESULTS',36,'b',700)
txt(3920,3630,1490,72,'All required evidence + no unresolved blocking issue',30,'muted')
wire([(3300,3465),(3300,3540)],'flow')

# Compact cross-stage support modules share the same outer explanatory frame.
box(1870,3760,1400,112,'#E8ECEB','off',2,12)
badge(1890,3782,'10','off',65,48,26)
txt(1978,3776,1250,47,'Weekly QA → shared review tasks',35,'off',700)
txt(1978,3824,1250,39,'System1: 5 sources · A: 20 originals · B: 5 judgments',27,'muted')
box(3400,3760,1100,112,'#E8ECEB','off',2,12)
badge(3420,3782,'10','off',65,48,26)
txt(3508,3776,960,47,'Optional API assistance · OFF',35,'off',700)
txt(3508,3824,960,39,'S1 / A / B suggestions → existing checks',27,'muted')
# Visible return to source governance for unusable originals; label stays outside node text.
wire([(2940,2420),(2857,2420),(2857,3190),(2070,3190),(2070,3100)],'return')
txt(2854,3180,560,54,'Missing body → source follow-up',25,'human',600)

# Outer leaders are drawn on top of the central frame, in reserved blank gutters.
wire([(1010,1820),(1010,1920),(2300,1920),(2300,2140)],'leader',False)
wire([(2870,1820),(2870,1880),(3300,1880),(3300,2210)],'leader',False)
wire([(4730,1820),(4730,1920),(3770,1920),(3770,2210)],'leader',False)
wire([(6590,1820),(6590,1960),(4210,1960),(4210,2210)],'leader',False)
wire([(5920,2380),(5490,2380)],'leader',False)
wire([(4730,4010),(4730,3850),(4570,3850),(4570,3725)],'leader',False)
wire([(2870,4010),(2870,3850),(3330,3850),(3330,3725)],'leader',False)
wire([(1010,4010),(1010,3900),(1750,3900),(1750,3420),(1870,3420)],'leader',False)
wire([(1680,3320),(1870,3320)],'leader',False)
pin(2300,2140,'01','s1');pin(3300,2210,'02','a');pin(3770,2210,'03','a');pin(4210,2210,'04','a')
# Pins finish the callout links and prevent thin leads from being mistaken for data arrows.
pin(5490,2380,'05','b')
pin(5485,2580,'06','b')
wire([(5485,2580),(5840,2580),(5840,3900),(6590,3900),(6590,4010)],'leader',False)
pin(4570,3725,'07','b');pin(3330,3725,'08','human');pin(1870,3420,'09','human');pin(1870,3320,'10','off')

# Bottom reading key and evidence qualification.
txt(140,5452,2100,48,'READ THE MAP',31,'ink',700)
wire([(560,5477),(720,5477)],'flow');txt(750,5452,820,55,'Solid arrow: workflow / handoff',30,'ink')
wire([(1690,5477),(1840,5477)],'return');txt(1880,5452,1060,55,'Dashed arrow: return / future path',30,'ink')
wire([(2980,5477),(3130,5477)],'leader',False);txt(3170,5452,1190,55,'Fine leader + number: detail reference',30,'ink')
box(4490,5454,61,47,'goldbg','gold',4);txt(4580,5452,1050,55,'Double frame: measured evidence',30,'ink')
txt(5710,5452,1760,55,'PASS = scoped criterion • OPEN = unmeasured',29,'muted',500,'right')
txt(140,5520,7320,60,'Evidence is a dated development diagnosis. Eight real PDF pages are exposed samples, not independent held-out acceptance. Targets shown are stage criteria; they do not change production confidence settings.',30,'muted')

css='''*{box-sizing:border-box}html,body{margin:0;background:#F4F5F1;font-family:Arial,Helvetica,sans-serif}.board{position:relative;width:7600px;height:5600px;overflow:hidden}.shape,.txt{position:absolute}.txt{line-height:1.24;white-space:normal;overflow:visible;font-kerning:normal}.shape{pointer-events:none}'''
html='<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Requirement Workstream | Complete Architecture Map</title><style>'+css+'</style></head><body><main class="board" data-document-role="page" data-label="Requirement Workstream | Complete architecture and evaluation" data-speaker-notes="Start with the central System1 to System2A to System2B flow. Zoom into numbered frames 01 to 10. Double-border evaluation frames contain scope, measurement methods, current observations and stage criteria. Technical implementation details are intentionally omitted. System3 is future; live API assistance is disabled. Evidence snapshot 11 September 2026; this is development diagnosis, not independent acceptance.">'+''.join(parts)+'</main></body></html>'
(ROOT/'architecture-map.html').write_text(html)
(ROOT/'layout.json').write_text(json.dumps({'width':W,'height':H,'panels':panels,'nodes':nodes,'wires':wires},indent=2))
viewer=html.replace('</head>','''<style>html,body{height:100%;overflow:hidden;background:#DEE5E7}#view{position:absolute;left:0;top:70px;right:0;bottom:0;overflow:hidden;touch-action:none}.board{transform-origin:0 0;cursor:grab}.board:active{cursor:grabbing}nav{position:fixed;z-index:8;top:0;left:0;right:0;height:70px;background:#173042;color:white;display:flex;align-items:center;gap:8px;padding:12px 18px;font:14px Arial}nav strong{margin-right:20px}button{font:14px Arial;border:1px solid #6E8999;background:#214254;color:white;border-radius:7px;padding:9px 13px;cursor:pointer}button:hover{background:#436778}#zoom{margin-left:auto;min-width:70px}</style></head>''')
viewer=viewer.replace('<body>','<body><nav><strong>Requirement Workstream</strong><button onclick="fit()">Full map</button><button onclick="core()">Core workflow</button>'+''.join(f'<button onclick="detail({p["id"]!r})">{p["id"]}</button>' for p in panels)+'<button onclick="scaleBy(1.3)">+</button><button onclick="scaleBy(1/1.3)">−</button><span id="zoom"></span></nav><div id="view">')
script='''</div><script>const P=PANELS;const b=document.querySelector('.board'),v=document.querySelector('#view');let s=1,tx=0,ty=0;function draw(){b.style.transform=`translate(${tx}px,${ty}px) scale(${s})`;document.querySelector('#zoom').textContent=Math.round(s*100)+'%'}function focus(x,y,w,h){s=Math.min((v.clientWidth-46)/w,(v.clientHeight-36)/h);tx=(v.clientWidth-w*s)/2-x*s;ty=(v.clientHeight-h*s)/2-y*s;draw()}function fit(){focus(0,0,7600,5600)}function core(){focus(1800,2000,4050,1900)}function detail(id){const p=P.find(x=>x.id===id);focus(p.x-20,p.y-20,p.w+40,p.h+40)}function scaleBy(k){const x=v.clientWidth/2,y=v.clientHeight/2;tx=x-(x-tx)*k;ty=y-(y-ty)*k;s*=k;draw()}let drag=null;v.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,tx,ty};v.setPointerCapture(e.pointerId)};v.onpointermove=e=>{if(drag){tx=drag.tx+e.clientX-drag.x;ty=drag.ty+e.clientY-drag.y;draw()}};v.onpointerup=()=>drag=null;v.onwheel=e=>{e.preventDefault();let k=Math.exp(-e.deltaY*.0015),r=v.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;tx=x-(x-tx)*k;ty=y-(y-ty)*k;s*=k;draw()};window.onresize=fit;fit();</script>'''.replace('PANELS',json.dumps(panels))
viewer=viewer.replace('</body>',script+'</body>')
(ROOT/'review.html').write_text(viewer)
print(json.dumps({'artifact':str(ROOT/'architecture-map.html'),'preview':str(ROOT/'review.html'),'panels':len(panels),'nodes':len(nodes),'wires':len(wires),'size':[W,H]}))
