import sys,os,threading,time,socket,logging
from pathlib import Path
ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent));sys.path.insert(0,str(ROOT))
DATA=Path(os.getenv('LOCALAPPDATA',Path.home()))/'Ahnenarchiv';DATA.mkdir(parents=True,exist_ok=True);os.environ['DATA_DIR']=str(DATA)
logging.basicConfig(filename=DATA/'app.log',level=logging.INFO)
def main():
    import uvicorn,webview
    from app.main import create_app
    from app.cli import import_archive
    from app.models import Record
    from app.sync import synchronize
    from sqlalchemy import select
    app=create_app(data_dir=DATA,desktop=True)
    with app.state.sessions() as db: empty=db.scalar(select(Record).limit(1)) is None
    seed=ROOT/'seed/stammbaum-huschka.json'
    if empty and seed.is_file(): import_archive(app,seed)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    app.state.allowed_hosts={f'127.0.0.1:{port}',f'localhost:{port}'}
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_config=None,access_log=False))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    for _ in range(200):
        if server.started: break
        time.sleep(.05)
    if not server.started: raise RuntimeError('Lokaler Start fehlgeschlagen.')
    stop=threading.Event()
    def sync_loop():
        while not stop.is_set(): synchronize(app);stop.wait(45)
    threading.Thread(target=sync_loop,daemon=True).start()
    webview.create_window('Ahnenarchiv · Familie Huschka',f'http://127.0.0.1:{port}/desktop/bootstrap?key={app.state.local_secret}',width=1280,height=850,min_size=(800,600))
    try: webview.start(gui='edgechromium')
    finally: stop.set();server.should_exit=True;thread.join(timeout=5)
if __name__=='__main__':
    try: main()
    except Exception:
        logging.exception('Start fehlgeschlagen')
        if sys.platform=='win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0,'Start fehlgeschlagen. Details: %LOCALAPPDATA%\\Ahnenarchiv\\app.log','Ahnenarchiv',16)
        raise
