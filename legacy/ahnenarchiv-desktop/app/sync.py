"""Desktop sync: durable SQLite outbox; retries preserve UUIDs; server owns approvals."""
import threading,time,copy
from pathlib import Path
from urllib.parse import urlparse
import httpx
from fastapi import Request,HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select,delete
from .models import Setting,Record,User,Proposal,Outbox,now,uid
from .security import hash_password,login_token

SYNC_LOCK=threading.Lock()
def vault(app):
    import keyring
    return keyring, 'Ahnenarchiv:'+str(app.state.storage.resolve())
def get_token(app):
    if hasattr(app.state,'test_token'): return app.state.test_token
    k,service=vault(app);return k.get_password(service,'server-token')
def put_token(app,token):
    k,service=vault(app);k.set_password(service,'server-token',token)
def config(app):
    with app.state.sessions() as db:
        s=db.get(Setting,'remote');return s.data if s else {}
def remote_request(app,method,path,**kwargs):
    cfg=config(app);token=get_token(app)
    if not cfg.get('url') or not token: raise HTTPException(503,'Onlineverbindung zuerst einrichten.')
    try:
        with httpx.Client(timeout=30,follow_redirects=False) as client:
            r=client.request(method,cfg['url']+path,headers={'Authorization':'Bearer '+token,**kwargs.pop('headers',{})},**kwargs)
            if r.status_code>=400:
                try: msg=r.json().get('detail','Serverfehler')
                except ValueError: msg='Serverfehler'
                raise HTTPException(r.status_code,msg)
            return r.json()
    except httpx.HTTPError: raise HTTPException(503,'Keine Verbindung zum Server. Deine Ergänzungen bleiben lokal gespeichert.')

def synchronize(app):
    if not SYNC_LOCK.acquire(blocking=False): return app.state.sync_status
    try:
        with app.state.sessions() as db:
            queue=list(db.scalars(select(Outbox).where(Outbox.status=='queued').order_by(Outbox.created)))
        for item in queue:
            try:
                if item.data['type']=='upload':
                    content=(app.state.media_dir/item.data['filename']).read_bytes()
                    remote_request(app,'POST','/api/upload',headers=item.data['headers'],content=content)
                else: remote_request(app,'POST','/api/proposals',json=item.data['body'])
            except HTTPException as exc:
                with app.state.sessions() as db:
                    q=db.get(Outbox,item.id);q.error=str(exc.detail);db.commit()
                raise
            with app.state.sessions() as db:
                q=db.get(Outbox,item.id);q.status='sent';q.error='';db.commit()
        snap=remote_request(app,'GET','/api/snapshot')
        proposals=remote_request(app,'GET','/api/proposals')
        me=remote_request(app,'GET','/api/me')
        if me['id']!=config(app).get('user_id'): raise HTTPException(409,'Verbindung gehört zu anderem Konto.')
        with app.state.lock,app.state.sessions() as db:
            remote_ids={r['id'] for r in snap['records']}
            for r in list(db.scalars(select(Record))):
                if r.kind!='staged_media' and r.id not in remote_ids: db.delete(r)
            for obj in snap['records']:
                obj=copy.deepcopy(obj)
                if obj['kind']=='staged_media' and obj['data'].get('owner')==me['id']: obj['data']['owner']='local'
                r=db.get(Record,obj['id'])
                if r: r.data=obj['data'];r.kind=obj['kind'];r.version=obj['version']
                else: db.add(Record(**obj))
            for obj in proposals:
                p=db.get(Proposal,obj['id'])
                if p:
                    for k,v in obj.items(): setattr(p,k,v)
                else: db.add(Proposal(**obj))
            local=db.get(User,'local');local.role=me['role'];local.name=me['name'];local.email=me['email']
            # Private staged files belong to the local desktop user in its copy.
            for p in db.scalars(select(Proposal).where(Proposal.kind=='media')):
                upload=db.get(Record,p.payload.get('upload_id',''))
                if upload and upload.kind=='staged_media': upload.data=dict(upload.data,owner='local')
            db.commit()
        cfg=config(app);token=get_token(app)
        with httpx.Client(timeout=60,follow_redirects=False) as client:
            for obj in snap['records']:
                if obj['kind'] not in ('media','staged_media'): continue
                path=app.state.media_dir/obj['data'].get('datei','')
                if not path.resolve().is_relative_to(app.state.media_dir.resolve()): continue
                if path.is_file(): continue
                r=client.get(cfg['url']+'/api/media/'+obj['id'],headers={'Authorization':'Bearer '+token})
                if r.status_code==200:
                    import hashlib
                    expected=obj['data'].get('sha256')
                    if expected and hashlib.sha256(r.content).hexdigest()!=expected: raise HTTPException(503,'Mediendatei konnte nicht verifiziert werden. Erneuter Abgleich folgt.')
                    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.part');tmp.write_bytes(r.content);tmp.replace(path)
                else: raise HTTPException(503,'Daten abgeglichen; eine Mediendatei konnte noch nicht geladen werden.')
        app.state.sync_status={'message':'Alles auf aktuellem Stand','last_sync':now()}
    except Exception as exc:
        message=str(exc.detail) if isinstance(exc,HTTPException) else 'Abgleich unterbrochen. Lokale Daten bleiben erhalten.'
        app.state.sync_status=dict(app.state.sync_status,message=message)
    finally: SYNC_LOCK.release()
    return app.state.sync_status

