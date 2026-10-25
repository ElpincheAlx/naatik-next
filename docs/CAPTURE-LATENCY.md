> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Latencia de captura: medición y cambios

## Alcance y resultados

Referencia anterior: commit `a63d1ad`. La referencia se extrajo a un directorio
nuevo en `/tmp`; no se modificaron otros proyectos ni la copia de validación.
Se ejecutó el mismo `tools/benchmark_capture_latency.py` contra ambas fuentes,
con MangaOCR 0.1.16, Torch 2.13.0, CPU y dos hilos; Python 3.14.8 y PySide6 6.11.1.
Se conservaron el intérprete, snapshot e idioma explícitamente configurados.
No se instaló ni descargó nada ni se cambiaron los valores por defecto de Next.

Imagen fija del repositorio: `examples/nihon.png`. **24/24 resultados anteriores
y 24/24 posteriores coinciden con el resultado esperado**, sin recortar ni
normalizar texto para la comparación. Los datos numéricos, versiones y hash de
la imagen están en [capture-latency.json](evidence/capture-latency.json).

Se usa Qt offscreen. El selector entrega esa imagen tras un QTimer solicitado
de 150 ms: su tiempo real se registra aparte (aproximadamente 143–158 ms).
La recepción IPC es una llamada inyectada al handler. **No son tiempos de
Spectacle interactivo, del socket Unix con nombre ni de pegado en otra aplicación.**
El estado XDG es temporal, con diccionarios vacíos; no se midió el catálogo real
del usuario. No se vació la caché de disco del sistema entre ejecuciones.

Tiempos en ms: **mediana [mínimo, máximo]**. El total incluye la selección
inyectada; no se suman etapas que se solapan.

| Recorrido | n antes/después | Antes | Después |
|---|---:|---:|---:|
| Next cerrado: nuevo proceso Python → portapapeles | 3/3 | 4316,5 [4281,1–4332,6] | 3543,1 [3537,1–3545,9] |
| Primera captura con Next abierto y motor preparado | 3/3 | 737,9 [730,6–753,9] | 448,8 [445,1–453,9] |
| Capturas sucesivas con motor residente | 18/18 | 741,2 [707,6–767,9] | 446,3 [431,2–457,8] |
| Nuevo proceso → invocación del selector inyectado | 3/3 | 3863,8 [3840,7–3893,5] | 204,5 [202,8–205,4] |
| Comprobación real `spectacle --version` + `--help`, sin selector | 5/5 | 422,0 [416,7–486,0] | 0,002 [0,0017–0,0021] con caché |

La última fila es una medición **independiente** de los ensayos con selector
inyectado. La primera comprobación del proceso sigue costando lo mismo: se
elimina su repetición, no se elimina la comprobación. No se ha medido cuánto
mejora el recorrido completo de captura real.

La inferencia residente no presenta una mejora relevante: el recorrido de
worker OCR sigue alrededor de 290–300 ms. El ahorro demostrado está antes de la
inferencia. Una captura adicional con instrumentación interna midió preparación
inicial de motor de 3038 ms e inferencias de 276–279 ms: son una carga y cuatro
inferencias, no otra serie comparable de frío. No se promete respuesta inmediata.

## Cuellos de botella comprobados

1. El arranque esperaba `detect_task` y la carga/prueba de MangaOCR antes de
   consumir la captura externa. El código recorría también los motores no
   seleccionados. En la medición inicial, la preparación/prueba MangaOCR ocupó
   unos 3,3–3,6 s antes de permitir invocar el selector.
2. Cada captura añadía un temporizador fijo de 300 ms incluso con la aplicación
   ya oculta. Las medidas residentes muestran ese intervalo antes del selector.
3. El worker de captura era nuevo cada vez y consultaba las dos opciones de
   Spectacle en cada captura: aproximadamente 422 ms adicionales en esta máquina,
   medidos por separado sin abrir selector.
4. Argos no era un requisito explícito del ACK, pero su detección se lanzaba al
   arranque gráfico y podía competir por recursos. En captura-copia ya se omitía.
   El modelo MangaOCR ya era residente entre capturas: no se atribuye a este
   cambio una reutilización que ya existía.

## Implementación

