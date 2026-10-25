> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Stream Deck / StreamController

## Crear y asignar el script

1. Abre `${PROJECT_ROOT}/launch`. Si la aplicación estaba abierta antes de esta
   actualización, ciérrala y ábrela una vez para iniciar el nuevo canal local.
2. En **OCR**, selecciona el motor y espera a que esté listo. Esa selección
   se conserva; el script no fija un motor, idioma ni ruta de traducción.
3. En **Integraciones**, selecciona **Acción → Capturar y copiar** y pulsa **Crear script…** y elige
   la carpeta y el nombre. Se crea ejecutable, con permisos 0700. Si ya existe,
   se pide confirmación. No se sobrescriben enlaces simbólicos ni el lanzador.
4. **Copiar ruta** copia la ruta absoluta; **Abrir carpeta** abre su ubicación.
   **Copiar comando** incluye el quoting completo. No añadas más comillas. Esto sirve
   también para nombres con espacios, apóstrofes, `$`, Unicode y otros caracteres.
5. En StreamController elige el botón del deck y añade **OS → Run Command**
   (Ejecutar comando). Pega ese comando. Activa **Detached / Separado** y deja
   **Auto run every** en **0**; no necesitas una acción que simule un atajo.
   Si falta OS, su instalación corresponde al usuario: Next no instala plugins.
6. Da el foco a otra aplicación y pulsa el botón. Solo aparece el selector de
   región: arrastra y suelta para reconocer y copiar con el OCR elegido. La copia
   es explícita incluso si la preferencia automática está desactivada. No abre la
   ventana principal, no consulta diccionarios ni traduce. Pega tú el texto en la
   aplicación de destino; Next no simula teclas ni pega automáticamente.

