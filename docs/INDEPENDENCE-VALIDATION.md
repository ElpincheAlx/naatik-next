> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Auditoría e instalación independiente — 2026-10-19

Última evidencia: **PASS/0 externo** de instalación pública y MangaOCR CPU propio.
Ver [EXTERNAL-PUBLIC-INSTALL-PASS.md](EXTERNAL-PUBLIC-INSTALL-PASS.md). Máquina
limpia e interacción gráfica de esa copia siguen pendientes. El texto siguiente
conserva los intentos y bloqueos anteriores como historia, no como estado actual.
No se modifica JapaneseMining, su Python, datos ni servicios. El alcance futuro
confirmado se mantiene en AGENTS.md; no se incorporó análisis/Anki/móvil aquí.

## Dependencias del equipo identificadas y tratamiento

| Hallazgo | Tipo | Tratamiento |
|---|---|---|
| Default MangaOCR buscaba `${REFERENCE_ROOT}/.venv-mangaocr` | Entorno externo heredado | Eliminado el fallback; `.venv-mangaocr` propio y lock CPU |
| Default buscaba refs/snapshots en caché global Hugging Face | Recurso compartido implícito | Eliminado; modelo XDG propio, selección explícita o descarga confirmada |
| Detección Paddle inspeccionaba entornos del proyecto antiguo | Evidencia heredada no funcional | Eliminada; sigue pendiente, sin afirmar inferencia |
| `.desktop` versionado contenía `/historical-home` | Ruta personal | Plantilla `.desktop.in`; el instalador genera solo la entrada XDG |
| Workers dependían del cwd del proceso padre | Supuesto de ejecución | QProcess fija directorio del código; launch resuelve ubicación |
| Python 3.14/venv/pip y Qt nativo | Sistema/base propia | Se exige plataforma del lock, venv sin system-site-packages, hashes |
| Tesseract/datos de idiomas, Spectacle, libX11 | Sistema opcional según función | Diagnóstico y pruebas; no se empaquetan ni sustituyen |
| Fuentes de Qt y fuente de prueba de Pillow | Sistema / paquete base | No se copia una fuente personal |
| Modelos Argos/diccionarios actuales | Recursos opcionales del usuario | Sin importación automática; en perfil nuevo faltan y se informa |
| Stanza, diagnóstico oficial Argos, ZIP/DB de pruebas | Solo pruebas/diagnóstico | No se convierten en dependencias nuevas de ejecución |
| Paths históricos en docs/evidencias | Evidencia de desarrollo | Se conservan como historia, no defaults de producto |

Las preferencias existentes tienen `manga_python` y `manga_model` explícitos:
se respetan. No se reescribieron sus valores ni se migraron recursos. Una persona
nueva no necesita ese árbol. Un perfil antiguo solo queda completamente autónomo
cuando su usuario elija recursos propios; no ocultamos esa diferencia.

## Ejecución aislada real

Área: `~/Naatik-validation/independent-install/Next con espacios` y HOME nuevo
`…/home-review2`. Código copiado sin entornos, ruedas ni datos de usuario.
Se creó una venv nueva Python 3.14 sin system/user site packages; instalación base
por lock/hash desde **las 17 ruedas necesarias de `.wheelhouse`**, sin recurrir a
JapaneseMining. Se instaló la entrada de menú solo en HOME de revisión.

`tools/independent_smoke.py` exige marca explícita de revisión y HOME de prueba;
no debe ejecutarse en un perfil normal. Con entorno mínimo `env -i`, PATH del
sistema, Qt offscreen y sin modelos precargados:

- Primer inicio muestra asistente, MangaOCR informa recursos faltantes, Argos sin
  rutas y diccionarios vacíos; defaults propios sin referencias al árbol antiguo.
- Elección explícita Tesseract/eng; guarda y redetecta.
- Worker real Tesseract sobre muestra sintética `examples/hello.png`: **Hello world**.
  El event loop Qt siguió atendiendo eventos durante los trabajos.
- Cierra/abre: recupera idioma/motor y no vuelve a mostrar el asistente completado.
- Intento real de descargar primer archivo: DNS `Temporary failure in name resolution`.
  Error comprensible; no se acredita descarga ni modelo listo.
- `launch --help` desde `/tmp`: correcto. Instalación/eliminación de menú desde
  otro cwd y ruta con espacios: correctas; preferencias aisladas conservadas.
- SHA-256 de preferencias, base de diccionarios y entrada de menú normales iguales
  antes/después de la prueba aislada. Sin escritura en el perfil real.

Evidencia de salida: [independent-install-evidence.json](independent-install-evidence.json).
Esta prueba **no es una VM ni un equipo limpio**: Tesseract, datos de idioma,
Python y bibliotecas Qt/xcb/OpenGL/glibc siguen siendo los del host Fedora 44.

## Runtime CPU y modelo

