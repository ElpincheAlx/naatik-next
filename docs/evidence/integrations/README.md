# Integraciones centralizadas — revisión 2026-10-20

**193 pruebas aprobadas**:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -q
```

[Salida completa](tests.txt). Tras el último ajuste visual pasaron también
**35 pruebas dirigidas** de integraciones/atajos ([salida](focused-tests.txt)).
Se conservan las pruebas de captura, traducción,
diccionarios, procesos e IPC; la interfaz sigue teniendo las seis pestañas previas.

Cobertura nueva/actualizada: selector de cuatro acciones; un solo bloque visible
de atajo/script; ausencia de atajos en Preferencias; independencia de combinaciones,
borradores, comandos, rutas y accesos; cambiar de acción sin guardar ni registrar;
persistencia al reabrir; conflictos entre acciones y con el atajo heredado;
desactivación con fallo de escritura; estado no registrado aunque exista una
preferencia activada; generación/sobrescritura y archivos que aparecen después
del diálogo; `--show` para abrir/reenviar a la ventana principal.

Los scripts y comandos copiados se ejecutaron realmente contra un lanzador
**sintético** que registra argumentos y perfil. Se probaron las cuatro acciones,
rutas con espacios, apóstrofes, Unicode, `$()`, `%` y barras, sin inyección. Los
`.desktop` se validaron/ejecutaron con Gio del sistema contra ese lanzador de
prueba. Esto comprueba escapado y argumentos; no equivale a activar un botón
físico ni a lanzar una instancia gráfica real desde KDE o StreamController.
No se modificaron sus configuraciones ni los scripts preexistentes del usuario.

## Capturas

- Integraciones (referencia histórica no distribuida): perfil temporal, script real generado para
  Translator y estado **No registrado**, sin ocultar el fallo.
- Detalles (referencia histórica no distribuida): comando escapado, perfil XDG y atajo previo
  conservado en compatibilidad.

Ambas son renders Qt **offscreen**, sin simular registro satisfactorio.

## Registro global: sin acreditar en este escritorio

Se ejecutó realmente `X11Grab`/libX11 sobre el `DISPLAY=:0` declarado. Falló al
abrir el display; no se llegó al registro ni al segundo registro de conflicto.
Qt offscreen también rechazó el registro y mostró ese estado. No hubo pulsaciones
sintéticas ni cambios de atajos KDE. El cierre dejó el atajo inactivo.
[Resultado estructurado](evidence.json).

Las pruebas de registro/conflicto que sí pasan usan un backend inyectado y eventos
simulados, además de comprobar el protocolo/rollback. **La reorganización no
resuelve ni acredita el fallo global anterior.** Registro, conflicto real y
activación con foco en otra aplicación requieren la sesión KDE/X11 del usuario.

Reproducir el render y el intento de registro con un perfil HOME/XDG temporal:

```bash
cd ${PROJECT_ROOT}
.venv/bin/python tools/integrations_review.py --probe-x11 \
  --output /tmp/HISTORICAL-REVIEW
```

Para el probe de registro real Qt usa `QT_QPA_PLATFORM=xcb` desde el escritorio.
El probe registra y libera temporalmente `Ctrl+Alt+Shift+F12` en conexiones propias,
sin tocar KDE y sin enviar teclas. No acredita activación interactiva.
[Guía y pasos manuales](../../INTEGRATIONS.md#comprobar-en-el-escritorio).
