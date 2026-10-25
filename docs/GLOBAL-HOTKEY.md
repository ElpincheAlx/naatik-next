> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Atajo global de captura y OCR

Implementación del 2026-10-19. Plataforma objetivo: **KDE/X11**, Qt `xcb`.
No se declara soporte Wayland ni validación de activación global en escritorio.

## Configurar y probar

1. Abre `${PROJECT_ROOT}/launch`. En **OCR**, espera a que el motor seleccionado
   esté **listo**. No se selecciona un motor alternativo automáticamente.
2. En **Integraciones → Detalles → Compatibilidad: atajo anterior de capturar y reconocer**, enfoca
   el campo y pulsa una combinación con Ctrl, Alt o Meta. Pulsa **Guardar**.
   Inicialmente está desactivado; su valor previo se conserva. El valor inicial histórico es **Ctrl+Alt+Shift+R**. Solo se admiten
   combinaciones simples: letras, números, F1–F35, espacio, Impr Pant y navegación.
3. Comprueba el estado: **Registrado en X11** significa que el servidor aceptó
   el registro, no que ya se haya comprobado el recorrido interactivo. Si hay
   conflicto o error, no se declara el atajo activo. La preferencia solicitada
   se conserva para reintentar al abrir Next; puedes cambiarla o desactivarla.
4. Da el foco a otra aplicación y pulsa el atajo. Next se oculta, Spectacle pide
   una región y al completarla se ejecuta el OCR seleccionado. Next muestra la
   imagen y el resultado. No hay traducción automática. Prueba **日本**, su
   original OCR y la consulta JMdict desde la selección.
5. Repite y cancela con **Esc**: no debe arrancar OCR ni cambiar la imagen, el
   original, las correcciones o el panel de diccionario anteriores. Comprueba
   que Next vuelve a mostrarse. Mantén/repite el atajo durante captura y OCR:
   debe haber una sola operación. Si hay correcciones, primero se solicita
   confirmación para reemplazarlas; rechazándola se conservan.
6. Guarda otra combinación: la anterior debe dejar de actuar. **Desactivar**
   libera el registro y guarda ese estado. Puedes escribir otro valor en el campo sin activar ni cambiar el registro hasta pulsar **Guardar**.
   Cierra/reabre para comprobar persistencia; cerrar libera el registro.
7. Opcionalmente prueba una combinación ya utilizada por otra aplicación: un
   conflicto de grab X11 se informa y no se sustituye. No todos los mecanismos
   de atajos de otras aplicaciones tienen conflictos detectables: comprueba
   manualmente el efecto y usa una combinación libre.

Next debe permanecer abierto; no se añade servicio ni proceso residente tras
cerrar. El atajo no inicia captura mientras haya captura, OCR o diálogo modal de
Next activo, ni mientras se esté registrando una combinación en el campo activo.
Después de cambiar el mapa/distribución del teclado, guarda de nuevo el atajo:
esta versión no vuelve a mapear automáticamente los registros X11.

## API y ciclo de vida

`naatik_next.hotkey` usa **libX11 del sistema** mediante `ctypes` de CPython:
conexión propia, root window, `XGrabKey` con keycode y modificadores concretos,
modos asíncronos y `owner_events=False`. Lee el mapa real de modificadores y
registra variantes de Caps/Num/Scroll Lock. No utiliza `AnyKey`, `AnyModifier`,
monitorización global del teclado ni guarda/loguea las pulsaciones. Los eventos
ajenos a la combinación se ignoran. El auto-repeat tradicional Release/Press se
filtra; el flujo Qt también ignora activaciones durante captura/OCR.

Se comprueban los errores asíncronos con `XSync` y un manejador Xlib temporal,
restaurado inmediatamente en el hilo principal. `BadAccess` significa conflicto;
se liberan los registros propios parciales. Cambiar una combinación libera la
anterior antes de intentar la nueva: si falla, **no queda ningún atajo activo**.
Se desactiva el notifier antes de liberar registros y cerrar la conexión.

`QSocketNotifier` integra el descriptor X11 en el hilo principal Qt. La captura
reutiliza el worker Spectacle existente y OCR reutiliza los workers Tesseract o
MangaOCR. Un QTimer cancelable cubre el intervalo ocultar/iniciar proceso; el
bloqueo de duplicados comienza antes de ese intervalo. Cancelar/fallar restaura
la ventana, preserva los datos anteriores y no lanza OCR. El motor/idioma se
comprueban de nuevo al terminar; si cambiaron no se cambia la selección ni se
reconoce silenciosamente con otra. La maximización se conserva al volver.

