"""Independent raw-token text check using Python's HTMLParser, not libxml/BeautifulSoup."""
from hashlib import sha256
from html.parser import HTMLParser

VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}

class SourceTokens(HTMLParser):
    def __init__(self,profile):
        super().__init__(convert_charrefs=True)
        self.profile=profile;self.stack=[];self.parts=[];self.root_count=0
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs);parent=self.stack[-1] if self.stack else None
        is_root=(tag=='title' and parent is not None and parent[0]=='head')
        if self.profile=='lovdata':is_root=is_root or attrs.get('id') in ('documentMeta','documentBody')
        else:is_root=is_root or (tag=='main' and (self.profile=='asc' or attrs.get('id')=='main'))
        inside=is_root or bool(parent and parent[1]);ignored=tag in ('script','style') or bool(parent and parent[2])
        if is_root:self.root_count+=1
        if tag not in VOID:self.stack.append((tag,inside,ignored))
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                del self.stack[i:];return
    def handle_data(self,data):
        if self.stack and self.stack[-1][1] and not self.stack[-1][2]:self.parts.append(data)


def verify_raw_text(raw,document):
    # Normalize only HTML newline spelling; preserve spaces between inline elements.
    decoded=raw.decode(document.encoding,errors='strict').replace('\r\n','\n').replace('\r','\n')
    parser=SourceTokens(document.profile);parser.feed(decoded);parser.close()
    source_text=''.join(parser.parts)
    actual=''.join(atom.text for atom in document.atoms)
    return {'engine':'stdlib.HTMLParser','status':'passed' if source_text==actual and parser.root_count==len(document.root_node_ids) else 'failed',
            'source_text_sha256':sha256(source_text.encode()).hexdigest(),
            'canonical_text_sha256':sha256(actual.encode()).hexdigest(),
            'source_text_characters':len(source_text),'canonical_text_characters':len(actual),
            'root_count':parser.root_count}
