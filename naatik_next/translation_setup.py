"""Explicit official catalogue and resumable provisioning; no network in inference.

Only this setup module accesses the catalogue. Models are data selected by key
from a locally recorded official index, never arbitrary command/URL requests.
"""
from .i18n import t
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from .storage import paths, UserError

INDEX = 'https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json'
LICENSE_SOURCE = 'https://github.com/argosopentech/argos-translate/issues/533'
LICENSE = t('MIT o CC0 según el mantenedor; el catálogo no acredita licencia individual. ')+LICENSE_SOURCE
MAX_MODEL = 1024**3
SAMPLE = '私は毎日日本語を勉強しています。今日は図書館で本を読みます。'


def root():
    directory = paths()['data']/'argos'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory


def atomic_json(path, value):
    fd, name = tempfile.mkstemp(prefix='.next-', dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream: json.dump(value, stream, ensure_ascii=False, indent=2)
        os.replace(name, path)
    finally: Path(name).unlink(missing_ok=True)


@contextlib.contextmanager
def locked(name):
    import fcntl
    with (root()/name).open('a') as lock:
        try: fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as e: raise UserError(t('Ya hay otra preparación de traducción en curso.')) from e
        yield


def version(text):
    if not isinstance(text,str) or not re.fullmatch(r'\d+(?:\.\d+){0,3}',text):
        raise UserError(t('Versión de catálogo no admitida.'))
    return tuple(int(n) for n in text.split('.')) + (0,)*(4-len(text.split('.')))


def secure_url(url, *, redirect=False):
    parsed=urllib.parse.urlsplit(url)
    hosts={'argos-net.com','www.argosopentech.com','raw.githubusercontent.com','github.com'}
    if redirect: hosts.update({'storage.googleapis.com','objects.githubusercontent.com','release-assets.githubusercontent.com'})
    if parsed.scheme!='https' or parsed.hostname not in hosts or parsed.username or parsed.password or parsed.port not in (None,443):
        raise UserError(t('El catálogo contiene un origen HTTPS no admitido: ')+str(parsed.hostname))
    return url


class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        secure_url(newurl, redirect=True)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class AccessError(UserError):
    """A server/proxy HTTP rejection, distinct from DNS and integrity failures."""


def open_url(request, timeout=20):
    secure_url(request.full_url, redirect=True)
    try:
        return urllib.request.build_opener(HTTPSRedirect()).open(request,timeout=timeout)
    except urllib.error.HTTPError as error:
        code=error.code
        error.close()
        hint=(t(' Puedes obtener el archivo del origen oficial en tu navegador e importarlo en Traducción → Opciones avanzadas → Importar modelo local.')
              if request.full_url.endswith('.argosmodel') else t(' El catálogo no se ha actualizado.'))
        raise AccessError(('HTTP ' + f'{code}' + ' en ' + f'{request.get_method()}' + ' de ' + f'{request.full_url}' + t('. La respuesta procede del servidor o de un intermediario; este estado no identifica la causa.'))+hint) from None


def normalize(items):
    if not isinstance(items,list) or len(items)>3000: raise UserError(t('Catálogo no válido.'))
    result=[]
    for item in items:
        if item.get('type','translate')!='translate': continue
        a,b=item.get('from_code',''),item.get('to_code','')
        if not all(isinstance(c,str) and re.fullmatch('[A-Za-z0-9_-]{1,20}',c) for c in (a,b)): continue
        links=item.get('links',[])
        url=next((link for link in links if isinstance(link,str) and link.startswith('https://')),None)
        if not url: continue
        try: secure_url(url)
        except UserError: continue
        required=item.get('argos_version','0'); release=item.get('package_version','0')
        try: compatible=version(required)<=version('1.11.0'); version(release)
        except UserError: continue
        key=hashlib.sha256((a+'|'+b+'|'+release+'|'+url).encode()).hexdigest()
        result.append(dict(key=key,from_code=a,to_code=b,version=release,requires=required,
                           from_name=str(item.get('from_name',a))[:100],to_name=str(item.get('to_name',b))[:100],
                           compatible=compatible,url=url,license=str(item.get('license') or LICENSE)[:1000]))
    return result


def catalogue(*, online=False, opener=open_url, progress=lambda text:None):
    target=root()/'catalogue.json'
    if online:
        progress(t('Consultando catálogo oficial de Argos…'))
        try:
            with opener(urllib.request.Request(INDEX),timeout=20) as response:
                secure_url(response.geturl(),redirect=True)
                data=response.read(4*1024*1024+1)
        except OSError as e:raise UserError(t('No se pudo consultar el catálogo oficial. Revisa la conexión y reintenta; se conserva el catálogo anterior. ')+str(e)) from e
        if len(data)>4*1024*1024: raise UserError(t('El catálogo excede el tamaño permitido.'))
        items=normalize(json.loads(data))
        value=dict(source=INDEX,sha256=hashlib.sha256(data).hexdigest(),items=items)
        atomic_json(target,value)
        return value
    if not target.is_file(): return dict(source=INDEX,sha256=None,items=[])
    value=json.loads(target.read_text())
    if value.get('source')!=INDEX: raise UserError(t('Origen del catálogo guardado no válido.'))
    # Keys/URLs are revalidated on use; no executable data in the cache.
    for item in value['items']: secure_url(item['url'])
    return value


def plans(items, source='ja', destination='es'):
    compatible=[item for item in items if item['compatible']]
    def edge(a,b):
        choices=[i for i in compatible if (i['from_code'],i['to_code'])==(a,b)]
        return max(choices,key=lambda i:version(i['version'])) if choices else None
    direct=edge(source,destination)
    result=[]
    if direct: result.append(dict(route=[source,destination],keys=[direct['key']]))
    if source!='en' and destination!='en':
        first,second=edge(source,'en'),edge('en',destination)
        if first and second:result.append(dict(route=[source,'en',destination],keys=[first['key'],second['key']]))
    return result


def selected(keys, digest):
    cache=catalogue()
    if not digest or cache['sha256']!=digest:raise UserError(t('El catálogo cambió; revisa de nuevo la propuesta antes de descargar.'))
    if not isinstance(keys,list) or not 1<=len(keys)<=2 or len(set(keys))!=len(keys):raise UserError(t('Selección de modelos inválida.'))
    available={i['key']:i for i in cache['items']}
    try:items=[available[key] for key in keys]
    except KeyError as e:raise UserError(t('El modelo ya no aparece en el catálogo guardado.')) from e
    if not all(re.fullmatch('[0-9a-f]{64}',i['key']) and i['key']==hashlib.sha256((i['from_code']+'|'+i['to_code']+'|'+i['version']+'|'+i['url']).encode()).hexdigest() for i in items):raise UserError(t('Metadatos guardados no válidos; vuelve a consultar el catálogo.'))
    if not all(i['compatible'] and version(i['requires'])<=version('1.11.0') for i in items):raise UserError(t('El modelo requiere otra versión de Argos.'))
    if len(items)==2 and items[0]['to_code']!=items[1]['from_code']:raise UserError(t('Los modelos no forman una ruta.'))
    return items


def details(keys, digest, *, opener=open_url, progress=lambda text:None):
    items=selected(keys,digest)
    result=[]
    for item in items:
        item=dict(item,bytes=None)
        progress(t('Consultando tamaño: ')+item['from_code']+' → '+item['to_code'])
        try:
            with opener(urllib.request.Request(item['url'],method='HEAD'),timeout=20) as response:
                secure_url(response.geturl(),redirect=True)
                length=response.headers.get('Content-Length','')
                if length.isdigit() and 0<int(length)<=MAX_MODEL:item['bytes']=int(length)
        except (OSError,AccessError) as error:
            item['size_detail']=t('No se pudo comprobar el tamaño (HEAD): ')+str(error)
        result.append(item)
    return dict(items=result,sha256=digest,route=[items[0]['from_code']]+[i['to_code'] for i in items])


def download(item, *, opener=open_url, progress=lambda text:None):
    """Resume only with a server identity validator; validate ZIP before import."""
    folder=root()/'downloads';folder.mkdir(exist_ok=True,mode=0o700)
    final=folder/(item['key']+'.argosmodel');partial=folder/(item['key']+'.part');meta=folder/(item['key']+'.json')
    if any(p.is_symlink() for p in (final,partial,meta)):raise UserError(t('Destino de descarga enlazado no admitido.'))
    if final.is_file():return final
    prior=json.loads(meta.read_text()) if meta.is_file() else {}
    offset=partial.stat().st_size if partial.is_file() else 0
    if offset and offset==prior.get('total') and offset<=MAX_MODEL:return finish_download(partial,final,meta)
    if offset>MAX_MODEL or not prior.get('validator'):offset=0
    headers={'Accept-Encoding':'identity'}
    if offset:headers.update(Range=f'bytes={offset}-',**{'If-Range':prior['validator']})
    started=time.monotonic()
    with opener(urllib.request.Request(item['url'],headers=headers),timeout=20) as response:
        secure_url(response.geturl(),redirect=True)
        status=response.status
        etag=response.headers.get('ETag','')
        validator=etag if etag and not etag.startswith('W/') else response.headers.get('Last-Modified')
        length=response.headers.get('Content-Length','')
        total=int(length) if length.isdigit() else None
        if status==206:
            match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
            if not offset or not match or int(match[1])!=offset or validator!=prior.get('validator'):
                raise UserError(t('Reanudación incoherente; se conserva el parcial para reintentar.'))
            total=int(match[3])
            if int(match[2])!=total-1 or (length.isdigit() and int(length)!=total-offset):raise UserError(t('Rango de descarga incoherente.'))
        elif status==200:offset=0
        else:raise UserError(t('Respuesta de descarga inesperada: ')+str(status))
        if total is not None and not 0<total<=MAX_MODEL:raise UserError(t('Tamaño de modelo no admitido (máximo 1 GiB).'))
        atomic_json(meta,dict(validator=validator,total=total,url=item['url']))
        with partial.open('ab' if offset else 'wb') as stream:
            while True:
                if time.monotonic()-started>900:raise UserError(t('Descarga interrumpida por tiempo; vuelve a intentar para recuperar el parcial.'))
                block=response.read(256*1024)
                if not block:break
                offset+=len(block)
                if offset>MAX_MODEL or (total is not None and offset>total):raise UserError(t('El modelo supera el tamaño anunciado.'))
                stream.write(block);stream.flush()
                progress(f"{item['from_code']} → {item['to_code']}: {offset:,} / {total if total else 'tamaño desconocido'} bytes")
        if not offset or (total is not None and offset!=total):raise UserError(t('Descarga incompleta; vuelve a intentar para reanudar.'))
    return finish_download(partial,final,meta)


def finish_download(partial,final,meta):
    import zipfile
    try:
        with zipfile.ZipFile(partial) as archive:
            if len(archive.infolist())>20000 or sum(i.file_size for i in archive.infolist())>2*MAX_MODEL:
                raise UserError(t('El paquete descomprimido supera el límite admitido.'))
            if archive.testzip():raise UserError(t('El paquete descargado no supera su comprobación ZIP.'))
    except (zipfile.BadZipFile,UserError):
        partial.unlink(missing_ok=True);meta.unlink(missing_ok=True);raise UserError(t('Paquete incompleto o dañado; vuelve a descargar.'))
    partial.replace(final)
    return final


@contextlib.contextmanager
def offline_guard():
    import socket
    names=('create_connection','getaddrinfo')
    saved={name:getattr(socket,name) for name in names}
    saved_methods={name:getattr(socket.socket,name) for name in ('connect','connect_ex')}
    def blocked(*args,**kwargs):raise UserError(t('La prueba sin conexión intentó acceder a la red; no se declara lista.'))
    try:
        for name in names:setattr(socket,name,blocked)
        for name in saved_methods:setattr(socket.socket,name,blocked)
        yield
    finally:
        for name,value in saved.items():setattr(socket,name,value)
        for name,value in saved_methods.items():setattr(socket.socket,name,value)


def validate(route, *, _locked=False):
    if not _locked:
        with locked('.provision.lock'):return validate(route,_locked=True)
    from .translation import Argos
    with offline_guard():
        engine=Argos();report=engine.discover()
        if route not in report['routes']:raise UserError(t('La ruta no pasó carga e inferencia: ')+'; '.join(report['errors']))
        result=engine.translate(SAMPLE,route)
    from .translation import package_api
    api,directory=package_api()
    installed=[dict(from_code=p.from_code,to_code=p.to_code,version=p.package_version) for p in api.get_installed_packages(path=[directory])]
    value=dict(route=route,input=SAMPLE,output=result['text'],offline_checked=True,installed=installed,available_routes=report['routes'],errors=report['errors'],
               status=t('Listo: carga e inferencia CPU comprobadas con conexiones Python bloqueadas; puede usarse sin conexión.'))
    atomic_json(root()/'validation.json',value)
    return value


def install_models(keys,digest,*,opener=open_url,progress=lambda text:None,preserve_installed=False,download_keys=None):
    from .translation import install_package
    items=selected(keys,digest)
    with locked('.provision.lock'):
        from .translation import package_api
        api, directory = package_api()
        existing = {(p.from_code, p.to_code) for p in api.get_installed_packages(path=[directory])} if preserve_installed else set()
        for item in items:
            if (item['from_code'], item['to_code']) in existing:
                progress(t('Conservando modelo instalado ')+item['from_code']+' → '+item['to_code'])
                continue
            if download_keys is not None and item['key'] not in download_keys:
                raise UserError(t('Los modelos instalados cambiaron desde la propuesta. Revisa y confirma de nuevo la preparación.'))
            path=download(item,opener=opener,progress=progress)
            progress('Importando y validando paquete '+item['from_code']+' → '+item['to_code'])
            result=install_package(path,expected=(item['from_code'],item['to_code']))
            from .resources import digest as file_digest
            atomic_json(Path(result['model'])/'naatik-import.json',dict(source=item['url'],catalogue_sha256=digest,
                        sha256=file_digest(path),license=item['license'],license_source=LICENSE_SOURCE))
        route=[items[0]['from_code']]+[i['to_code'] for i in items]
        progress(t('Comprobando carga e inferencia real de ')+' → '.join(route))
        return validate(route,_locked=True)


def status(*, _locked=False):
    if not _locked:
        with locked('.provision.lock'):return status(_locked=True)
    from .translation import Argos,package_api
    installed=[];error=''
    try:
        api,directory=package_api()
        installed=[dict(from_code=p.from_code,to_code=p.to_code,version=p.package_version) for p in api.get_installed_packages(path=[directory])]
        ready=Argos().discover()
    except Exception as e:ready=dict(routes=[],errors=[str(e)],detail=t('Falta preparar el entorno de traducción.'));error=str(e)
    return dict(installed=installed,**ready,catalogue=catalogue(),runtime_error=error)
