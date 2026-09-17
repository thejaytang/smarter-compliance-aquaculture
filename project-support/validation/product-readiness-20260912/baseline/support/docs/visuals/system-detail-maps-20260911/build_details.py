from pathlib import Path
from html import escape
import json, re

OUT=Path(__file__).resolve().parent
S=.7; W=5600; H=4200
COL=[100,1490,2880,4270]
Y=[700+260*i for i in range(7)]
C={'ink':'#173042','muted':'#536775','paper':'#F4F5F1','s1':'#176D65','a':'#2A608E','b':'#765387','human':'#A25336','gold':'#A37524','goldbg':'#FFFAEE','line':'#A7B7BD','off':'#77848B'}
class Board:
    def __init__(self,key,title,subtitle,color,modules):
        self.key=key; self.title=title; self.color=color; self.parts=[]; self.nodes=[]; self.wires=[]; self.modules=modules; self.holds=set(); self.measurements=[]; self.human_items=[]
        self.box(0,0,W,H,'paper')
        self.text(100,65,4300,60,'REQUIREMENT WORKSTREAM / SYSTEM DETAIL '+key.upper(),41,color,700)
        self.text(100,140,5380,125,title,88,'ink',700)
        self.text(105,295,5350,93,subtitle,36,'muted')
        self.text(4310,65,1180,60,'PROCESS + DECISIONS + EVIDENCE',30,'muted',700,'right')
        for i,(name,desc) in enumerate(modules):
            x=COL[i]
            self.box(x,470,1230,2120,'white',color,3,18)
            self.box(x,470,1230,166,{'s1':'#E4F0EB','a':'#E6EFF6','b':'#EFE8F3'}[color],color,3,18)
            self.badge(x+32,500,f'0{i+1}',color)
            self.text(x+139,492,1030,76,name,49,color,700)
            self.text(x+36,576,1150,56,desc,31,'muted')
    def box(self,x,y,w,h,bg='white',border=None,bw=1,r=0,extra=''):
        bg=C.get(bg,bg); border=C.get(border,border) if border else bg
        self.parts.append(f'<div class="shape" style="left:{x*S}px;top:{y*S}px;width:{w*S}px;height:{h*S}px;background:{bg};border:{bw*S}px solid {border};border-radius:{r*S}px;{extra}"></div>')
    def text(self,x,y,w,h,t,size=34,color='ink',weight=400,align='left'):
        self.parts.append(f'<div class="txt" style="left:{x*S}px;top:{y*S}px;width:{w*S}px;height:{h*S}px;font-size:{size*S}px;color:{C.get(color,color)};font-weight:{weight};text-align:{align}">{escape(str(t)).replace(chr(10),"<br>")}</div>')
    def badge(self,x,y,t,color):
        self.box(x,y,85,57,color,r=7);self.text(x,y+7,85,46,t,32,'white',700,'center')
    def wire(self,pts,kind='flow',arrow=True,label=None):
        col=C[{'flow':'ink','hold':'human','return':'human','leader':'line','off':'off'}[kind]]
        th=4 if kind=='flow' else 3
        self.wires.append({'points':pts,'kind':kind,'arrow':arrow})
        for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
            assert x1==x2 or y1==y2
            ln=abs(x2-x1)+abs(y2-y1)
            intervals=[(0,ln)] if kind not in ('return','off') else [(j,min(j+13,ln)) for j in range(0,int(ln),23)]
            for a,b in intervals:
                if not ln:continue
                xa=x1+(x2-x1)*a/ln; ya=y1+(y2-y1)*a/ln;xb=x1+(x2-x1)*b/ln;yb=y1+(y2-y1)*b/ln
                self.box(min(xa,xb)-th/2,min(ya,yb)-th/2,max(th,abs(xb-xa)),max(th,abs(yb-ya)),col)
        if arrow:
            (px,py),(x,y)=pts[-2:];ch='▶' if x>px else '◀' if x<px else '▼' if y>py else '▲'
            self.text(x-16,y-18,32,37,ch,30,col,700,'center')
        if label:
            x,y,t=label;self.box(x-4,y-2,122,35,'white');self.text(x,y,118,36,t,24,col,700,'center')
    def step(self,m,r,title,body,decision=False,continuation=None):
        x=COL[m]+40;y=Y[r]
        self.box(x,y,760,180,'#FFF5DB' if decision else 'white',self.color,3,12)
        self.text(x+22,y+13,718,79,title,32,self.color,700)
        self.text(x+22,y+97,718,77,body,28,'ink')
        self.nodes.append({'module':m+1,'row':r+1,'title':title,'body':body,'x':x*S,'y':y*S,'w':760*S,'h':180*S,'decision':decision})
        if r<6:self.wire([(x+380,y+180),(x+380,Y[r+1])],label=(x+400,y+201,continuation) if continuation else None)
    def branch(self,m,r,label,title,body,hold=False,route_to=None):
        x=COL[m]+860;y=Y[r]-4
        self.box(x,y,330,198,'#FCF0E8' if hold else '#EEF2F3','human' if hold else 'line',2,12)
        self.text(x+18,y+12,294,70,title,28,'human' if hold else 'ink',700)
        self.text(x+18,y+86,294,104,body,24,'muted')
        self.wire([(COL[m]+800,Y[r]+80),(x,Y[r]+80)],'hold' if hold else 'flow')
        self.text(x+4,y-37,322,32,label.upper(),22,'human' if hold else 'ink',700)
        self.nodes.append({'module':m+1,'row':r+1,'title':title,'body':body,'x':x*S,'y':y*S,'w':330*S,'h':198*S,'branch':True})
        if hold:
            lane=COL[m]+1250;self.holds.add(m)
            self.wire([(x+330,Y[r]+96),(lane,Y[r]+96),(lane,2635)],'hold',False)
        if route_to:
            tm,tr=route_to;lane=COL[m]+1285
            if tm==m:
                self.wire([(x+330,Y[r]+96),(lane,Y[r]+96),(lane,Y[tr]-35),(COL[tm]+760,Y[tr]-35),(COL[tm]+760,Y[tr])],'flow')
            else:
                self.wire([(x+330,Y[r]+96),(lane,Y[r]+96),(lane,Y[tr]+80),(COL[tm]+40,Y[tr]+80)],'flow')
    def handoff(self,m,label):
        x=COL[m];lane=x+1307
        self.wire([(x+420,Y[6]+180),(x+420,2470),(lane,2470),(lane,Y[0]+80),(COL[m+1]+40,Y[0]+80)])
        self.text(x+45,2490,1140,71,label,31,self.color,600)
    def human(self,items,rule):
        self.human_items={'items':items,'rule':rule}
        self.box(100,2635,5400,302,'#F6EAE2','human',3,16)
        self.text(140,2650,5260,50,'SHARED HUMAN WORKBENCH · ALL EXCEPTIONS REMAIN TRACEABLE',34,'human',700)
        for i,(t,b) in enumerate(items):
            x=135+i*895
            self.box(x,2720,844,142,'white','#D3B6A5',2,10)
            self.text(x+17,2732,810,48,t,32,'human',700)
            self.text(x+17,2786,810,67,b,28,'ink')
            if i<5:self.wire([(x+844,2790),(x+887,2790)],'hold')
        self.text(142,2890,5260,43,rule,29,'human',600)
        for m in self.holds:
            lane=COL[m]+1250
            self.wire([(lane,2635),(lane,2690)],'hold')
            self.wire([(COL[m]+740,2635),(COL[m]+740,2590)],'return')
    def measure(self,m,title,scope,rows,method,conclusion):
        self.measurements.append({'module':m+1,'title':title,'scope':scope,'rows':rows,'method':method,'conclusion':conclusion})
        x=COL[m];y=3040;w=1230;h=950
        self.wire([(x+460,2590),(x+460,2612)],'leader',False)
        self.box(x,y,w,h,'goldbg','gold',4)
        self.box(x+12,y+12,w-24,h-24,'goldbg','gold',1)
        self.box(x+22,y-18,860,59,'gold')
        self.text(x+42,y-8,820,45,'MEASUREMENT & EVALUATION',32,'white',700)
        self.box(x+w-57,y-4,61,49,'paper',extra=f'border-left:{4*S}px solid {C["gold"]};border-bottom:{4*S}px solid {C["gold"]};')
        self.text(x+30,y+63,w-60,61,title,39,'gold',700)
        self.text(x+30,y+137,w-60,118,scope,30,'muted')
        yy=y+265
        self.text(x+30,yy,600,42,'MEASURE / OBSERVATION',24,'gold',700)
        self.text(x+815,yy,370,42,'CRITERION / RESULT',24,'gold',700)
        yy+=50
        for a,b in rows:
            self.box(x+30,yy-5,w-60,1,'#DCCAA2')
            self.text(x+30,yy+5,754,76,a,30,'ink',600)
            self.text(x+815,yy+5,375,76,b,29,'human' if 'FAIL' in b else 'gold' if 'OPEN' in b else 'ink',600)
            yy+=80
        yy+=15
        self.text(x+30,yy,w-60,45,'HOW TO MEASURE / EVALUATE',25,'gold',700);yy+=48
        self.text(x+30,yy,w-60,185,method,30,'ink');yy+=196
        self.box(x+30,yy,w-60,2,'#DCCAA2');yy+=18
        self.text(x+30,yy,w-60,y+h-yy-23,conclusion,26,'muted')
    def finish(self,note):
        self.text(110,4040,5290,53,note,30,'muted')
        self.text(110,4110,5290,48,'Solid arrows: sequence or branch  ·  Amber nodes: decision  ·  Rust paths: human exception / return  ·  Gold double frames: scoped evaluation  ·  Evidence: 11 Sep 2026',27,'muted')
        css=f'*{{box-sizing:border-box}}html,body{{margin:0;background:{C["paper"]};font-family:Arial,Helvetica,sans-serif}}.board{{position:relative;width:{W*S}px;height:{H*S}px;overflow:hidden}}.txt,.shape{{position:absolute}}.txt{{line-height:1.2;overflow:visible}}'
        html=f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{escape(self.title)}</title><style>{css}</style></head><body><main class="board" data-document-role="page" data-label="{escape(self.title)}" data-speaker-notes="Read modules 01 through 04. Follow numbered main steps, decision branches and the shared human return loop. Review the corresponding gold evaluation frames. This map expands one current processing stage; System3 semantic enrichment remains future.">'+''.join(self.parts)+'</main></body></html>'
        (OUT/f'{self.key}.html').write_text(html)
        layout={'key':self.key,'title':self.title,'size':[W*S,H*S],'nodes':self.nodes,'wires':self.wires,'human':self.human_items,'measurements':self.measurements,'modules':[{'label':m[0],'description':m[1],'x':COL[i]*S,'y':470*S,'w':1230*S,'h':3540*S} for i,m in enumerate(self.modules)]}
        (OUT/f'{self.key}-layout.json').write_text(json.dumps(layout,indent=2))
        return html,layout