Cierre de 43 paquetes a partir de METADATA/Requires-Dist, con selección por tags
cp314 y dependencias aplicables. Torch CPU cp314 no estaba disponible localmente;
para su cierre se contrastó el METADATA CPU cp313 2.13.0 disponible, quedando la
comprobación del METADATA/binario cp314 pendiente. El hash cp314 se tomó de su
entrada exacta en el índice oficial conservado en caché, contrastando además la
existencia de ese archivo en el índice oficial vía web. No se usó la rueda cp313
como binario cp314. No se instaló la variante CUDA ni se copió un site-packages.

Intento offline del instalador CPU en la copia aislada: falla explícitamente por
`torch-2.13.0+cpu-cp314-cp314-manylinux_2_28_x86_64.whl` ausente. El intérprete propio
creado queda sin acreditar; no usa el entorno antiguo. Intentos HTTPS a PyPI,
Hugging Face y PyTorch desde este entorno fallaron por DNS. Por ello no se acredita
instalación/inferencia del nuevo cierre CPU, aunque el adaptador se hubiera probado
antes con otro runtime.

Modelo: catálogo con revisión fijada, tamaños y SHA-256 del snapshot local
previamente auditado. La licencia Apache-2.0 se verificó en la ficha **del modelo**,
no se dedujo de MangaOCR. No se copian pesos a Git ni al perfil normal.
El descargador solo acepta el catálogo cerrado, limita bytes/timeout, comprueba
SHA-256 y usa `.part` para recuperar interrupciones; no ejecuta código del modelo.
El worker ya rechaza `auto_map`, usa modo offline y exige inferencia 日本 para Listo.

## Pruebas y límites

Suite automatizada: 76 pruebas pasan. Ocho regresiones nuevas verifican defaults
sin legado, fallo de red, reanudación Range, segundo uso sin red, servidor que
ignora Range, integridad, límites de tamaño, ruta peligrosa, cancelación conservando
parcial y exclusión de preparaciones concurrentes (algunas pruebas cubren varios
casos). Transporte **inyectado**, no descarga real exitosa. La suite restante cubre
supervisión/cancelación/cierre, OCR original/correcciones, selección, importación,
IPC y atajo con el alcance ya documentado. No se repitió la importación masiva de
ZIP ni pruebas pesadas de modelos sin cambios en esas funciones.

`xdpyinfo -display :0` volvió a fallar: unable to open display. La GUI se comprobó
**offscreen**; no se acreditan captura interactiva, registro global, foco, entrada
del menú activada ni conexión IPC real del escritorio en este paso.

Gates pendientes concretos:

1. Conseguir la rueda CPU cp314 cuyo hash está fijado, instalar el lock, `pip check`,
   importar y reconocer con el worker y modelo propios; comparar su salida real.
2. Descarga completa y reanudación reales desde Hugging Face; los tests de protocolo
   no equivalen a éxito del proveedor/CDN.
3. Instalar en máquina/VM limpia y confirmar paquetes nativos de Fedora y apertura
   del menú. Otras plataformas/arquitecturas siguen sin acreditación.
4. Escritorio KDE/X11 real: captura/cancelación, atajo desde otra app e IPC/Stream Deck.
5. Preparación gráfica de modelos Argos y GPU no implementadas. Recursos de terceros
   sin permisos aclarados siguen siendo importados por el usuario, sin bundle.

Corrección del cierre durante la auditoría: UniDic Lite 1.0.8 solo publica sdist.
El lock incluye el SHA-256 del sdist oficial contrastado en PyPI; las ruedas
locales no se confunden con ruedas publicadas. `requirements-manga-build.lock`
fija setuptools/packaging/wheel antes de la construcción. Los 43 paquetes de
runtime siguen separados del adicional wheel 0.47.0 usado para construir.
La instalación desde ese sdist y el runtime completo siguen siendo gates pendientes.

## Continuación después de 586a7fb

La validación sin cachés del desarrollador ya tiene un único comando ejecutable:
`tools/validate-public-install.sh`. Se ejecutó aquí y quedó BLOCKED por DNS al
consultar el primer lock público; perfil normal sin cambios. El nuevo gate no se
confunde con el éxito histórico de instalación desde `.wheelhouse` descrito arriba.
Se eliminó del lock la alternativa de rueda UniDic local. Requisitos corregidos,
investigación de Python 3.12/3.13, 85 pruebas y evidencia actual:
[PUBLIC-INSTALL-VALIDATION.md](PUBLIC-INSTALL-VALIDATION.md).

## Ejecución externa posterior PASS/0

El usuario completó `public-install-U6n9VjIW`. Se registraron los logs sin repetir
ninguna prueba o descarga. Las 11 etapas pasaron, con perfil normal sin cambios;
el cierre público CPU y modelo completo ya están acreditados en ese host.
[Resumen, artefactos, límites y apertura aislada](EXTERNAL-PUBLIC-INSTALL-PASS.md).