En esta máquina se inspeccionaron, sin ejecutar ni modificar, StreamController
Flatpak **1.5.0-beta.16** y OSPlugin (manifest **1.0.0**, VERSION registrado
`b7c719b2ec7e9424cf182d7682c3189772f4dbd2`). El código local de RunCommand incluye
Detached y la ejecución en el host mediante `flatpak-spawn --host` cuando se usa
Flatpak; no hay que añadir ese prefijo por duplicado. No se ha probado un botón
físico ni su acceso al host. Fuente de referencia:
[OSPlugin / RunCommand oficial](https://github.com/StreamController/OSPlugin/blob/main/actions/RunCommand/RunCommand.py).
La versión local puede diferir del código upstream actual. Si el host no es
accesible desde tu instalación, revisa el error de StreamController; Next no cambia
permisos, configuración de Flatpak ni servicios automáticamente.

También puede invocarse directamente, desde cualquier directorio:

```bash
/historical-home/Naatik-next/launch --capture-copy
```

El script generado contiene exports de las raíces XDG y del runtime usados al
crearlo y una única llamada `exec` al lanzador absoluto con `--capture-copy`. Así
apunta al mismo perfil aunque el ejecutor aporte otras variables XDG. Lee las
preferencias actuales en cada apertura, no una copia del motor elegido al crear
el script. Si mueves Next o cambias deliberadamente de perfil XDG, regenera el
script. No contiene bucles, recursión, HTTP ni simulación de teclas.

## Instancia única y arranque

El lanzador acepta `--capture-copy` y `--capture` (mutuamente excluyentes),
además de `--help`. Sin argumentos abre o muestra la instancia existente.
`--capture-copy` envía **capturar y copiar en segundo plano**. `--capture`, el
atajo global y **Seleccionar región** conservan el flujo gráfico con OCR, copia
según preferencia y consulta exacta automática.

Si Next está cerrado, `--capture-copy` inicia el propietario del canal y el bucle
Qt sin mostrar la ventana ni el asistente inicial. Solo prepara el OCR seleccionado, sin inferencia de prueba redundante; no abre
la base de diccionarios ni descubre rutas Argos. El proceso permanece vivo tras acabar o cancelar: es propietario
del portapapeles y atiende nuevas peticiones, sin depender de que Klipper lo
conserve al salir. Una invocación normal del lanzador abre esa misma instancia.
Cerrar expresamente su ventana después de abrirla, o **Salir de Next** en el
menú de bandeja cuando esté disponible, termina el proceso. No hay servicio,
autostart ni instalación en segundo plano.

Si la ventana ya estaba visible, se oculta únicamente durante la selección y se
restaura al obtener la región, con su estado previo (incluido minimizado), sin
`raise_` ni `activateWindow`, usando `WA_ShowWithoutActivating` y sin solicitar
`WindowActive`. No se vuelve a mostrar al terminar OCR. Si estaba oculta, sigue
oculta. El editor, el original OCR y los paneles de resultados anteriores quedan
intactos. Las regiones temporales se eliminan al completar o cancelar.

Si falta preparar motor/idioma/modelo o falla OCR, se informa mediante una
notificación de bandeja de Qt y log, sin diálogo modal ni apertura automática.
Pulsar la notificación o **Abrir Configuración** en el menú de bandeja es una
acción explícita que abre la configuración. La presentación de notificaciones
está sujeta al escritorio. Sin notificaciones, se puede abrir siempre el
lanzador normal para configurar. Esc/cancelación no muestra aviso. Error o texto
vacío conserva el portapapeles; resultados tardíos de trabajos cancelados tampoco
lo sobrescriben. La copia válida se realiza en el hilo Qt principal.

### Regenerar un script anterior

Next no modifica scripts existentes al actualizarse, incluido un script guardado
junto al repositorio. Abre **Integraciones**, selecciona **Capturar y copiar** y pulsa **Crear script…**, elige un archivo nuevo o confirma explícitamente sobrescribir el
anterior. Copia otra vez **Copiar comando** y actualiza la
acción **OS → Run Command** del botón de StreamController. Mantén
**Detached/Separado** activado y repetición en **0**. Si conservas la misma ruta,
el botón usará el nuevo contenido; si cambias la ruta, debes actualizarlo.
No se editan botones ni scripts externos automáticamente.

`QLockFile` elige un único propietario antes de construir la ventana o iniciar
workers. El propietario abre `QLocalServer`; los demás usan `QLocalSocket`, esperan
respuesta y terminan. Si el propietario aún arranca, los clientes reintentan
hasta 15 segundos con el mismo ID; no abren una segunda ventana. Si falta el canal
(por ejemplo, una versión antigua aún abierta), se informa en stderr/log para
captura-copia y en GUI/log para el flujo normal. No se elimina su bloqueo. Cierra/reabre Next para actualizar una instancia antigua.

Las peticiones de captura que llegan durante la detección inicial se agrupan en
una pendiente hasta iniciar la preparación del OCR seleccionado. El selector
puede ejecutarse durante esa carga: la región espera al motor con identidad
y cancelación controladas. No espera a detectar todos los motores. La aceptación no espera
a cargar modelos: se confirma **queued**. Si el motor seleccionado no queda listo,
la acción de copia notifica con acceso a Configuración y no cambia de motor.
Cancelar operaciones descarta también esa petición pendiente. Si hay captura/OCR activo, las repeticiones se ignoran sin
encolar una captura para después. Los diálogos modales también impiden iniciar
otra captura. Cancelar la selección conserva imagen, original, correcciones y
resultados de diccionario, y permite solicitar otra captura.

Canal: socket Unix con nombre, `UserAccessOption`, directorios propios 0700.
Usa `$XDG_RUNTIME_DIR/naatik-next/ipc/<hash-del-state>.sock`; si el runtime no es
utilizable, el fallback es `$XDG_STATE_HOME/naatik-next/ipc/<hash>.sock` (o la raíz
XDG predeterminada). No usa `/tmp` para el canal normal. La ruta tiene límite por
Unix; si es demasiado larga se informa. Solo el propietario del bloqueo puede
retirar un socket obsoleto propio; no se retiran archivos normales ni enlaces.

Protocolo JSON cerrado v1: ID hexadecimal de 32 caracteres y acción `capture`,
`capture-copy` o `show`, una trama por conexión, hasta 160 bytes. Sin rutas, texto OCR, motor,
argumentos de shell ni comandos arbitrarios. Hay plazos de lectura, límites de
conexiones y caché acotada de IDs para no ejecutar de nuevo una retransmisión.
El ACK confirma recepción/cola/estado, no que la captura ya haya concluido.
El canal se cierra y libera antes del bloqueo al salir. El propietario Qt puede permanecer sin ventana para conservar el portapapeles.
No es una cola durable frente a un cierre forzado del sistema.

APIs oficiales consultadas:
[QLocalServer](https://doc.qt.io/qtforpython-6/PySide6/QtNetwork/QLocalServer.html),
[QLocalSocket](https://doc.qt.io/qtforpython-6/PySide6/QtNetwork/QLocalSocket.html),
[QLockFile](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QLockFile.html).
Solo se usan sockets locales; importar QtNetwork no activa servicios HTTP/TCP.
La captura sigue limitada al adaptador KDE/X11/Spectacle comprobado previamente;
no se acredita soporte Wayland.

## Validación y recorrido manual pendiente

**Suite completa: 111 pruebas, OK.** Pruebas dirigidas offscreen:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest \
  tests.test_integrations tests.test_instance tests.test_hotkey \
  tests.test_processes tests.test_selection_lookup tests.test_capture_copy -v
```

- Generación ejecutable, quoting, directorio de trabajo ajeno y perfil XDG fijado;
  confirmación/rechazo de sobrescritura, enlaces, copiar ruta, abrir carpeta y
  persistencia de la ruta. El lanzador destino de la prueba de quoting es un
  ejecutable de prueba que registra argumentos, no el motor OCR.
- Inicio abierto/cerrado del `main` con controlador de instancia simulado;
  peticiones antes de conectar el handler y durante detección, coalescencia,
  motor no listo, reintentos con ID estable, timeout sin duplicar y liberación
  del bloqueo al fallar el registro.
- Transporte **QLocalSocket real sobre socketpair Unix heredado**, incluyendo
  intercambio cliente/servidor en procesos separados. Tramas fragmentadas,
  sobredimensionadas, desconocidas y retransmisión del mismo ID. Esto prueba el
  protocolo/transporte conectado, **no** `listen/connectToServer` por nombre.
- Elección **QLockFile real entre cinco procesos simultáneos**: un solo ganador.
  Esto no equivale por sí solo a cinco invocaciones completas de la GUI.
- Cancelación/nueva captura y exclusión durante OCR; regresiones del atajo y
  botón anterior. La captura de estas pruebas es sintética/inyección, sin nueva
  inferencia ni captura interactiva.

Limitación del entorno: `QLocalServer.listen` falla (`Unknown error 1`) por la
restricción de creación/bind de sockets con nombre, y `:0` tampoco es accesible.
No se declara verificado el recorrido completo de aplicación abierta/cerrada,
registro del socket con nombre, captura interactiva ni botón físico. Los tests
usan transporte heredado o simulación donde se indica. Las pruebas offscreen
limpian expresamente los DeferredDelete de Qt entre casos.

### Evidencia de captura-copia

`tests/test_capture_copy.py` inyecta región y OCR para comprobar instancia abierta
u oculta, estado minimizado, ausencia de activación explícita, copia con preferencia
desactivada, ambos motores, errores/vacío/cancelación y errores tardíos sin diálogos,
repeticiones, cola inicial y apertura posterior. Vigila que no se inicien consultas
ni traducción y que el editor y los paneles previos no cambien.

Un subproceso real con QApplication offscreen ejecuta el arranque `--capture-copy`,
comprueba que la ventana sigue oculta al acabar, mantiene el bucle Qt y el texto
del portapapeles, y abre después la GUI. El broker IPC y el OCR están inyectados
en esa prueba. El protocolo nuevo se prueba también sobre sockets Unix heredados;
la elección del bloqueo entre procesos se conserva de las pruebas existentes.
La prueba de quoting ejecuta un lanzador de prueba con `--capture-copy`, no OCR.

Esto no acredita captura real al soltar, entrega de notificaciones KDE, foco de
otras aplicaciones ni pegado X11. El socket Unix con nombre no se ha validado en
este entorno restringido; no se usa el transporte inyectado en producción.

Prueba manual en KDE/X11:

1. Con Next cerrado, enfoca un editor y ejecuta el botón actualizado. Delimita una
   región y suelta; debe verse solo el selector y poder pegarse el OCR en ese
   editor después de que termine, sin cambiar foco ni aparecer Next.
2. Repite varias veces rápidamente: solo una captura debe estar activa. Abre
   después el lanzador normal: debe mostrar la misma instancia. Repite con Next
   visible, oculto y minimizado; su estado debe restaurarse sin activarlo.
3. Desactiva la copia automática en preferencias y repite: esta acción sigue
   copiando. Copia un testigo, cancela con Esc y prueba una región sin texto y un
   fallo OCR: debe poder pegarse todavía el testigo. Comprueba que los paneles de
   editor, diccionario y traducción previos no se modifican.
4. En un perfil propio sin OCR preparado, solicita captura-copia: debe aparecer
   un aviso con acceso a Configuración, sin abrir la GUI hasta pulsarlo. Tras
   configurar, solicita captura-copia de nuevo.

APIs de Qt usadas dentro de las dependencias existentes:
[QSystemTrayIcon](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QSystemTrayIcon.html),
[QGuiApplication.quitOnLastWindowClosed](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QGuiApplication.html#PySide6.QtGui.QGuiApplication.quitOnLastWindowClosed).

Diagnóstico opcional sin contenido y mediciones antes/después: [CAPTURE-LATENCY.md](CAPTURE-LATENCY.md).

### Instancia residente y terminales

La primera ejecución de `${PROJECT_ROOT}/launch --capture-copy --timings` permanece
en ejecución, aunque solo veas el selector: conserva el motor y el portapapeles.
Para pedir más capturas, usa **otra terminal** o el botón de Stream Deck; las
llamadas posteriores envían IPC al propietario y terminan. Espera a que acabe el
OCR antes de volver a pulsar. No uses Ctrl+C para pasar a la captura siguiente.
Para abrir la GUI de esa misma instancia, ejecuta `${PROJECT_ROOT}/launch`.

SIGINT/SIGTERM solicitan un cierre único y ordenado, incluso repetidos; una
captura interrumpida no es una muestra de rendimiento. Consulta el recorrido de
frío y tres capturas residentes en [CAPTURE-LATENCY.md](CAPTURE-LATENCY.md) y la
evidencia y límites del cierre en [SHUTDOWN.md](SHUTDOWN.md). El script externo
existente se conserva sin editar; esta corrección no requiere regenerarlo.


## Translator y OCR Phrase separados

En Integraciones el selector **Acción** incluye **Translator**, **OCR Phrase** y
**Abrir ventana principal**, con configuraciones independientes de atajo, script y
acceso directo. Comando completo y perfil están plegados en **Detalles**; la ayuda
externa está en **Cómo configurarlo**. [Guía vigente](INTEGRATIONS.md). Ambos reciben el
portapapeles; no capturan. Asigna cada comando a un botón distinto con Detached.
No sustituyen el botón de captura-copia ni lo modifican. Para iniciar Next cerrado
mediante el teclado, puedes asignar esos scripts/accesos desde Atajos de KDE;
los cuatro atajos internos separados requieren una instancia residente. No dupliques
la misma combinación en KDE y en Next. Recorrido completo y preparación:
[POPUPS.md](POPUPS.md). El script externo existente no se ha regenerado.