def fill(board,data):
    for m,steps in enumerate(data):
        for r,step in enumerate(steps):board.step(m,r,*step)

s1=Board('system1','System1 | Govern the source, version and admission','Detailed flow: intake → retrieve and retain versions → assess effective selection → release a traceable source package. One Leader coordinates the three bounded modules and their handoff.','s1',[
 ('Discovery & intake','Establish identity before admitting a candidate'),('Retrieval & monitoring','Preserve the official original and its versions'),('Governance & QA','Keep human authority and evaluate source eligibility'),('Handoff & continuity','Expose current outputs; reopen only affected scope')])
fill(s1,[
 [('01 · Registered identity?','Distinguish existing governed sources from new proposals.',True,'new'),('02 · Receive a candidate','Authorised local file or structured candidate; record its origin.'),('03 · Compare identities','Check duplicate official identities and missing source fields.',True,'clear'),('04 · Complete the proposal','Locate the official source, retrieval target, format and provenance.'),('05 · Named human ACCEPT?','Admission is explicit; ordinary ratings do not create a source.',True,'yes'),('06 · Register the source','Assign the formal source identity and retain the admission decision.'),('07 · Queue eligible retrieval','Existing and newly admitted current records join the same route.')],
 [('01 · Resolve retrieval target','Official identity and retrievable original are separate concepts.'),('02 · Acquire the original','Keep authoritative language and original published format.'),('03 · Usable payload?','Check format, expected file evidence and failed/restricted access.',True,'yes'),('04 · Compare current version','Compare exact source bytes with the retained snapshot.',True,'changed'),('05 · Retain a new snapshot','Keep the previous original; attach provenance and version lineage.'),('06 · Record acquisition state','Success, failure and restricted access remain distinct from selection.'),('07 · Return current evidence','Expose the valid snapshot, version, access result and any open issue.')],
 [('01 · Preserve human decisions','Read the current selection, named decisions, reports and drafts.'),('02 · Assess five dimensions','Authority, relevance, currency, traceability and access permission.'),('03 · Evidence supports scores?','Each dimension needs scoped evidence and calibrated confidence.',True,'yes'),('04 · All machine gates pass?','Five HIGH ratings, threshold support, valid original and no hold.',True,'yes'),('05 · Resolve effective selection','Retain human precedence; machine admission never invents a reviewer.'),('06 · Audit + weekly source QA','Check source/file consistency. Monday sample: 5 eligible records.'),('07 · INCLUDE and current?','Only effective INCLUDE with a usable current snapshot moves on.',True,'yes')],
 [('01 · Bind the source package','Source identity + original + version + selection and acquisition state.'),('02 · Recheck current evidence','Reject changed bytes or stale eligibility before a downstream start.',True,'current'),('03 · Expose the eligible original','System2A starts only on explicit user action; opening a view does not start it.'),('04 · Publish the source register','One-way Excel snapshot of the owning saved source state.'),('05 · Reconcile output status','Saved, export-pending, synchronized and failed are separate states.'),('06 · Process downstream follow-up','Missing body or source defect returns to the existing source task.'),('07 · Preserve continuity','New source versions or loss of eligibility suspend affected downstream use.')]
])
s1.branch(0,0,'existing','Retain identity','Keep previous decisions; use the existing retrieval route.',route_to=(1,0))
s1.branch(0,2,'duplicate','Reconcile first','Keep one source identity. Resolve the proposed link or metadata.',True)
s1.branch(0,4,'no','Remain a candidate','Pending or declined admission retains its reason.',True)
s1.branch(1,2,'no','Preserve valid file','Paywall/failure: record evidence and request an authorised original.',True)
s1.branch(1,3,'same','Reuse snapshot','Record the check; avoid creating a duplicate source version.',route_to=(1,5))
s1.branch(2,2,'unknown','Human assessment','Unknown stays unknown; no invented percentage.',True)
s1.branch(2,3,'no','Keep the hold','Low score, source failure or human follow-up needs action.',True)
s1.branch(2,6,'no','Retain selection','PENDING needs review; EXCLUDE stays out of downstream intake.')
s1.branch(3,1,'stale','Refresh evidence','Reload current source and selection before retry.',True)
s1.branch(3,4,'locked','Retry the export','The decision stays saved; retain the last complete workbook.',True)
for m,t in enumerate(['OUTPUT → existing or admitted source','OUTPUT → original + acquisition evidence','OUTPUT → effective selection + current snapshot']):s1.handoff(m,t)
s1.text(4315,2490,1120,70,'OUTPUT → governed source package for explicit A intake',31,'s1',600)
s1.human([('1 · One source task','Consolidate candidate, access, URL, original and QA issues.'),('2 · Inspect evidence','See the exact decision, reason, original and prior history.'),('3 · Correct / supplement','Rate the source, correct metadata or supply an authorised file.'),('4 · Check current version','A stale or incomplete request remains a draft or pending.'),('5 · Save named decision','Apply once, retain the reason, receipt and previous decisions.'),('6 · Return to the owner','Verified correction re-enters intake, retrieval or governance.')], 'A saved URL is metadata only. A supplied original still needs checking. A source may retain other unresolved issues after one correction.')
s1.measure(0,'Admission and identity','Current source base: 87 identities; new-candidate browser admission remains maintainer-assisted.', [('Identity / prior history','Preserved · scoped check'),('Candidate admission','Named ACCEPT required')], 'Compare source identities and named decisions before/after the controlled transition. Exercise new, duplicate and declined candidates; check that only accepted candidates obtain a formal identity.', 'No autonomous discovery provider is configured. Candidate admission and source-population completeness have no measured accuracy percentage.')
s1.measure(1,'Acquisition and preservation','Normal-load preservation and current 38-record intake are different populations.', [('Managed originals · 73 / 73','Unchanged · PASS'),('Q01 Explained states · 38 / 38','100% · PASS'),('Missing-body follow-ups · 7','Explicit · REPORT')], 'Match original fingerprints and version lineage before/after the bounded load. Reconcile all intake records to a parse outcome or a located source follow-up. Exercise failed replacement while keeping the previous valid original.', 'Stored bytes do not establish complete source content. System2A can still return an empty-body finding. No source was reacquired for this diagram.')
s1.measure(2,'Governance and weekly checks','Five source dimensions; Monday design count of five eligible source records.', [('Confidence setting · 95%','Policy, not accuracy'),('Weekly sample · 5 sources','Monitoring design'),('Calibrated source accuracy','UNMEASURED · OPEN')], 'Bind each rating and confidence to the exact source evidence and calibrated scope. Check all hard gates and human holds. Sample eligible records without duplicate stage/week batches; retain shortfalls and open findings.', 'Weekly agreement is reported only for complete reviewed batches. It is not calibration or complete source-coverage evidence.')
s1.measure(3,'Durable handoff and outputs','Checkpoint 15 preserves all five owning business/history stores and normal source revision 1.', [('Business/history preservation','Unchanged · scoped PASS'),('Saved / source Excel revision','1 / 1 · recorded'),('Source-review human time','UNMEASURED · OPEN')], 'Compare owning business tables and originals before/after the controlled action. Check source-version guards and saved/exported revision equality. Review stale requests, failed exports and downstream eligibility loss separately.', 'The source package is not an extracted Requirement dataset. No Source1 timing is inferred from the separate System2 performance cohort.')

