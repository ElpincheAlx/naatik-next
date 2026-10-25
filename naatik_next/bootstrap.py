"""Small system-Tk setup front end used only when the Next Qt environment is absent.

Requires Fedora's documented python3-tkinter system package, never global pip.
All installation runs in a supervised subprocess, not Tk's event thread.
"""
from .i18n import t
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time


def main():
    try:
        import tkinter as tk
        from tkinter import ttk,messagebox
    except ImportError:
        print(t('Falta la interfaz de preparación del sistema: instala python3-tkinter en Fedora. No se usa Python de otro proyecto.'),file=sys.stderr)
        return 1
    from .install_language import existing_settings, persist
    from .i18n import set_language, choose_language
    # The language dialog is Tk-only: no Qt or private runtime is required yet.
    settings, _ = existing_settings()
    gate = tk.Tk(); gate.title('Idioma / Language'); gate.geometry('400x180')
    selected = {'code': None}
    value = tk.StringVar(value=settings.get('ui_language', 'es'))
    ttk.Label(gate, text='Idioma de interfaz / Interface language').pack(pady=12)
    ttk.Radiobutton(gate, text=t('Español'), variable=value, value='es').pack()
    ttk.Radiobutton(gate, text='English', variable=value, value='en').pack()
    def accept_language():
        selected['code'] = value.get(); gate.destroy()
    ttk.Button(gate, text='Continuar / Continue', command=accept_language).pack(side='left', padx=25, pady=15)
    ttk.Button(gate, text='Cancelar / Cancel', command=gate.destroy).pack(side='right', padx=25, pady=15)
    gate.mainloop()
    if selected['code'] is None: return 130
    set_language(selected['code'])
    os.environ['NAATIK_NEXT_UI_LANGUAGE'] = selected['code']
    from .translation_runtime import compatible,PROJECT
    try:compatible()
    except Exception as e:print(str(e),file=sys.stderr);return 1
    window=tk.Tk();window.title(t('Preparar Na’atik Next'));window.geometry('660x460')
    ttk.Label(window,text=t('Preparar Next desde cero'),font=('',16,'bold')).pack(padx=20,pady=16)
    ttk.Label(window,text=t('Falta la interfaz Qt o su entorno está incompleto. Next puede preparar su\nentorno privado con versiones y hashes fijados. No hace falta Argos global.\nOrigen: https://pypi.org/simple · CPU · Linux x86_64 / Python 3.14.\nLos modelos se preparan después en la sección Traducción.'),justify='left').pack(padx=20)
    log=tk.Text(window,height=12,wrap='word');log.pack(fill='both',expand=True,padx=20,pady=12)
    state={'process':None,'deadline':None,'closing':False,'ready':False};events=queue.Queue()
    def append(text):
        log.insert('end',text+'\n');log.see('end')
    def reader(process):
        for line in process.stdout:
            try:events.put(json.loads(line))
            except ValueError:events.put({'progress':t('Preparando…')})
        process.stdout.close();process.wait()
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        events.put({'exit':process.returncode})
    def prepare():
        if state['process'] is not None:return
        if not messagebox.askyesno(t('Confirmar descarga'),t('¿Descargar e instalar los requisitos de Next desde PyPI en .venv?\nNo se descargan modelos todavía. El tamaño total no está publicado en el lock.\nLicencias y versiones: docs/THIRD_PARTY_DEPENDENCIES.md.\nPuedes cancelar y reintentar sin usar cachés personales.'),parent=window):return
        try: persist(selected['code'])
        except Exception as error:
            messagebox.showerror(t('Configuración'), str(error), parent=window); return
        environment=dict(os.environ,PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')
        for key in ('PYTHONPATH','PYTHONHOME'):environment.pop(key,None)
        process=subprocess.Popen([sys.executable,'-m','naatik_next.worker'],cwd=PROJECT,env=environment,
                 stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,start_new_session=True)
        state.update(process=process,deadline=None,ready=False)
        process.stdin.write(json.dumps({'action':'prepare_base_runtime'})+'\n');process.stdin.close()
        threading.Thread(target=reader,args=(process,),daemon=True).start();start.config(state='disabled')
        append(t('Preparando entorno propio. La ventana seguirá respondiendo.'))
    def cancel(close=False):
        state['closing']=close
        process=state['process']
        if process and process.poll() is None:
            if state['deadline'] is None:
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                state['deadline']=time.monotonic()+2
            return
        if close:window.destroy()
    def opened():
        if state['ready']:os.execv(str(PROJECT/'.venv/bin/python'),[str(PROJECT/'.venv/bin/python'),'-m','naatik_next.app',*sys.argv[1:]])
    def poll():
        process=state['process']
        if process and state['deadline'] and time.monotonic()>state['deadline']:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        while not events.empty():
            item=events.get_nowait()
            if 'progress' in item:append(item['progress'])
            if 'error' in item:append(item['error'])
            if 'result' in item and state['deadline'] is None:state['ready']=True;append(t('Interfaz preparada. Abre Next para elegir y comprobar los modelos.'));open_button.config(state='normal')
            if 'exit' in item:
                state['process']=None;start.config(state='normal')
                if not state['ready']:append(t('Preparación no completada. Puedes reintentar; no se declara lista.'))
                if state['closing']:window.destroy();return
        window.after(100,poll)
    bar=ttk.Frame(window);bar.pack(fill='x',padx=20,pady=10)
    start=ttk.Button(bar,text=t('Descargar y preparar…'),command=prepare);start.pack(side='left')
    ttk.Button(bar,text=t('Cancelar'),command=cancel).pack(side='left',padx=10)
    open_button=ttk.Button(bar,text=t('Abrir Next'),command=opened,state='disabled');open_button.pack(side='right')
    window.protocol('WM_DELETE_WINDOW',lambda:cancel(True))
    # Signal callbacks only record an instruction; Qt/Tk work happens in poll.
    signal_state={'stop':False}
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:signal_state.update(stop=True))
    def signals():
        if signal_state['stop']:cancel(True)
        if not state['closing']:window.after(100,signals)
    window.after(100,poll);window.after(100,signals);window.mainloop()
    return 0


if __name__=='__main__':raise SystemExit(main())