- El arranque prepara únicamente el OCR seleccionado. MangaOCR carga una vez
  en su worker CPU, sin reconocer además una muestra antes de la primera captura.
  Tesseract comprueba ejecutable e idiomas sin una inferencia sintética previa.
  **Volver a detectar y probar** mantiene las pruebas explícitas y la detección
  completa. Si el intérprete no cambia, esa acción tampoco mata un modelo
  residente para cargarlo otra vez. Si cambian los metadatos de archivos del
  modelo en la misma ruta, la preparación invalida esa instancia y lo recarga.
- El selector se solicita mientras se prepara el motor. Si la región llega antes,
  queda en el temporal privado hasta terminar la preparación. Solo entonces se
  inicia su OCR. Se preservan identidad de preparación, generación OCR y captura
  única; cancelar borra la petición/imagen pendiente e invalida respuestas tardías.
- Captura y OCR conservan sus workers. La comprobación de Spectacle se guarda
  dentro del worker y se invalida por ruta, modificación o tamaño del ejecutable.
  Tesseract conserva el supervisor Python, pero su CLI arranca un proceso de
  Tesseract por imagen; no se afirma que sus pesos queden residentes.
- Se sustituye la espera de 300 ms por una vuelta al bucle Qt tras ocultar la
  ventana. Debe comprobarse en el escritorio real que el recorte no incluya Next;
  offscreen no acredita la sincronización del compositor.
- Captura-copia no abre la base de diccionarios ni inicia Argos. La GUI prepara
  Argos después del motor elegido, o después de la primera captura pendiente.
  Los callbacks de ventanas cerradas no pueden iniciar tareas ni persistir
  preferencias. Las pruebas se ejecutan además dentro de un perfil XDG exterior
  temporal para contener callbacks que escapasen a un fixture.
- No cambian idioma, modelo, calidad, GPU, texto ni política de copia. Continúan
  los flujos gráficos de consulta y la copia explícita de `--capture-copy`.
  No se añaden servicios, dependencias ni tareas de inicio automático.

## Medir una captura real

Después de cerrar una instancia anterior a esta actualización:

```bash
${PROJECT_ROOT}/launch --capture-copy --timings
```

**La primera terminal queda ocupada:** esa instancia permanece residente para
conservar el modelo, recibir IPC y mantener la propiedad del portapapeles.
No pulses Ctrl+C entre capturas. Después de terminar la primera captura, abre
**otra terminal** y ejecuta tres veces este comando, esperando que cada OCR
termine antes de solicitar el siguiente (también puedes usar Stream Deck):

```bash
${PROJECT_ROOT}/launch --capture-copy --timings
```

Las llamadas posteriores envían IPC y terminan; la primera instancia sigue viva.
Usa la misma imagen/región, motor, idioma y configuración. Resume mientras el
propietario sigue abierto. Para botón y atajo, abre:

```bash
${PROJECT_ROOT}/launch --timings
```

`--timings` también habilita el registro en una instancia ya abierta por el
protocolo local cerrado: solo añade el booleano opcional `timings: true`, nunca
rutas ni código. Los workers ya residentes reciben la activación en la siguiente
petición. El registro permanece activo hasta salir y reiniciar sin la opción.
No se persiste como preferencia. Para medir frío real, cierra expresamente Next
entre muestras; para primera captura abierta, inicia la GUI, espera preparación
y pulsa una vez. No mezcles esas series al resumir.

Registro privado: `$XDG_STATE_HOME/naatik-next/capture-timings.jsonl` (por defecto
`~/.local/state/naatik-next/capture-timings.jsonl`). Solo contiene etapa de una
lista cerrada, identificador aleatorio, PID y reloj monótono. No añade imágenes,
texto OCR, portapapeles, coordenadas, rutas de imágenes ni payloads IPC al registro.
Los temporales necesarios para OCR conservan el ciclo de limpieza existente.

Para resumirlo:

```bash
cd ${PROJECT_ROOT}
.venv/bin/python tools/capture_timings.py --last-process
```

`--last-process` limita la salida al propietario de la petición más reciente;
evita mezclar esa serie con ejecuciones anteriores del registro. Sin esa opción
se muestra todo el historial. Los registros antiguos sin evento `interrupted`
no permiten reconstruir retrospectivamente una interrupción: no los uses como
muestras comparables del incidente.