a=Board('system2a','System2A | Recover, verify and repair the original','Detailed flow: admit a current source → preserve every content type → inspect the original against the result → repair and recheck → unlock only accepted content for B.','a',[
 ('Intake & format routing','Make scope and recoverable failures explicit'),('Content reconstruction','Retain full source units, tables and context'),('Original-side verification','Inspect omissions as well as existing output'),('Proofreading & A delivery','Correct the effective view; preserve original facts')])
fill(a,[
 [('01 · Explicitly start a source','Consume the current System1 INCLUDE decision and selected original.'),('02 · Original and version valid?','Check identity, content fingerprint and current eligibility.',True,'yes'),('03 · Determine the real format','PDF, supported HTML and XLSX use distinct structural routes.'),('04 · Scan original structure','PDF: page zones, columns, repeated headers/footers, native vs scanned text.'),('05 · Retain extraction evidence','Native text + page images + OCR for scanned text; retain source regions.'),('06 · Complete supported body?','An empty body or an unhandled source condition stays explicit.',True,'yes'),('07 · Process a bounded scope','Record completed and unfinished scope; preserve checkpoints and old runs.')],
 [('01 · Recover source blocks','Detect headings, paragraphs, lists, tables, figures and auxiliary content.'),('02 · Resolve text evidence','Compare native/OCR readings; retain alternatives and unresolved conflicts.'),('03 · Rebuild hierarchy + order','Combine numbering, indentation and page geometry; preserve source boundaries.'),('04 · Join cross-page text','Check adjacent pages, parent scope, alignment and sentence/list continuity.',True,'eligible'),('05 · Rebuild physical tables','Recover cells, rows, columns, headers, merged spans and original fragments.'),('06 · Assemble cross-page tables','Compare columns/headers; deduplicate repeated headers and join valid row fragments.',True,'eligible'),('07 · Bind context and retain facts','Link titles, notes, captions and source segments to the complete logical content.')],
 [('01 · Start from the original','Survey the declared source regions, including regions with no output.'),('02 · Compare text + key tokens','Locate omitted/changed text, numbers, units and controlling expressions.'),('03 · Check structure + order','Compare headings, boundary types, reading order and source coverage.'),('04 · Check cells + relationships','Check row/column/span ownership and title, note and continuation links.'),('05 · Record located findings','Bind differences to original/result regions, severity and evidence.'),('06 · All four A dimensions valid?','Text, coverage, structure and order each need supported confidence.',True,'yes'),('07 · No open blocker or draft?','Current source and dependencies must also pass; otherwise keep pending.',True,'yes')],
 [('01 · Open Content proofreading','Original on the left; current content, finding and context on the right.'),('02 · Choose the exact repair','Text, missing content, source boundary, table cell or typed relationship.'),('03 · Bind repair to source evidence','Preserve the source location and explain what the correction resolves.'),('04 · Save a versioned correction','Update the effective view; keep originals, prior facts and named history.'),('05 · Recheck affected evidence','Old checks become stale; rerun the relevant comparison and dependencies.'),('06 · Content and coverage accepted?','Explicit human acceptance or qualified machine route; other holds remain.',True,'yes'),('07 · Expose accepted A scope to B','Only current accepted content with valid context can unlock Requirement judgment.')]
])
a.branch(0,1,'no','Source follow-up','Return identity, stale-original or access problems to System1.',True)
a.branch(0,2,'HTML / XLSX','Native structure','HTML: sections/tables. XLSX: cells/merges. Keep original order.')
a.branch(0,3,'templates','Preserve roles','Distinguish body from repeated furniture; keep both traceable.')
a.branch(0,4,'unsupported','Controlled copy','Only unsupported formats may use a verified parsing copy.',True)
a.branch(0,5,'no','Keep failure visible','A supported-format failure cannot be accepted through conversion.',True)
a.branch(1,1,'conflict','Retain alternatives','Unresolved high-risk text conflict enters Content proofreading.',True)
a.branch(1,2,'new boundary','Keep separate','New heading/list item blocks a guessed continuation.')
a.branch(1,3,'uncertain','Review the join','Keep both page regions; confirm text order and hyphen handling.',True)
a.branch(1,4,'whole table','Retain fragments','Keep page images, physical cells and repeated headers.')
a.branch(1,5,'uncertain','Review assembly','Check column alignment, row continuity, notes and all fragments.',True)
a.branch(1,6,'figures','Preserve evidence','Keep full images/captions. Scanned body still needs transcription.')
a.branch(2,0,'no output','Missing region','A broad output box does not prove the region was recovered.')
a.branch(2,4,'unverified','Declare the gap','A generic alarm is not a specifically located error.',True)
a.branch(2,5,'no','No auto-pass','Unknown calibration, weak evidence or conflict keeps A pending.',True)
a.branch(2,6,'blocked','Keep the hold','Unfinished context, human follow-up or draft blocks affected use.',True)
a.branch(3,3,'stale','Compare before retry','Retain the draft; reload current original/content and dependencies.',True)
a.branch(3,4,'still wrong','Continue repair','Save/recheck does not automatically clear unrelated findings.',True)
a.branch(3,5,'no','Remain in A','B stays blocked for this scope; accepted unrelated scope is retained.',True)
for m,t in enumerate(['OUTPUT → declared source scope + retained evidence','OUTPUT → complete structured source content','OUTPUT → findings + current acceptance evidence']):a.handoff(m,t)
a.text(4315,2490,1120,70,'OUTPUT → current accepted content, context and provenance',31,'a',600)
a.human([('1 · Locate the issue','Use bound original regions, full-table context and the stated reason.'),('2 · Inspect the scope','Check surrounding text, headers, notes and dependencies.'),('3 · Correct or supplement','Keep every addition and structural repair anchored to the original.'),('4 · Save with a receipt','Named decisions are durable; a saved draft is incomplete.'),('5 · Revalidate the change','Refresh affected checks and suspend dependent B results.'),('6 · Reopen or complete A','Unresolved issues remain pending; history keeps the old version.')], 'Source problems return to System1. A repairs preserve source meaning; deciding which content is a Requirement belongs to B.')
a.measure(0,'Format and coverage scope','31 readable materials out of 38 records. Fidelity diagnosis: one PDF, 8 exposed pages and 275 original regions.', [('Q02 Readable parsed · 31 / 31','≥95% · PASS'),('Q03 Complete regions · 64 / 275','≥99% · FAIL'),('Q36 Real scan / mixed quality','UNMEASURED · OPEN')], 'Reconcile every input with a declared outcome. Compare all reference regions, including absent output. Count a complete region only when content, structure and controlling relations agree. Evaluate real scans/mixed pages as a separate representative cohort.', '31/31 parsing completion is not source-fidelity acceptance. The scan repair fixture is synthetic and does not qualify real scan accuracy.')
a.measure(1,'Reconstruction and cross-page joins','Parser 04: 125 cells, 12 relations and 3 whole tables. Implemented joins still require independent qualification.', [('Q07/08 Text / grid · 123/125; 125/125','≥98% each · PASS'),('Q10/12 Relations / tables · 0/12; 0/3','FAIL / diagnostic FAIL'),('Exact cross-page join precision / recall','UNMEASURED · OPEN')], 'Match exact cells, spans and expected relationships. For text/table joins, label exact fragment pairs: precision = correct/predicted joins; recall = correct/required joins. Check wrong joins, missed joins, repeated headers and row completeness. Proposed criterion: ≥98% each; retain fragment evidence.', 'Join code and physical fragments do not prove correct assembly. Q04 CER 0.13%; Q05 WER 0.90% report only; Q06 tokens 211/211; Q09 order 20/20; Q11 pages 0/8. Broad diagnostic scores cannot replace exact join labels.')
a.measure(2,'Verifier reliability','Verifier 6, natural original-first diagnosis. Injected errors and unmodified controls form a separate paired challenge.', [('Q19 Natural recall · 8 / 29','≥90% · FAIL'),('Q20 Critical located · 7 / 11','all · FAIL'),('Q21 Finding precision · 8 / 33','≥80% · FAIL')], 'Natural recall = specifically located true findings / all adjudicated natural defects. Precision = actionable true findings / actionable prompts. Q22 injected defects: 12/12 detected; Q23 control false alarms: 0/12, meeting the ≤1-control criterion.', 'Never combine natural and injected populations. Independently callable checking does not establish independent accuracy; Q35 held-out qualification remains open.')
a.measure(3,'Repair, acceptance and monitoring','A release cohort: 8 pages. Shared candidate-08 operations: full 38-document copied workload.', [('Q24 Safe automatic A release · 0 / 8','≥10% · FAIL'),('Q31 Save p95 · 0.658 s; n=10','≤2 s · PASS'),('Weekly A design · 20 original units','Normal activation OFF')], 'Count only evidence-qualified automatic releases over the 8-page cohort. Time persistent saves and take nearest-rank p95. Weekly QA samples original-side units, including absent output; a repair requires a separate finding follow-up before closure.', 'A partial delivery is not whole-source completion. Original/content/policy changes reopen affected scope. Actual reviewer effort remains Q28 UNMEASURED.')

