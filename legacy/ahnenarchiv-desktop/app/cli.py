import argparse,json,shutil,getpass,os
from pathlib import Path
from sqlalchemy import select
from .main import create_app
from .models import Record,User,Audit,uid
from .security import hash_password

def import_archive(app,path):
    path=Path(path);data=json.loads(path.read_text(encoding='utf-8'));mapping={'personen':'person','familien':'family','beziehungen':'relationship','medien':'media','quellen':'source','orte':'place','pruefhinweise':'issue','quellenseiten':'source_page'}
    with app.state.sessions() as db:
        if db.scalar(select(Record).limit(1)): raise RuntimeError('Import nur in leeren Bestand. Kein Überschreiben vorhandener Forschung.')
        for key,kind in mapping.items():
            for obj in data.get(key,[]):
                db.add(Record(id=obj.get('id',uid()),kind=kind,data=obj,version=1))
        db.add(Record(id='original_import',kind='archive_meta',data={k:v for k,v in data.items() if k not in mapping}))
        db.commit()
    for obj in data.get('medien',[]):
        source=(path.parent/obj['datei']).resolve()
        if not source.is_relative_to(path.parent.resolve()): continue
        if source.is_file():
            dest=app.state.media_dir/obj['datei'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    return len(data['personen'])

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    imp=sub.add_parser('import');imp.add_argument('path')
    adm=sub.add_parser('admin');adm.add_argument('--email',required=True);adm.add_argument('--name',required=True)
    sub.add_parser('export').add_argument('path')
    args=parser.parse_args();app=create_app()
    if args.command=='import': print(f'{import_archive(app,args.path)} Personen importiert.')
    elif args.command=='admin':
        password=getpass.getpass('Admin-Passwort (mindestens 12 Zeichen): ')
        if password!=getpass.getpass('Wiederholen: '): raise SystemExit('Passwörter unterscheiden sich.')
        with app.state.sessions() as db:
            if db.scalar(select(User).where(User.email==args.email.lower())): raise SystemExit('Konto existiert bereits. Rechte in der Anwendung ändern.')
            db.add(User(email=args.email.lower(),name=args.name,password=hash_password(password),role='admin',active=True));db.commit()
        print('Admin angelegt.')
    else:
        with app.state.sessions() as db:
            original=db.get(Record,'original_import');out=dict(original.data) if original else {}
            mapping={'person':'personen','family':'familien','relationship':'beziehungen','media':'medien','source':'quellen','place':'orte','issue':'pruefhinweise','source_page':'quellenseiten'}
            for key in mapping.values(): out[key]=[]
            for r in db.scalars(select(Record)):
                if r.kind in mapping: out[mapping[r.kind]].append(r.data)
            out['app_ergaenzungen']={'vorschlaege':[{k:getattr(p,k) for k in ['id','actor','kind','target','payload','source','status','reviewer']} for p in db.scalars(select(__import__('app.models',fromlist=['Proposal']).Proposal))]}
        Path(args.path).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print('Export erstellt.')
if __name__=='__main__': main()
