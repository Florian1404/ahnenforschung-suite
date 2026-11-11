import copy, re, calendar
from fastapi import HTTPException
from .models import Record, Proposal
from sqlalchemy import select

FIELDS={'namen.geburtsname','anzeigename','geschlecht','lebensstatus','biografie','geburt.datum.iso','geburt.ort_original','tod.datum.iso','tod.ort_original','taufe.datum.iso','taufe.ort_original','bestattung.datum.iso','bestattung.ort_original'}
def getpath(data,path):
    for key in path.split('.'):
        if not isinstance(data,dict): return None
        data=data.get(key)
    return data

def datevalue(value):
    if value is None or value=='': return None
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}(?:-\d{2})?(?:-\d{2})?',value): raise HTTPException(422,'Datum als JJJJ, JJJJ-MM oder JJJJ-MM-TT eingeben.')
    parts=list(map(int,value.split('-')))
    if not 1<=parts[0]<=9999: raise HTTPException(422,'Ungültiges Jahr.')
    if len(parts)>1 and not 1<=parts[1]<=12: raise HTTPException(422,'Ungültiger Monat.')
    if len(parts)>2 and not 1<=parts[2]<=calendar.monthrange(*parts[:2])[1]: raise HTTPException(422,'Ungültiger Tag.')
    return value

def setpath(data,path,value):
    keys=path.split('.');node=data
    for k in keys[:-1]: node=node.setdefault(k,{})
    old=node.get(keys[-1]);node[keys[-1]]=value
    if path.endswith('.datum.iso'):
        parts=list(map(int,value.split('-'))) if value else []
        node.update(jahr=parts[0] if parts else None,monat=parts[1] if len(parts)>1 else None,tag=parts[2] if len(parts)>2 else None,qualifizierer='exakt' if len(parts)==3 else 'teilweise' if parts else 'unbekannt',original=value,konflikt=False)
    return old

def validate(kind,payload):
    if kind=='patch':
        if not isinstance(payload.get('changes'),dict) or not payload['changes']: raise HTTPException(422,'Keine Änderungen.')
        for path,value in payload['changes'].items():
            if path not in FIELDS: raise HTTPException(422,'Feld nicht bearbeitbar: '+path)
            if path.endswith('.datum.iso'): datevalue(value)
            elif value is not None and (not isinstance(value,str) or len(value)>20000): raise HTTPException(422,'Ungültiger Feldwert.')
            if path=='anzeigename' and not (value or '').strip(): raise HTTPException(422,'Name fehlt.')
            if path=='namen.geburtsname' and value is not None and len(value)>200: raise HTTPException(422,'Geburtsname ist zu lang.')
            if path=='geschlecht' and value not in ('m','w','divers','unbekannt'): raise HTTPException(422,'Ungültiges Geschlecht.')
    elif kind=='person':
        if not isinstance(payload.get('anzeigename'),str) or not payload['anzeigename'].strip() or len(payload['anzeigename'])>200: raise HTTPException(422,'Neue Personen brauchen einen Namen oder eine vorläufige Bezeichnung.')
        for event in ['geburt','tod']:
            value=payload.get(event,{}).get('datum',{}).get('iso');datevalue(value)
    elif kind=='relationship':
        if payload.get('typ') not in ('eltern_kind','partner') or not payload.get('von_person_id') or not payload.get('zu_person_id'): raise HTTPException(422,'Beziehung unvollständig.')
        if payload['von_person_id']==payload['zu_person_id']: raise HTTPException(422,'Person kann nicht mit sich selbst verbunden sein.')
        if payload.get('elternschaft_typ','ungeklaert') not in ('ungeklaert','biologisch','adoptiv','pflege','stief','elternteil_aus_diagramm'): raise HTTPException(422,'Ungültige Elternschaft.')
    elif kind=='media':
        if not payload.get('person_ids') or not (payload.get('titel') or '').strip(): raise HTTPException(422,'Bild braucht einen Titel und mindestens eine benannte Person.')
    else: raise HTTPException(422,'Unbekannter Vorschlagstyp.')

def ensure_relationship(db,payload):
    a,b=payload['von_person_id'],payload['zu_person_id']
    for ident in [a,b]:
        r=db.get(Record,ident)
        if not r or r.kind!='person': raise HTTPException(409,'Beide Personen müssen zuerst freigegeben werden.')
    rows=list(db.scalars(select(Record).where(Record.kind=='relationship')))
    for r in rows:
        x=r.data
        if x.get('typ')==payload['typ'] and (x.get('von_person_id'),x.get('zu_person_id'))==(a,b): raise HTTPException(409,'Verbindung existiert bereits.')
    if payload['typ']=='eltern_kind':
        children={}
        for r in rows:
            if r.data.get('typ')=='eltern_kind': children.setdefault(r.data['von_person_id'],[]).append(r.data['zu_person_id'])
        stack=[b];seen=set()
        while stack:
            x=stack.pop()
            if x==a: raise HTTPException(409,'Diese Verbindung würde einen Abstammungskreis erzeugen.')
            if x not in seen: seen.add(x);stack.extend(children.get(x,[]))

def public_person(r):
    p=r.data
    return {'namen':{'familienname':getpath(p,'namen.familienname'),'geburtsname':getpath(p,'namen.geburtsname')},'id':r.id,'anzeigename':p.get('anzeigename'),'geschlecht':p.get('geschlecht'),'geburt':{'datum':{'iso':getpath(p,'geburt.datum.iso')},'ort_original':getpath(p,'geburt.ort_original')},'tod':{'datum':{'iso':getpath(p,'tod.datum.iso')},'ort_original':getpath(p,'tod.ort_original')},'generation_in_vorlage':p.get('generation_in_vorlage'),'version':r.version}