b=Board('system2b','System2B | Identify, relate and deliver Requirements','Detailed flow: classify checked source content → judge meaning with full context → optionally retain linked subitems → apply current acceptance and counting rules → deliver a versioned result.','b',[
 ('Source-grounded proposal','Current local classifier order, not automatic acceptance'),('Context & human judgment','Retain supporting content and inspect every class'),('Optional parent / subitems','Provisional subdivision, independent of A boundaries'),('Acceptance & delivery','Current evidence, consistent counts and retained history')])
fill(b,[
 [('01 · A source and context accepted?','Require current complete text, structure, coverage and dependencies.',True,'yes'),('02 · Coverage or assembly view?','A coverage checklist / table assembly is context, not a duplicate obligation.',True,'no'),('03 · Operative wording present?','Normative or advisory wording proposes a Requirement; role still needs review.',True,'no'),('04 · Applicability / exemption rule?','Retain the full controlling clause and its scope as a Requirement candidate.',True,'no'),('05 · Numbered standard item?','A principle / indicator can propose a Requirement, subject to its actual role.',True,'no'),('06 · Definition, heading or support?','A modal definition, non-operative heading, citation or support contact is context.',True,'no'),('07 · No conclusive local evidence','Return UNDETERMINED with the matched evidence and a concise reason.')],
 [('01 · Bring proposals together','Requirement, context and undetermined proposals all keep source evidence.'),('02 · Attach original context','Full parent, numbering, definitions, headings, notes and table relationships.'),('03 · Check source association','Confirm that conditions and references belong to this statement and version.'),('04 · Check three B dimensions','Classification, association and subdivision need supported evidence/confidence.'),('05 · Review the proposed meaning','A human can select Requirement, context, non-Requirement or undetermined.'),('06 · Record decision and reason','Exclusions need a reason; advisory character remains distinguishable.'),('07 · Requirement to represent?','Only a current Requirement enters optional subdivision and delivery.',True,'yes')],
 [('01 · Preserve the complete parent','Keep full accepted A content, original number, source version and context.'),('02 · Is subdivision appropriate?','Whole-table containers cannot duplicate already identified source-row items.',True,'yes'),('03 · Select exact accepted spans','Children use nonempty, non-overlapping quotations; source text stays intact.'),('04 · Inspect all remaining text','Unassigned substantive text needs an explicit explanation and whole-parent review.'),('05 · Attach shared conditions','Keep inherited context; generated labels stay separate from original numbering.'),('06 · Choose one counting basis','Count the parent once OR counted children. Never count both.'),('07 · Save a reversible B decision','Keep spans, count policy and prior revisions. Clearing needs parent classification.')],
 [('01 · Recheck all current gates','Current source, accepted A/B, valid dependencies and no unresolved draft/hold.'),('02 · Supported acceptance route?','Every needed score is calibrated, or a current named human decision applies.',True,'yes'),('03 · Compose a parent envelope','Full parent and nested subitems remain together with one declared count basis.'),('04 · Publish counted Requirements','Keep context/non-counted rows separately; partial scope stays explicit.'),('05 · Synchronize one-way Excel','Original number, generated label, parent, counted value and evidence stay distinct.'),('06 · Send versioned change events','Add/replace, suspend or withdraw the parent and its current child set.'),('07 · Monitor and reopen selectively','B QA inspects positive and negative judgments; changes retain prior history.')]
])
b.branch(0,0,'no','Return to A','Repair source content or dependencies before judging Requirements.',True)
b.branch(0,1,'yes','CONTEXT','Retain the view without counting it as an obligation.')
b.branch(0,2,'yes','REQUIREMENT','Candidate only. Advisory wording is included.')
b.branch(0,3,'yes','REQUIREMENT','Preserve the applicability / exemption clause.')
b.branch(0,4,'yes','REQUIREMENT','Numbering alone does not establish an obligation.')
b.branch(0,5,'yes','CONTEXT','Retain complete located supporting evidence.')
# Classified branches join the next module directly; unknowns arrive from the main bottom handoff.
for r in range(1,6):
    lane=1447;b.wire([(COL[0]+1190,Y[r]+96),(lane,Y[r]+96),(lane,Y[0]+80),(COL[1]+40,Y[0]+80)])