Fuentes oficiales consultadas:

- [Xlib, §12 Keyboard Grabbing](https://www.x.org/releases/current/doc/libX11/libX11/libX11.html#Keyboard_Grabbing):
  `XGrabKey`, condiciones de foco respecto al root, `BadAccess`, `XUngrabKey`.
- [Xlib, Handling Protocol Errors](https://www.x.org/releases/current/doc/libX11/libX11/libX11.html#Handling_Protocol_Errors)
  y [Handling the Output Buffer](https://www.x.org/releases/current/doc/libX11/libX11/libX11.html#Handling_the_Output_Buffer):
  `XSetErrorHandler` y `XSync` para comprobar errores de registro.
- [QSocketNotifier](https://doc.qt.io/qtforpython-6.8/PySide6/QtCore/QSocketNotifier.html):
  integración de descriptores con el bucle de eventos Qt.
- [QKeySequenceEdit](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QKeySequenceEdit.html):
  registro local de una combinación en el campo, limitado a una secuencia.

## Evidencia y límites de validación

Sesión declarada por el entorno: `DISPLAY=:0`, `XDG_SESSION_TYPE=x11`, KDE.
RPM Spectacle `6.7.5-1.fc44`; libX11 `1.8.13-3.fc44.x86_64`.
`xdpyinfo -display :0` falla con `unable to open display` desde este entorno.
Un intento de Xorg dummy aislado en `:109`, sin tocar la sesión del usuario,
falló al crear sockets de escucha. No quedó un servidor ejecutándose. No se
puede acreditar registro real, conflicto real ni captura global desde otra
aplicación. La prueba manual anterior de captura/MangaOCR y consulta JMdict sigue
siendo evidencia de esos recorridos anteriores, no del atajo nuevo.

`QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest tests.test_hotkey -v`:
pruebas con XDG aislado, backend X11 simulado, eventos de protocolo simulados y
captura PNG sintética. Cubren persistencia/reapertura, cambio/desactivación/cierre,
Restaurar sin activar, error de escritura, conflicto/rollback parcial, plataforma
no compatible, repetición, foco de otra aplicación, motor no listo, cancelación
antes/durante captura y no traducir/cambiar motor. La carga real de libX11 y el
error de apertura de un display inexistente también se comprobaron. Estas pruebas
no son registro global real, inferencia OCR ni captura interactiva. El recorrido
1–7 es la revisión pendiente en el escritorio del usuario.

Comprobación adicional: `.venv/bin/python -m tools.hotkey_flow_smoke` inyectó la
activación y la imagen de captura (`examples/nihon.png`) y ejecutó **Tesseract real**
mediante el worker normal. Detección/prueba reales: Tesseract 5.5.3 listo; OCR jpn
produjo **日本** tanto en original como en editor, sin iniciar Argos. Se inspeccionó
la pestaña de preferencias en `/tmp/HISTORICAL-REVIEW`, renderizada
offscreen. La activación y captura de esa prueba son inyectadas: no valida el
atajo global ni Spectacle interactivo. Las pruebas unitarias también comprueban
la selección MangaOCR (worker y japonés fijo, con estado listo simulado) y que un
cambio de idioma durante la captura impide el OCR automático.

Resultado final: **13 pruebas nuevas aprobadas**, más **9 regresiones dirigidas**
de procesos y consulta de selección aprobadas. También se cubre el fallo al
guardar una desactivación: se libera el atajo de esta sesión y se advierte que
al reabrir podría volver la preferencia anterior si no se pudo escribir en disco.


## Acciones de popup y captura-copia

Los cuatro atajos de **Integraciones → Acción** son Capturar y copiar, Translator,
OCR Phrase y Abrir ventana principal. Cada uno conserva configuración independiente.
El atajo anterior de captura gráfica queda en Detalles → Compatibilidad, sin
migración de sus claves ni cambios en su recorrido. Se rechazan combinaciones
duplicadas entre las cinco entradas. No se modifican los atajos del sistema.
Script, acceso directo, menú y atajo despachan la misma acción interna.

La guía vigente de configuración, scripts y revisión está en
[INTEGRATIONS.md](INTEGRATIONS.md). La reorganización de GUI no acredita el registro
global: el probe real de esta revisión tampoco pudo abrir `:0`. [Evidencia nueva](evidence/integrations/README.md).
Se conservan arriba las APIs y los diagnósticos históricos; las pruebas anteriores
con eventos inyectados siguen sin equivaler a registro o activación global real.