Se registran inicio/importación del proceso, recepción IPC, petición aceptada,
preparación/invocación del selector, captura terminada, preparación/carga de motor,
inferencia y escritura en el portapapeles. El inicio se marca al entrar al módulo
Python de Next, antes de importar Qt; no mide el arranque previo del shell o del
intérprete. El benchmark de procesos nuevos sí mide desde antes de `Popen`.
Si se habilita en un proceso existente, no reconstruye etapas pasadas.
`process_to_request_ms` es la edad del proceso al pedir la captura: en una GUI
abierta puede incluir tiempo ocioso, no es necesariamente tiempo de arranque.

`selection_window_ms` comprende inicio de Spectacle, presentación y tiempo humano
hasta cerrar el selector. **No se atribuye todo ese intervalo al programa ni todo
al usuario.** Solo durante ese intervalo y solo con diagnóstico habilitado, un
subproceso del worker consulta Button1 mediante XQueryPointer cada ~10 ms para marcar
el arrastre. No registra coordenadas, movimiento, teclas ni contenido, no toma un
grab y se espera su salida al cerrar el selector (con terminación acotada si no responde). `drag_ms` separa ese arrastre aproximado;
el tiempo pensando antes de pulsar no se puede distinguir de la preparación de
la interfaz con esta integración. Sin display o sin observar el arrastre, figura
`null`, nunca un cero inventado. Las etapas se solapan: no deben sumarse para
estimar el total. `clipboard` confirma la llamada Qt, no valida el pegado externo.

Reproducción del ensayo automatizado (lee el motor explícitamente configurado,
usa solo la imagen del repositorio y perfiles XDG temporales):

```bash
.venv/bin/python tools/benchmark_capture_latency.py --runs 3 --resident 3 --output /tmp/HISTORICAL-REVIEW
```

## Validación

Suite completa: **125 pruebas, OK**, ejecutada dentro de un perfil XDG exterior
temporal; se comprobó que no cambiasen las huellas del perfil real ni del script
no versionado. Cobertura nueva: preparación paralela a selector en los tres
recorridos, una sola inferencia, imagen pendiente, cancelación, respuesta de
preparación obsoleta incluso al cambiar de motor, caché de modelo sin probe, ausencia de base/Argos en modo
silencioso, privacidad de eventos, diagnóstico IPC cerrado y muestreo inyectado
del arrastre. Se conservan las pruebas de errores, vacío, copia y respuestas OCR
obsoletas anteriores.

Se ejecutó también MangaOCR real en CPU: cancelar durante carga con región
inyectada, descartar una respuesta de preparación obsoleta, volver a cargar bajo
demanda y reutilizar el PID en la captura siguiente: PASS. Eso no valida captura
real ni foco. Tesseract real también conservó el OCR de la misma imagen y el
PID de su supervisor entre dos solicitudes: PASS. Quedan pendientes selector al soltar, monitores/escalado,
compositor, socket por nombre, foco y pegado externo en KDE/X11.

Referencias de APIs existentes:
[QTimer](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QTimer.html),
[Xlib y XQueryPointer](https://www.x.org/releases/current/doc/libX11/libX11/libX11.html).

## Cierre durante diagnóstico

El propietario se cierra expresamente al salir de la GUI o con SIGINT/SIGTERM.
Tras completar las cuatro capturas, puedes abrir la GUI mediante
`${PROJECT_ROOT}/launch` y cerrarla. Cerrar el propietario puede perder la selección
del portapapeles X11 si no existe un gestor que la conserve: pega antes de salir.
Una señal durante una operación marca `interrupted`; errores, cancelaciones,
interrupciones y muestras incompletas quedan fuera de los resúmenes. Sus totales
aparecen como `null`, aunque hubiera un evento de portapapeles. Una captura ya
terminada no se invalida por cerrar posteriormente una instancia ociosa.

El incidente comunicado (selector 513,813 ms, preparación 3075,889 ms,
captura 3908,708 ms, inferencia 430,083 ms, total 4346,108 ms y `successive n=0`)
incluye interrupciones y no constituye una comparación de rendimiento ni una
serie residente. No se incorpora al benchmark anterior. El cierre se investiga
por separado en [SHUTDOWN.md](SHUTDOWN.md).