b.branch(1,2,'conflict','Resolve association','A damaged/missing source relationship returns to A.',True)
b.branch(1,3,'unknown','Human judgment','Do not reuse confidence for a different proposal or source version.',True)
b.branch(1,5,'existing split','Keep prior subitems','An ordinary class change cannot silently discard a subdivision.',True)
b.branch(1,6,'no','Retain other classes','Context/excluded/unknown content stays traceable, outside delivery.')
b.branch(2,1,'no','Keep parent intact','No split is valid. Retain context and choose parent-only representation.',route_to=(2,5))
b.branch(2,2,'invalid','Correct the spans','Reject overlap, empty text or a quotation that does not match.',True)
b.branch(2,3,'unexplained','Incomplete decision','A keyword-free remainder is not automatically non-Requirement.',True)
b.branch(2,5,'provisional','Peer decision open','Final granularity, delivery and counting await collaborator agreement.')
b.branch(3,0,'changed','Suspend affected use','Changed A/context makes old B and its children stale.',True)
b.branch(3,1,'no','Keep B pending','A saved draft or unsupported score cannot release a result.',True)
b.branch(3,4,'failed','Retry output only','The decision remains saved; preserve the last complete workbook.',True)
b.branch(3,5,'future','System3 interface','Consumer not connected. Semantic enrichment remains future.')
for m,t in enumerate(['OUTPUT → proposal + source-cited reason, not acceptance','OUTPUT → accepted classification + complete associated context','OUTPUT → full parent + optional source-bound subitems']):b.handoff(m,t)
b.text(4315,2490,1120,70,'OUTPUT → current counted Requirements + context + change history',31,'b',600)
b.human([('1 · Open Requirement judgment','See the proposal, reason, accepted original and complete context.'),('2 · Decide the class','Requirement / context / non-Requirement / undetermined.'),('3 · Review parent / children','Confirm exact spans, shared conditions and one count basis.'),('4 · Save current evidence','Reject stale submissions; retain incomplete drafts separately.'),('5 · Recheck B after change','A/context changes never silently revive an earlier B decision.'),('6 · Close only resolved work','QA findings need explicit verification after a corrected judgment.')], 'B does not invent missing actors, thresholds or ontology fields. Site-specific grounding and final compliance judgment belong to future collaboration.')
b.measure(0,'Classifier quality and abstention','Classifier 5: initial 60 complete units, 41 positive (11 advisory), 19 negative. Extra negative is separate.', [('Q13 Precision · 41 / 41','≥95% · PASS'),('Q14/15 Recall / advisory · 41/41; 11/11','≥90% each · PASS'),('Q16 Decisive judgments · 53 / 60','≥90% · FAIL')], 'Compare proposals with frozen reference classes. Precision = TP/(TP+FP); recall = TP/all reference positives, including abstained positives. Decisiveness = non-abstained/all units. The separate extra negative is correct; combined decisive count is 54/61.', 'The seven initial abstentions are negatives. These controlled source-complete inputs do not prove acceptance of production A or calibrated release.')
b.measure(1,'Association and human review','Original association and human decisions use current source, content and dependency evidence.', [('Classification / association / split','Each needs support'),('Q28 Real reviewer outcomes / minutes','UNMEASURED · OPEN'),('Q30 Cached preview p95 · 0.763 s; n=20','≤2 s · PASS')], 'Trace each judgment to the complete accepted source and context; inspect false inclusion and omission. Group overlapping source scopes into independent reviewer tasks, time active work and record confirmation/correction/unresolved outcomes. UI p95 uses ranked request durations.', 'Fast evidence access is not reduced reviewer effort. Absence of a keyword is not a valid exclusion; ambiguity stays visible.')
b.measure(2,'Subdivision mechanics and binding','10 real parents and 55 manually selected spans. Accepted-A production delivery remains separate.', [('Q17 Bound spans · 55 / 55','All bindings · scoped PASS'),('Changed-context invalidation · 10 / 10','All affected · PASS'),('Q18 Accepted-A subdivision delivery','UNMEASURED · OPEN')], 'Match exact selected quotations and parent/source bindings; reject overlap and unexplained remainder. Change context and check that children become stale. Then test delivery from actually accepted A under each reversible parent-or-children policy.', 'All ten real B submissions remain blocked by unaccepted A. Valid bindings do not establish automatic semantic split accuracy or peer agreement.')
b.measure(3,'Release, coherent output and QA','B: 61 judgments; end-to-end: one source. Current candidate-08 export timing supplement.', [('Q25/26 Safe B / end-to-end · 0/61; 0/1','≥10% each · FAIL'),('Q32–34 Exports · 13.38 / 13.80 / 15.42 s','≤60 s each · PASS'),('Weekly B design · 3 positive + 2 negative','Normal activation OFF')], 'Count qualified releases over their distinct populations; automatic-pass correctness has no sample at zero releases. Match saved/exported versions and count parent or children once. Weekly sampling keeps shortfalls and missing classes explicit, with separate repair follow-up.', 'Q35 independent held-out qualification, Q37 live API benefit and Q38 remaining native Excel QA stay OPEN. System3 has no consumer acceptance.')

