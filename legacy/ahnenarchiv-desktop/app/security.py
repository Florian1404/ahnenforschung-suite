import hashlib,hmac,secrets,time
from fastapi import HTTPException
from sqlalchemy import select
from .models import Login,User

def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def hash_password(p):
    if not isinstance(p,str) or not 12<=len(p)<=256: raise HTTPException(422,'Passwort muss 12 bis 256 Zeichen lang sein.')
    salt=secrets.token_hex(16)
    return salt+':'+hashlib.scrypt(p.encode(),salt=salt.encode(),n=16384,r=8,p=1).hex()
def verify(p,stored):
    try:
        salt,value=stored.split(':');return hmac.compare_digest(value,hashlib.scrypt(p.encode(),salt=salt.encode(),n=16384,r=8,p=1).hex())
    except (ValueError,TypeError): return False

def login_token(db,user):
    token=secrets.token_urlsafe(40);db.add(Login(id=digest(token),user_id=user.id,expires=int(time.time())+30*86400));db.commit();return token

def current(db,request):
    header=request.headers.get('authorization','');token=header[7:] if header.startswith('Bearer ') else request.cookies.get('session','')
    session=db.get(Login,digest(token))
    user=db.get(User,session.user_id) if session and session.expires>time.time() else None
    if not user or not user.active: raise HTTPException(401,'Bitte anmelden.')
    return user

def admin(user):
    if user.role!='admin': raise HTTPException(403,'Nur Admins dürfen diese Aktion ausführen.')
