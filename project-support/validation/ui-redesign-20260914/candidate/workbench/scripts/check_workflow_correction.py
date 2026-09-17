"""Exercise v2 collection exchange in three independent, synthetic workspaces."""
from copy import deepcopy
import json
from check_offline_collaboration import app,uid,ROOT,ACTOR,A,B,save,take
from local_workbench.collaboration import Collaboration,fingerprint
from local_workbench.collaboration_collection import Collection
from local_workbench.collaboration_exchange import unpack,pack
from local_workbench.material_queue import MaterialQueue

name='workflow-'+uid()[:8];main=app(name);c=main.collaboration;q=MaterialQueue(c)
a=app(name+'-ana',True);b=app(name+'-daniel',True)
queue=q.listing(ACTOR,'pending');assert {m['source']['source_id'] for m in queue['materials'] if m['queue'].get('unopened') and m['source']['source_id'].startswith('TS')}=={'TS001','TS002','TS003'},queue
assert c.all('workspace')==[]
m=c.material_action(ACTOR,'open',{'source_id':'TS001','request_id':uid()});mid=m['id'];assert not m['blocks']
c.material_action(ACTOR,'extract',{'material_id':mid,'expected_revision':m['revision'],'request_id':uid()});c.tick()
m=c.read_material(ACTOR,mid);candidate=next(x for x in m['candidates'] if x['status']=='ready');raw=c.personal_adapter(ACTOR,mid).call('material_candidate',material_id=mid,candidate_id=candidate['id'])
blocks=deepcopy(raw['blocks']);index=next(i for i,v in enumerate(blocks) if v['type']=='text');blocks[index]['text']='Synthetic human correction'
r=c.material_action(ACTOR,'candidate-draft',{'material_id':mid,'expected_revision':m['revision'],'request_id':uid(),'candidate_id':candidate['id'],'blocks':blocks,'issues':[]})
assert r['status']=='applied' and not r['material']['confirmation']
take(c,c.prepare_own(ACTOR,{'source_id':'TS001','material_id':mid}));m=c.read_material(ACTOR,mid,view='master')
c.confirm_master(ACTOR,{'material_id':mid,'expected_revision':m['revision'],'request_id':uid(),'explicit_confirmation':True,'checked_scope':[s['id'] for s in m['scope']],'association_reviewed':True,'omissions_checked':True,'dependencies_checked':True})
archive=q.read_archive(ACTOR,mid);scope=[archive['scope'][0]['id']]
t=q.create(ACTOR,{'material_id':mid,'archive_revision':archive['revision'],'scope':scope,'assignee':A,'reason':'Synthetic offline scope check','request_id':uid()})['inspection']
work,filename=Collection(c).export(ACTOR,{'request_id':uid(),'kind':'work','items':[{'type':'source','key':'TS001'},{'type':'source','key':'TS002'},{'type':'inspection','key':t['id']}]})
assert unpack(work)['metadata']['collection_version']==2
for app_,actor in ((a,A),(b,B)):Collection(app_.collaboration).import_collection(actor,work,unpack(work))
for app_,actor,content in ((a,A,'Ana parallel correction'),(b,B,'Daniel parallel correction')):
 material=app_.collaboration.read_material(actor,mid);edited=deepcopy(material['blocks']);edited[index]['text']=content
 app_.collaboration.material_action(actor,'save',{'material_id':mid,'expected_revision':material['revision'],'request_id':uid(),'blocks':edited,'issues':[]})
 source=app_.collaboration.source_draft(actor,'TS002');review=deepcopy(source['source_review']);review['note']='Synthetic partial review, applicability still to check.'
 app_.collaboration.save_source(actor,{'source_id':'TS002','expected_revision':0,'source_review':review})
qa=MaterialQueue(a.collaboration);check=qa.detail(A,t['id']);assert check['material']['blocks']==archive['blocks']
qa.save(A,{'task_id':t['id'],'material_id':mid,'expected_revision':0,'request_id':uid(),'action':'save','note':'Partial synthetic check','checked_scope':[]})
returned=[]
for app_,actor in ((a,A),(b,B)):
 request={'kind':'submission','request_id':uid(),'summary':'Partial offline engineering results','items':[{'type':'material','key':mid},{'type':'source','key':'TS002'}]+([{'type':'inspection','key':t['id']}] if actor==A else [])}
 col=Collection(app_.collaboration);blob,_=col.export(actor,request);assert col.export(actor,request)[0]==blob
 received=c.import_package(ACTOR,blob);assert c.import_package(ACTOR,blob)['status']=='already_imported';returned.append(received)
assert c.read_material(ACTOR,mid,view='master')['blocks']==archive['blocks']
suba=next(x for x in c.all('submission') if x['actor']==A and x.get('material_id')==mid);take(c,c.preview(ACTOR,{'submission_id':suba['id']}))
subb=next(x for x in c.all('submission') if x['actor']==B and x.get('material_id')==mid);preview=c.preview(ACTOR,{'submission_id':subb['id']});assert preview['unresolved'];take(c,preview)
item=c.all('collection_item')[0];preview=Collection(c).preview(ACTOR,{'item_id':item['id']});request={'item_id':item['id'],'request_id':uid(),'expected_current_digest':preview['current_digest'],'choice':'incoming','explicit_confirmation':True}
r=Collection(c).adopt(ACTOR,request);assert r['status']=='adopted';assert Collection(c).adopt(ACTOR,request)==r
assert q.tasks(mid)[0]['status']=='pending' and not q.tasks(mid)[0]['checked_scope']
receipt_blob,_=Collection(c).export(ACTOR,{'kind':'receipt','request_id':uid(),'items':[{'type':'receipt','key':r['id']}]})
a.collaboration.import_package(A,receipt_blob)
assert a.collaboration.all('received_adoption')[0]['receipt']['contributor']==A
assert qa.tasks(mid)[0]['note']=='Partial synthetic check'
assert q.read_archive(ACTOR,mid)['blocks']==archive['blocks']
current=c.read_material(ACTOR,mid,view='master');q.continue_work(ACTOR,{'material_id':mid,'expected_master_revision':current['revision'],'request_id':uid()})
assert any(x['id']==mid for x in q.listing(ACTOR,'pending')['materials'])
# A malformed last item must not allow earlier valid items into another workspace.
bad=unpack(work);entry=bad['metadata']['items'][-1];nested=unpack(bad['files'][entry['path']]);nested['metadata']['task']['source_hash']='changed';bad['files'][entry['path']]=pack(nested['kind'],nested['metadata'],nested['files']);corrupt=pack('collection',bad['metadata'],bad['files'])
clean=app(name+'-bad-package',True).collaboration
try:clean.import_package(A,corrupt);raise AssertionError('Corrupt collection accepted')
except ValueError:pass
assert not clean.all('work') and not clean.all('package_receipt')
result={'status':'PASS','coordinator_root':str(main.root),'reviewer_roots':[str(a.root),str(b.root)],'material_id':mid,'checks':['unstarted HTML/PDF/Excel listed without drafts','editable first candidate remains unreviewed','immutable multi-item exports','two independent reviewers','same paragraph conflict','partial source and inspection results retain pending state','re-import idempotency','archive preserved after subsequent adoption','continue editing returns pending','whole collection validation before imports'],'windows':'PENDING: actual office device not exercised'}
report=ROOT/'project-support/reports/offline-collaboration-20260912/workflow-correction.json';report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