boards=[s1,a,b];layouts=[]
for obj in boards:
    _,layout=obj.finish('This is a workflow explanation. Quality values are exposed development diagnostics; manual loops, automatic accuracy and accepted delivery remain distinct.')
    layouts.append(layout)
(OUT/'layouts.json').write_text(json.dumps(layouts,indent=2))
review='''<!doctype html><html><head><meta charset="utf-8"><title>System detail canvases</title><style>*{box-sizing:border-box}html,body{margin:0;height:100%;overflow:hidden;background:#DCE4E7;font:14px Arial}nav{height:66px;background:#173042;color:white;display:flex;gap:9px;align-items:center;padding:13px 20px}button{background:#26485A;border:1px solid #6D8997;border-radius:7px;padding:10px 14px;color:white;font:14px Arial;cursor:pointer}button:hover{background:#497185}strong{margin-right:12px}#view{position:absolute;inset:66px 0 0;overflow:hidden}iframe{position:absolute;border:0;width:3920px;height:2940px;transform-origin:0 0;pointer-events:none}#zoom{margin-left:auto}</style></head><body><nav><strong>Internal system flows</strong><button onclick="load('system1')">System1</button><button onclick="load('system2a')">System2A</button><button onclick="load('system2b')">System2B</button><button onclick="fit()">Full canvas</button><button onclick="mod(0)">01</button><button onclick="mod(1)">02</button><button onclick="mod(2)">03</button><button onclick="mod(3)">04</button><button onclick="human()">Human loop</button><button onclick="metrics()">Evaluation</button><span id="zoom"></span></nav><div id="view"><iframe title="Detailed workflow" src="system1.html"></iframe></div><script>const fr=document.querySelector('iframe'),v=document.querySelector('#view');let key='system1',s=1,tx=0,ty=0;function draw(){fr.style.transform=`translate(${tx}px,${ty}px) scale(${s})`;document.querySelector('#zoom').textContent=Math.round(s*100)+'%'}function focus(x,y,w,h){s=Math.min((v.clientWidth-40)/w,(v.clientHeight-32)/h);tx=(v.clientWidth-w*s)/2-x*s;ty=(v.clientHeight-h*s)/2-y*s;draw()}function fit(){focus(0,0,3920,2940)}function load(k){key=k;fr.src=k+'.html';fit()}function mod(i){focus([100,1490,2880,4270][i]*.7-20,455*.7,1270*.7,2160*.7)}function human(){focus(90*.7,2620*.7,5420*.7,330*.7)}function metrics(){focus(90*.7,3010*.7,5420*.7,1000*.7)}let drag;v.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,tx,ty};v.setPointerCapture(e.pointerId)};v.onpointermove=e=>{if(drag){tx=drag.tx+e.clientX-drag.x;ty=drag.ty+e.clientY-drag.y;draw()}};v.onpointerup=()=>drag=null;v.onwheel=e=>{e.preventDefault();const k=Math.exp(-e.deltaY*.0015),r=v.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;tx=x-(x-tx)*k;ty=y-(y-ty)*k;s*=k;draw()};window.onresize=fit;fit();</script></body></html>'''
(OUT/'review.html').write_text(review)
print(json.dumps([{'key':b.key,'nodes':len(b.nodes),'connections':len(b.wires)} for b in boards]))
