"""Generate editable diagrams.net XML and renderable Graphviz source from the schema."""
from pathlib import Path
from xml.etree.ElementTree import Element,SubElement,ElementTree
import html
ROOT=Path(__file__).resolve().parents[1]
tables={
 'users':(40,70,['id : uuid [PK]','username : text [UNIQUE]','email : text [UNIQUE]','phone : text [UNIQUE, nullable]','full_name : text','password_hash : text (Argon2id)','created_at : timestamptz']),
 'account_holders':(420,80,['user_id : uuid [PK, FK → users]','account_id : uuid [PK, FK → accounts]','joined_at : timestamptz']),
 'banks':(820,80,['id : uuid [PK]','routing_number : text [UNIQUE]','name : text']),
 'bank_accounts':(800,330,['id : uuid [PK]','bank_id : uuid [FK → banks]','account_number : text','account_type : checking | savings','label : text','balance_cents : bigint ≥ 0','opening_balance_cents : bigint ≥ 0','active : boolean','created_at : timestamptz','UNIQUE(bank_id, account_number)']),
 'transfers':(250,390,['id : uuid [PK]','initiated_by : uuid [FK → users]','source_account_id : uuid [FK → accounts]','destination_account_id : uuid [FK → accounts]','amount_cents : bigint > 0','memo : text (≤ 140)','idempotency_key : uuid','created_at : timestamptz','UNIQUE(initiated_by, idempotency_key)'])}
edges=[('users','account_holders','1 : 0..N · ownership'),('bank_accounts','account_holders','1 : 1..N · holders*'),('banks','bank_accounts','1 : 0..N · bank'),('users','transfers','1 : 0..N · initiator'),('bank_accounts','transfers','1 : 0..N · source'),('bank_accounts','transfers','1 : 0..N · destination')]
file=Element('mxfile',host='app.diagrams.net',version='24.7.17')
diagram=SubElement(file,'diagram',name='PayLink ER Model',id='paylink-er')
model=SubElement(diagram,'mxGraphModel',dx='1250',dy='900',grid='1',gridSize='10',page='1',pageScale='1',pageWidth='1250',pageHeight='900')
root=SubElement(model,'root');SubElement(root,'mxCell',id='0');SubElement(root,'mxCell',id='1',parent='0')
for name,(x,y,attrs) in tables.items():
 cell=SubElement(root,'mxCell',id=name,value='<b>'+name.upper()+'</b><hr>'+'<br>'.join(html.escape(a) for a in attrs),style='rounded=1;whiteSpace=wrap;html=1;fillColor=#F3F6FC;strokeColor=#A9BDDD;fontColor=#20384A;align=left;verticalAlign=top;spacing=16;fontSize=12;',vertex='1',parent='1')
 SubElement(cell,'mxGeometry',x=str(x),y=str(y),width='335',height=str(65+len(attrs)*24),attrib={'as':'geometry'})
for i,(source,target,label) in enumerate(edges):
 cell=SubElement(root,'mxCell',id='edge'+str(i),value=label,style='edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=ERmany;startArrow=ERone;fontSize=11;fontColor=#486487;strokeColor=#7F99BC;labelBackgroundColor=#FFFFFF;',edge='1',parent='1',source=source,target=target)
 SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
cell=SubElement(root,'mxCell',id='note',value='PayLink · CS 5600 · Logical ER model\nUSD only · Five base relations\n* At least one holder is guaranteed by open_account; no deferred SQL assertion.\nSolid relationships are FKs. Source ownership is checked by the transfer function.',style='text;whiteSpace=wrap;html=0;align=left;fontSize=13;fontColor=#617A92;',vertex='1',parent='1')
SubElement(cell,'mxGeometry',x='40',y='770',width='1130',height='100',attrib={'as':'geometry'})
ElementTree(file).write(ROOT/'docs/er-diagram.drawio',encoding='utf-8',xml_declaration=True)
lines=['digraph PayLink {','graph [rankdir=LR, bgcolor="#FFFFFF", pad="0.4", nodesep="0.7", ranksep="1.3", fontname="Helvetica"];','label="PayLink logical ER model | Five base relations | USD simulation\\n* Minimum one holder is enforced by account-opening workflows, not SQL FKs."; labelloc=b; fontsize=12;', 'node [shape=plain,fontname="Helvetica"];','edge [color="#8DA6CA",fontname="Helvetica",fontsize=10,arrowsize=.7];']
for name,(_,_,attrs) in tables.items():
 rows='<TR><TD ALIGN="LEFT" BGCOLOR="#EAF0FC"><B>'+name.upper()+'</B></TD></TR>'
 rows+=''.join('<TR><TD ALIGN="LEFT">'+html.escape(a)+'</TD></TR>' for a in attrs)
 lines.append(f'{name} [label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="9" BGCOLOR="#F7F9FC">{rows}</TABLE>>];')
for source,target,label in edges:lines.append(f'{source} -> {target} [label="{label}"];')
lines.append('}')
(ROOT/'docs/er-diagram.dot').write_text('\n'.join(lines))
print('Editable drawio and Graphviz sources generated.')
