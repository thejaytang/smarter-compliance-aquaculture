"""Independent labeled evaluation of a fixed scoring method, with explicit scope."""
from collections import defaultdict
from hashlib import sha256
import json
import math


def calibrate(rows, *, method, scope, prediction_hash):
    """Wilson lower bounds, not an LLM's self-reported certainty.

    Rows must be frozen before calibration and independently labeled. Callers
    own sample provenance; the resulting artifact is not automatically activated.
    """
    groups = defaultdict(list)
    identities = set()
    for row in rows:
        if row['id'] in identities or row.get('split') != 'calibration' or row.get('label_origin') != 'independent_human':
            raise ValueError('independent_unique_calibration_labels_required')
        identities.add(row['id'])
        score = row['score']
        if type(score) not in (int,float) or not math.isfinite(score) or not 0 <= score <= 1 or type(row['correct']) is not bool:
            raise ValueError('invalid_calibration_observation')
        groups[min(19,int(score*20))].append(row['correct'])
    if not rows or not method or not scope or len(prediction_hash) != 64:
        raise ValueError('frozen_prediction_and_scope_required')
    buckets = []
    for bucket, outcomes in sorted(groups.items()):
        n=len(outcomes);p=sum(outcomes)/n;z=1.96
        lower=(p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n)
        buckets.append({'bin':bucket,'n':n,'correct':sum(outcomes),'confidence':max(0,lower)})
    artifact={'schema_version':'calibration/1','method':method,'scope':scope,'prediction_sha256':prediction_hash,
              'labels_sha256':sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),'bins':buckets}
    artifact['version']=sha256(json.dumps(artifact,sort_keys=True).encode()).hexdigest()
    return artifact


def calibrated_score(artifact, score, method, scope):
    if artifact['method'] != method or artifact['scope'] != scope:
        return None
    match=next((b for b in artifact['bins'] if b['bin']==min(19,int(score*20))),None)
    return match['confidence'] if match else None


def apply_calibrated_rules(units, source, config_root):
    """Activate only scoped, frozen, source-bound predictions from validated rules.

    No configuration is the safe offline default. Independent calibration and
    prediction files are supplied by the evaluation owner, never by a model reply.
    """
    from pathlib import Path
    from ..contracts.hashing import digest
    from ..domains.requirements.classification import propose, VERSION
    from .acceptance import ASPECTS
    root=Path(config_root).resolve();path=root/'scoring-rules.local.json'
    if not path.is_file():return
    config=json.loads(path.read_text())
    language=config.get('source_languages',{}).get(source.content_hash)
    if not language:return
    rules=config.get('rules',[])
    for unit in units:
        for stage, aspects in ASPECTS.items():
            parts=[]
            for aspect in aspects:
                evidence=unit['original']['references']
                part={'confidence':None,'calibration_version':None,'evidence':evidence,
                      'aspect':aspect,'method':'no_validated_rule'}
                candidates=[r for r in rules if r.get('source_sha256')==source.content_hash
                    and r.get('original_sha256')==digest(unit['original']) and r.get('unit_id')==unit['id']
                    and r.get('stage')==stage and r.get('aspect')==aspect]
                if len(candidates)==1:
                    r=candidates[0];artifact_path=(root/r['calibration_path']).resolve()
                    if not artifact_path.is_relative_to(root):raise ValueError('calibration_outside_configuration')
                    artifact=json.loads(artifact_path.read_text())
                    unsigned={k:v for k,v in artifact.items() if k!='version'}
                    if sha256(json.dumps(unsigned,sort_keys=True).encode()).hexdigest()!=artifact['version']:
                        raise ValueError('calibration_artifact_changed')
                    scope={'format':source.file_format,'language':language,'stage':stage,'aspect':aspect}
                    if stage=='requirement':
                        expected=digest(propose(dict(unit['original'],kind=unit['kind'])))
                        if r.get('method')!=VERSION or r.get('proposal_sha256')!=expected:
                            parts.append(part);continue
                    score=calibrated_score(artifact,r['score'],r['method'],scope)
                    if score is not None:
                        part.update(confidence=score,calibration_version=artifact['version'],method=r['method'],
                                    raw_score=r['score'],calibration_scope=scope)
                        if stage=='requirement':
                            from .requirement_scores import binding
                            part['rule_binding']=binding(unit,propose(dict(unit['original'],kind=unit['kind'])))
                parts.append(part)
            unit[stage+'_parts']=parts
