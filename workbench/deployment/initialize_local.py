"""Create missing local configuration from versioned templates; never overwrite it."""
import json
from pathlib import Path


def initialize(root):
    folder=Path(root)/'system1/Code/config';created=[]
    for name in ('config','schedule'):
        target=folder/(name+'.json')
        if target.exists():continue
        template=folder/(name+'.example.json')
        if not template.is_file():raise ValueError('Missing configuration template: '+str(template))
        value=json.loads(template.read_text(encoding='utf-8'))
        if name=='config':
            value.setdefault('governance_db','../runtime/governance.sqlite')
            value.setdefault('random_qa',{})['enabled']=False
        else:value['enabled']=False
        try:
            with target.open('x',encoding='utf-8') as out:out.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
            created.append(str(target))
        except FileExistsError:pass
    return created

if __name__=='__main__':
    for path in initialize(Path(__file__).resolve().parents[2]):print('Created local configuration:',path)