def install_desktop_routes(app,Sessions,who,admin,body,userjson):
    with Sessions() as db:
        if not db.get(User,'local'):
            # Initial offline permissions are member until server verifies an admin login.
            db.add(User(id='local',email='lokal@ahnenarchiv.invalid',name='Lokaler Benutzer',password=hash_password(uid()),role='member',active=True));db.commit()
    @app.get('/desktop/bootstrap')
    def bootstrap(key:str):
        import hmac
        if not hmac.compare_digest(key,app.state.local_secret): raise HTTPException(403)
        with Sessions() as db: token=login_token(db,db.get(User,'local'))
        response=RedirectResponse('/');response.set_cookie('session',token,httponly=True,samesite='strict');return response
    @app.get('/api/desktop/status')
    def status(request:Request):
        with Sessions() as db:
            who(db,request);queue=list(db.scalars(select(Outbox).where(Outbox.status=='queued')))
            return dict(app.state.sync_status,queued=len(queue),errors=[q.error for q in queue if q.error],url=config(app).get('url',''))
    @app.post('/api/desktop/connect')
    async def connect(request:Request):
        with Sessions() as db: who(db,request)
        b=await body(request);url=str(b.get('url','')).strip().rstrip('/');parsed=urlparse(url)
        if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('localhost','127.0.0.1')): raise HTTPException(422,'Serveradresse muss HTTPS verwenden.')
        if parsed.username or parsed.password or parsed.query or parsed.fragment: raise HTTPException(422,'Ungültige Serveradresse.')
        try:
            with httpx.Client(timeout=20) as client:
                r=client.post(url+'/api/login',json={'email':b.get('email'),'password':b.get('password'),'desktop_client':True})
                if r.status_code!=200: raise HTTPException(401,'Anmeldung am Server fehlgeschlagen.')
                result=r.json()
        except httpx.HTTPError: raise HTTPException(503,'Server nicht erreichbar.')
        with Sessions() as db:
            previous=db.get(Setting,'remote')
            if previous and (previous.data['user_id']!=result['user']['id'] or previous.data['url']!=url): raise HTTPException(409,'Diese lokale Installation ist an ein anderes Konto oder einen anderen Server gebunden. Dafür ein getrenntes Datenverzeichnis verwenden.')
        put_token(app,result['token'])
        with Sessions() as db:
            s=db.get(Setting,'remote');data={'url':url,'user_id':result['user']['id']}
            if s: s.data=data
            else: db.add(Setting(id='remote',data=data))
            u=db.get(User,'local');u.role=result['user']['role'];u.name=result['user']['name'];db.commit()
        # Reassign unsent local actors server-side on submission; local ownership remains separate.
        threading.Thread(target=synchronize,args=(app,),daemon=True).start();return {'ok':True}
    @app.post('/api/desktop/sync')
    def sync_now(request:Request):
        with Sessions() as db: who(db,request)
        threading.Thread(target=synchronize,args=(app,),daemon=True).start();return {'message':'Abgleich gestartet'}
    @app.get('/api/desktop/history/{ident}')
    def history(ident:str,request:Request):
        with Sessions() as db: who(db,request)
        return remote_request(app,'GET','/api/audit/'+ident)
