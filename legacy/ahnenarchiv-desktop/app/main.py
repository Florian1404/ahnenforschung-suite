import os,json,copy,secrets,time,io,shutil,threading
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import FileResponse,JSONResponse,RedirectResponse
from sqlalchemy import select,delete
from sqlalchemy.exc import IntegrityError
from PIL import Image
from .models import database,Record,User,Login,Proposal,Audit,Share,Setting,Outbox,uid,now
from .security import digest,hash_password,verify,login_token,current,admin
from .domain import validate,getpath,setpath,ensure_relationship,public_person

ROOT=Path(__file__).resolve().parent.parent
MAX_UPLOAD=8*1024*1024

def create_app(url=None,data_dir=None,desktop=False):
    storage=Path(data_dir or os.getenv('DATA_DIR',ROOT/'data'));storage.mkdir(parents=True,exist_ok=True)
    media_dir=storage/'media';media_dir.mkdir(exist_ok=True)
    engine,Sessions=database(url or os.getenv('DATABASE_URL','sqlite:///'+str(storage/'archive.sqlite')))
    lock=threading.RLock();attempts={}
    app=FastAPI(title='Ahnenarchiv',docs_url=None,redoc_url=None)
    app.state.sessions=Sessions;app.state.engine=engine;app.state.media_dir=media_dir;app.state.desktop=desktop;app.state.storage=storage;app.state.lock=lock
    app.state.local_secret=secrets.token_urlsafe(40)
    app.state.sync_status={'message':'Noch nicht verbunden','last_sync':None}

    @app.middleware('http')
    async def protection(request,call_next):
        origin=request.headers.get('origin')
        if request.method not in ('GET','HEAD','OPTIONS'):
            if origin and origin!=str(request.base_url).rstrip('/'):
                return JSONResponse({'detail':'Ungültiger Ursprung.'},status_code=403)
            if request.headers.get('content-length','0').isdigit() and int(request.headers.get('content-length','0'))>MAX_UPLOAD+65536:
                return JSONResponse({'detail':'Datei zu groß (maximal 8 MB).'},status_code=413)
        if desktop and request.headers.get('host') not in getattr(app.state,'allowed_hosts',{'127.0.0.1','localhost','testserver'}):
            return JSONResponse({'detail':'Host nicht erlaubt'},status_code=403)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='no-referrer';response.headers['Cache-Control']='no-store'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        return response

    def who(db,request): return current(db,request)
    def userjson(u): return {'id':u.id,'name':u.name,'email':u.email,'role':u.role,'active':u.active}
    def propjson(p): return {k:getattr(p,k) for k in ['id','actor','kind','target','base_version','payload','source','status','created','reviewer','reason']}
    def recordjson(r): return dict(r.data,id=r.id,version=r.version)
    def throttled(request):
        key=request.client.host if request.client else 'unknown';stamp=time.time();values=[v for v in attempts.get(key,[]) if v>stamp-300]
        if len(values)>=20: raise HTTPException(429,'Bitte in fünf Minuten erneut versuchen.')
        values.append(stamp);attempts[key]=values
        if len(attempts)>10000: attempts.clear()
    async def body(request):
        raw=await request.body()
        if len(raw)>1024*1024: raise HTTPException(413,'Anfrage zu groß.')
        try:
            value=json.loads(raw)
            if not isinstance(value,dict): raise ValueError()
            return value
        except (ValueError,TypeError): raise HTTPException(422,'Ungültige JSON-Anfrage.')

    @app.get('/')
    def index(): return FileResponse(ROOT/'app/static/index.html')
    @app.get('/static/{filename}')
    def static(filename:str):
        if filename not in ['app.js','style.css']: raise HTTPException(404)
        return FileResponse(ROOT/'app/static'/filename)
    @app.get('/health')
    def health(): return {'ok':True,'desktop':desktop}
    @app.get('/api/capabilities')
    def capabilities(): return {'desktop':desktop,'max_upload_bytes':MAX_UPLOAD}
    @app.get('/api/me')
    def me(request:Request):
        with Sessions() as db:
            u=who(db,request);return dict(userjson(u),desktop=desktop)
    @app.post('/api/register')
    async def register(request:Request):
        if desktop: raise HTTPException(403,'Registrierung über die Onlineversion.')
        throttled(request);b=await body(request);email=str(b.get('email','')).strip().lower();name=str(b.get('name','')).strip()
        if '@' not in email or len(email)>254 or not name or len(name)>200: raise HTTPException(422,'Name und E-Mail prüfen.')
        password=hash_password(b.get('password'))
        with Sessions() as db:
            if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,'Registrierung konnte nicht angelegt werden.')
            db.add(User(email=email,name=name,password=password));db.commit()
        return {'message':'Registrierung gespeichert. Ein Admin muss dein Konto freigeben.'}
    @app.post('/api/login')
    async def login(request:Request):
        if desktop: raise HTTPException(403,'Verbindung unter Synchronisierung einrichten.')
        throttled(request);b=await body(request)
        with Sessions() as db:
            u=db.scalar(select(User).where(User.email==str(b.get('email','')).strip().lower()))
            if not u or not verify(str(b.get('password','')),u.password) or not u.active: raise HTTPException(401,'Anmeldung fehlgeschlagen oder Konto noch nicht freigegeben.')
            token=login_token(db,u);response=JSONResponse({'user':userjson(u),'token':token} if b.get('desktop_client') else {'user':userjson(u)})
            response.set_cookie('session',token,httponly=True,samesite='strict',secure=request.url.scheme=='https',max_age=30*86400)
            return response
    @app.post('/api/logout')
    def logout(request:Request):
        if desktop: raise HTTPException(403,'Lokale App über das Fenster schließen.')
        with Sessions() as db:
            who(db,request);token=request.cookies.get('session','');r=db.get(Login,digest(token))
            if r: db.delete(r);db.commit()
        response=JSONResponse({'ok':True});response.delete_cookie('session');return response

    @app.get('/api/snapshot')
    def snapshot(request:Request):
        with Sessions() as db:
            u=who(db,request);rows=[r for r in db.scalars(select(Record)) if r.kind!='staged_media' or u.role=='admin' or r.data.get('owner')==u.id]
            return {'records':[{'id':r.id,'kind':r.kind,'data':r.data,'version':r.version} for r in rows],'generated':now()}
    @app.get('/api/archive')
    def archive(request:Request,q:str=''):
        with Sessions() as db:
            who(db,request);rows=list(db.scalars(select(Record)))
            return {'personen':[recordjson(r) for r in rows if r.kind=='person' and q.casefold() in json.dumps(r.data.get('namen',{}),ensure_ascii=False).casefold()+str(r.data.get('anzeigename','')).casefold()], 'familien':[recordjson(r) for r in rows if r.kind=='family'],'beziehungen':[recordjson(r) for r in rows if r.kind=='relationship'],'medien':[recordjson(r) for r in rows if r.kind=='media'],'pruefhinweise':[recordjson(r) for r in rows if r.kind=='issue']}
    @app.get('/api/person/{ident}')
    def person(ident:str,request:Request):
        with Sessions() as db:
            who(db,request);r=db.get(Record,ident)
            if not r or r.kind!='person': raise HTTPException(404)
            return recordjson(r)
    @app.post('/api/proposals')
    async def propose(request:Request):
        b=await body(request);kind=b.get('kind');payload=b.get('payload',{});validate(kind,payload)
        ident=b.get('id') or uid()
        if not isinstance(ident,str) or len(ident)>100: raise HTTPException(422,'Ungültige ID.')
        with lock,Sessions() as db:
            u=who(db,request)
            old=db.get(Proposal,ident)
            if old:
                if old.actor!=u.id: raise HTTPException(409,'Vorschlags-ID bereits verwendet.')
                return propjson(old)
            target=b.get('target') or ('person_'+uid() if kind=='person' else uid())
            if kind=='patch':
                r=db.get(Record,target)
                if not r or r.kind!='person': raise HTTPException(404,'Person nicht gefunden.')
                if not isinstance(b.get('base_version'),int): raise HTTPException(422,'Datensatzversion fehlt.')
                payload=dict(payload,before={p:getpath(r.data,p) for p in payload['changes']})
            if kind=='media':
                uploaded=db.get(Record,payload.get('upload_id',''))
                if not uploaded or uploaded.kind!='staged_media' or uploaded.data.get('owner')!=u.id: raise HTTPException(422,'Upload fehlt oder gehört einem anderen Nutzer.')
            p=Proposal(id=ident,actor=u.id,kind=kind,target=target,base_version=b.get('base_version',0),payload=payload,source=str(b.get('source',''))[:20000]);db.add(p)
            if desktop:
                # Server IDs and media bytes remain stable across retries.
                db.add(Outbox(id=ident,data={'type':'proposal','body':dict(b,id=ident,target=target)}))
            db.commit();return propjson(p)
    @app.get('/api/proposals')
    def proposals(request:Request):
        with Sessions() as db:
            u=who(db,request);rows=db.scalars(select(Proposal).order_by(Proposal.created.desc()))
            return [propjson(p) for p in rows if u.role=='admin' or p.actor==u.id]
    @app.post('/api/proposals/{ident}/review')
    async def review(ident:str,request:Request):
        b=await body(request)
        if desktop:
            from .sync import remote_request
            with Sessions() as db: admin(who(db,request))
            result=remote_request(app,'POST',f'/api/proposals/{ident}/review',json=b)
            from .sync import synchronize
            synchronize(app);return result
        if b.get('decision') not in ['approve','reject']: raise HTTPException(422,'Entscheidung fehlt.')
        with lock,Sessions() as db:
            u=who(db,request);admin(u)
            p=db.scalar(select(Proposal).where(Proposal.id==ident).with_for_update())
            if not p: raise HTTPException(404)
            if p.status!='pending': raise HTTPException(409,'Vorschlag bereits bearbeitet.')
            if b['decision']=='reject': p.status='rejected';p.reason=str(b.get('reason',''))[:20000]
            else:
                validate(p.kind,p.payload)
                r=db.scalar(select(Record).where(Record.id==p.target).with_for_update());before=copy.deepcopy(r.data) if r else None
                if p.kind=='patch':
                    if not r or r.version!=p.base_version: raise HTTPException(409,'Datensatz inzwischen geändert. Vorschlag auf Basis des aktuellen Stands neu einreichen.')
                    data=copy.deepcopy(r.data)
                    for path,value in p.payload['changes'].items():
                        old=getpath(data,path)
                        if path.endswith('.datum.iso'):
                            ev=path.split('.')[0];data.setdefault(ev,{}).setdefault('alternativen',[]).append({'wert':copy.deepcopy(data.get(ev,{})),'grund':'Stand vor Freigabe','bevorzugt':False})
                        setpath(data,path,value)
                    if getpath(data,'tod.datum.iso'): data['lebensstatus']='verstorben'
                    birth,death=getpath(data,'geburt.datum.iso'),getpath(data,'tod.datum.iso')
                    if birth and death and int(death[:4])<int(birth[:4]): raise HTTPException(422,'Sterbejahr liegt vor dem Geburtsjahr.')
                    data.setdefault('forschung',{}).setdefault('freigegebene_ergaenzungen',[]).append({'vorschlag_id':p.id,'quelle':p.source,'pruefer':u.id,'datum':now()})
                    r.data=data;r.version+=1
                else:
                    if r: raise HTTPException(409,'Zieldatensatz existiert bereits.')
                    data=copy.deepcopy(p.payload);data['id']=p.target
                    if p.kind=='person':
                        data.setdefault('datensatz_typ','person');data.setdefault('lebensstatus','unbekannt');data.setdefault('forschung',{})['status']='freigegebener_vorschlag'
                        for event in ['geburt','hochzeit','tod','taufe','bestattung']: data.setdefault(event,{'datum':{'iso':None},'ort_original':None})
                    elif p.kind=='relationship':
                        # Lock a shared sentinel to serialize cycle validation across server workers.
                        db.scalar(select(Setting).where(Setting.id=='graph_lock').with_for_update())
                        ensure_relationship(db,data);data.setdefault('elternschaft_typ','ungeklaert');data['biologisch_bestaetigt']=data['elternschaft_typ']=='biologisch';data['status']='freigegeben'
                    elif p.kind=='media':
                        for personid in data['person_ids']:
                            per=db.get(Record,personid)
                            if not per or per.kind!='person': raise HTTPException(409,'Bildperson muss zuerst freigegeben werden.')
                        upload=db.get(Record,data['upload_id'])
                        if not upload or upload.kind!='staged_media' or upload.data.get('owner')!=p.actor: raise HTTPException(409,'Upload fehlt oder gehört nicht zum Einreicher.')
                        data.update(datei=upload.data['datei'],mime_type=upload.data['mime_type'],sha256=upload.data['sha256']);data['zuordnungen']=[{'person_id':pid} for pid in data['person_ids']]
                    db.add(Record(id=p.target,kind={'person':'person','relationship':'relationship','media':'media'}[p.kind],data=data,version=1))
                db.add(Audit(target=p.target,actor=u.id,action='approve',data={'proposal':p.id,'source':p.source,'before':before,'after':copy.deepcopy(data),'version':r.version if r else 1}));p.status='approved'
            p.reviewer=u.id;db.commit();return propjson(p)

    @app.post('/api/upload')
    async def upload(request:Request):
        with Sessions() as db:
            u=who(db,request)
            from urllib.parse import unquote,quote
            title=unquote(request.headers.get('x-title','')).strip();person_ids=request.headers.get('x-person-ids','').split(',')
            if not title or len(title)>200 or not all(person_ids): raise HTTPException(422,'Upload braucht Titel und Personenzuordnung.')
            for pid in person_ids:
                per=db.get(Record,pid);pending=db.scalar(select(Proposal).where(Proposal.target==pid,Proposal.kind=='person',Proposal.status=='pending'))
                if not (per and per.kind=='person') and not (pending and (pending.actor==u.id or u.role=='admin')): raise HTTPException(422,'Unbekannte Person: zuerst neuen Personenvorschlag anlegen.')
            chunks=[];size=0
            async for chunk in request.stream():
                size+=len(chunk)
                if size>MAX_UPLOAD: raise HTTPException(413,'Maximal 8 MB pro Datei.')
                chunks.append(chunk)
            content=b''.join(chunks)
            if content.startswith(b'%PDF-'): ext='pdf';mime='application/pdf'
            else:
                try:
                    image=Image.open(io.BytesIO(content));image.verify();fmt=image.format
                    if fmt not in ['JPEG','PNG','WEBP']: raise ValueError()
                    ext={'JPEG':'jpg','PNG':'png','WEBP':'webp'}[fmt];mime={'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp'}[fmt]
                except Exception: raise HTTPException(422,'Nur gültige JPG-, PNG-, WebP-Bilder oder PDF-Dateien erlaubt.')
            import hashlib
            ident=request.headers.get('x-upload-id') or uid()
            if not all(c.isalnum() or c=='-' for c in ident) or len(ident)>100: raise HTTPException(422,'Ungültige Upload-ID.')
            old=db.get(Record,ident)
            if old:
                if old.kind!='staged_media' or old.data['owner']!=u.id or old.data['sha256']!=hashlib.sha256(content).hexdigest(): raise HTTPException(409,'Upload-ID Konflikt.')
                return {'id':ident}
            filename=ident+'.'+ext;path=media_dir/filename;path.write_bytes(content)
            data={'datei':filename,'mime_type':mime,'owner':u.id,'sha256':hashlib.sha256(content).hexdigest(),'title':title,'person_ids':person_ids}
            db.add(Record(id=ident,kind='staged_media',data=data))
            if desktop: db.add(Outbox(id=ident,data={'type':'upload','filename':filename,'headers':{'x-title':quote(title,safe=''),'x-person-ids':','.join(person_ids),'x-upload-id':ident}}))
            db.commit();return {'id':ident}
    @app.get('/api/media/{ident}')
    def media(ident:str,request:Request,share:str=''):
        with Sessions() as db:
            r=db.get(Record,ident)
            if not r or r.kind not in ['media','staged_media']: raise HTTPException(404)
            if share:
                s=db.scalar(select(Share).where(Share.token_hash==digest(share),Share.active==True))
                if not s or not s.data.get('allow_media') or r.kind!='media': raise HTTPException(403)
                ids=visible_ids(db,s)
                assigned=media_person_ids(db,r)
                # A group image must not reveal people outside the share's visible scope.
                if not assigned or not assigned.issubset(ids): raise HTTPException(403)
            else:
                u=who(db,request)
                if r.kind=='staged_media' and r.data.get('owner')!=u.id and u.role!='admin': raise HTTPException(403)
            path=(media_dir/r.data.get('datei','')).resolve()
            if not path.is_relative_to(media_dir.resolve()) or not path.is_file(): raise HTTPException(404,'Datei lokal noch nicht verfügbar.')
            return FileResponse(path,media_type=r.data.get('mime_type','application/octet-stream'),headers={'Content-Disposition':'inline'})
    def visible_ids(db,s):
        ids=set()
        for r in db.scalars(select(Record).where(Record.kind=='person')):
            if s.data.get('person_ids') and r.id not in s.data['person_ids']: continue
            birth=getpath(r.data,'geburt.datum.iso');status=r.data.get('lebensstatus','')
            dead=bool(getpath(r.data,'tod.datum.iso')) or status.startswith('verstorben') or (birth and int(birth[:4])<time.gmtime().tm_year-120)
            if dead or s.data.get('include_living'): ids.add(r.id)
        return ids
    def media_person_ids(db,r):
        ids=set(r.data.get('person_ids',[]));ids.update(x.get('person_id') for x in r.data.get('zuordnungen',[]) if x.get('person_id'))
        for p in db.scalars(select(Record).where(Record.kind=='person')):
            if any(a.get('medium_id')==r.id for a in p.data.get('anhaenge',[])): ids.add(p.id)
        return ids
    @app.get('/api/shared/{token}')
    def shared(token:str):
        if desktop: raise HTTPException(404)
        with Sessions() as db:
            s=db.scalar(select(Share).where(Share.token_hash==digest(token),Share.active==True))
            if not s: raise HTTPException(404,'Freigabelink ungültig oder widerrufen.')
            ids=visible_ids(db,s);rows=list(db.scalars(select(Record)))
            return {'name':s.name,'personen':[public_person(r) for r in rows if r.kind=='person' and r.id in ids],'familien':[{'id':r.id,'partner_person_ids':[i for i in r.data.get('partner_person_ids',[]) if i in ids],'kinder_person_ids':[i for i in r.data.get('kinder_person_ids',[]) if i in ids]} for r in rows if r.kind=='family' and any(i in ids for i in r.data.get('partner_person_ids',[]))],'beziehungen':[{'id':r.id,**{k:r.data.get(k) for k in ['typ','von_person_id','zu_person_id','elternschaft_typ','biologisch_bestaetigt','status']}} for r in rows if r.kind=='relationship' and r.data.get('von_person_id') in ids and r.data.get('zu_person_id') in ids],'medien':[{'id':r.id,'titel':r.data.get('titel'),'person_ids':sorted(media_person_ids(db,r)),'mime_type':r.data.get('mime_type')} for r in rows if r.kind=='media' and s.data.get('allow_media') and media_person_ids(db,r) and media_person_ids(db,r).issubset(ids)],'pruefhinweise':[]}
    @app.get('/api/users')
    def users(request:Request):
        if desktop:
            from .sync import remote_request
            with Sessions() as db: admin(who(db,request))
            return remote_request(app,'GET','/api/users')
        with Sessions() as db: admin(who(db,request));return [userjson(u) for u in db.scalars(select(User))]
    @app.post('/api/users/{ident}')
    async def user_edit(ident:str,request:Request):
        b=await body(request)
        if desktop:
            from .sync import remote_request
            with Sessions() as db: admin(who(db,request))
            return remote_request(app,'POST','/api/users/'+ident,json=b)
        with lock,Sessions() as db:
            me=who(db,request);admin(me);u=db.get(User,ident)
            if not u: raise HTTPException(404)
            if b.get('role') not in ['admin','member'] or not isinstance(b.get('active'),bool): raise HTTPException(422,'Rolle/Status ungültig.')
            if u.id==me.id and (b['role']!='admin' or not b['active']): raise HTTPException(409,'Eigenes Admin-Konto nicht deaktivieren.')
            u.role=b['role'];u.active=b['active'];db.add(Audit(target=u.id,actor=me.id,action='user_permissions',data=b));db.commit();return userjson(u)
    @app.get('/api/shares')
    def shares(request:Request):
        if desktop:
            from .sync import remote_request
            with Sessions() as db: admin(who(db,request))
            return remote_request(app,'GET','/api/shares')
        with Sessions() as db: admin(who(db,request));return [{'id':s.id,'name':s.name,'active':s.active,'data':s.data} for s in db.scalars(select(Share))]
    @app.post('/api/shares')
    async def share_create(request:Request):
        b=await body(request)
        if desktop:
            from .sync import remote_request
            with Sessions() as db: admin(who(db,request))
            return remote_request(app,'POST','/api/shares',json=b)
        with Sessions() as db:
            me=who(db,request);admin(me);token=secrets.token_urlsafe(32);ids=b.get('person_ids',[])
            if not isinstance(ids,list) or any(not db.get(Record,i) for i in ids): raise HTTPException(422,'Ungültiger Freigabebereich.')
            s=Share(id=uid(),name=str(b.get('name','Familienstammbaum'))[:200],token_hash=digest(token),data={'person_ids':ids,'include_living':b.get('include_living') is True,'allow_media':b.get('allow_media') is True});db.add(s);db.commit()
            return {'id':s.id,'token':token,'url':str(request.base_url).rstrip('/')+'/#share='+token}
    @app.post('/api/shares/{ident}/revoke')
    def revoke(ident:str,request:Request):
        if desktop:
            from .sync import remote_request
            with Sessions() as db: admin(who(db,request))
            return remote_request(app,'POST',f'/api/shares/{ident}/revoke',json={})
        with Sessions() as db:
            admin(who(db,request));s=db.get(Share,ident)
            if not s: raise HTTPException(404)
            s.active=False;db.commit();return {'ok':True}
    @app.get('/api/audit/{ident}')
    def history(ident:str,request:Request):
        with Sessions() as db:
            who(db,request);return [{'id':a.id,'actor':a.actor,'action':a.action,'created':a.created,'data':a.data} for a in db.scalars(select(Audit).where(Audit.target==ident).order_by(Audit.created.desc()))]
    @app.post('/api/audit/{ident}/restore')
    def restore(ident:str,request:Request):
        if desktop:
            from .sync import remote_request
            with Sessions() as db: admin(who(db,request))
            return remote_request(app,'POST',f'/api/audit/{ident}/restore',json={})
        with lock,Sessions() as db:
            me=who(db,request);admin(me);a=db.get(Audit,ident)
            if not a or a.data.get('before') is None: raise HTTPException(422,'Kein vorheriger Stand für diese Änderung.')
            r=db.scalar(select(Record).where(Record.id==a.target).with_for_update())
            if not r or r.version!=a.data.get('version'): raise HTTPException(409,'Weitere Änderungen vorhanden. Bitte einzeln korrigieren.')
            prev=copy.deepcopy(r.data);r.data=copy.deepcopy(a.data['before']);r.version+=1
            db.add(Audit(target=r.id,actor=me.id,action='restore',data={'before':prev,'after':r.data,'version':r.version,'restored_audit':a.id}));db.commit();return {'ok':True}
    if desktop:
        from .sync import install_desktop_routes
        install_desktop_routes(app,Sessions,who,admin,body,userjson)
    with Sessions() as db:
        if not db.get(Setting,'graph_lock'): db.add(Setting(id='graph_lock',data={}));db.commit()
    return app

app=create_app()
