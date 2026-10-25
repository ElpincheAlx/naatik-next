> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Anki en Next: inspección y diseño

Estado histórico de cb5d115: **propuesta documental, sin implementación ni envíos**.
Implementación posterior y límites de validación: [ANKI.md](ANKI.md). Revisión del
2026-10-20 sobre Next `0ce616d`. Todas las pantallas siguientes son propuestas,
no controles ya disponibles. El alcance actual no añade una sección ni botones
operativos a la aplicación.

Se inspeccionaron como texto `${REFERENCE_ROOT}/` y el paquete
`~/Naatik-validation/japanesemining-workflow-review/`. No se ejecutaron/importaron
sus módulos, lanzadores ni servicios; no hubo peticiones a AnkiConnect local,
consulta/exportación de la colección, instalación ni creación de notas. Los
fuentes relevantes presentes en ambas referencias coinciden byte por byte.
[Manifiesto de archivos, SHA-256 y símbolos](evidence/anki-design/inspection.json).
Las rutas y nombres estáticos antiguos se citan para explicar el código, nunca
como valores predeterminados de Next.

**Pendientes independientes:** el fallo de comandos con Next completamente
cerrado y la configuración de Apariencia siguen abiertos. Este documento no los
resuelve, no cambia bandeja/cierre/arranque, y no amplía el ciclo de vida. Tampoco
introduce publicación, móvil/historial ni envíos automáticos.

## 1. Qué está conectado en JapaneseMining

La cadena del paquete de referencia, contrastada con los archivos actuales, es
`streamdeck_phrase.sh` → analizador HTTP → `ui_service.UiBridge.show_phrase`
(`ui_service.py:80`) → `PhrasePopupQt`. Translator usa `show_translator` (`:149`)
y `TranslatorPopupQt`. Son rutas diferentes, no dos presentaciones del mismo envío.

| Entrada y evidencia estática | Recorrido efectivo | Texto y efecto |
|---|---|---|
| Phrase, pie «Añadir a Anki», `phrase_popup_qt.py:473` | señal `clicked` → `send_full_phrase_to_anki` (`:860`) → `run_phrase_anki` (`:790`) → subproceso `phrase_anki.py` | Envía `self.data`, el análisis recibido; no vuelve a leer el editor de Next ni un OCR original. |
| Phrase, menú «Añadir selección a Anki», `SelectableLabel.open_context_menu` (`:98`) | selección literal del label → `send_selection_to_anki` (`:832`) → `analyze_text` (`:770`) → mismo subproceso | Reanaliza la selección en `/analyze`, fija `selected_text` y `expression`. Puede seleccionarse texto de frase, lectura, traducción o contenido de diccionario; no garantiza que sea una palabra japonesa. |
| Tarjeta de palabra expandida, `phrase_popup_qt.py:198` | label seleccionable enlazado al mismo callback | Es la selección del texto presentado, no una identidad estructurada de la entrada/acepción del diccionario. |
| Translator Qt, `translator_popup_qt.py` | editor → workers de traducción/lecturas y selección → tooltip de diccionario | No se encontró control, callback ni llamada Anki en este archivo. No afirmar que su tooltip envía notas. |
| Servidor móvil, `jp/server/static/app.js:764`, `jp/server/web.py:269` | botón de candidato → POST `/api/anki` → `jp.server.anki.add_note` (`:47`) | Elige candidato del análisis actual; si no coincide `selected_word`, el backend elige el primero. Guarda `add_mined` tras recibir ID. Es otra implementación, fuera del diseño de escritorio de Next. |
| CLI `jp/jp.py:105`, comando `mine` | lookup + `enrich_word`/`get_example` → `jp.modules.anki.add_note` | Palabra de argumento y enriquecimiento local; sin selector gráfico de destino. |
| `anki_phrase.sh:11` y `phrase_streamdeck.sh:30` | JSON de archivo temporal → `phrase_anki.py`; el segundo analiza portapapeles y envía enseguida | Existen recorridos sin previsualización. El paquete muestra que el botón de frase configurado apunta al residente, no demuestra que estos scripts alternativos estén asignados o activos. |
| `yomitan_anki.py` | wrapper de stdin → `jp.modules.anki.add_note` | Adaptador existente. No se encontró un llamador en los fuentes activos inspeccionados; no atribuirle un botón actual. |
| `phrase_popup.py` GTK y variantes de respaldo | existen métodos de envío | No son el popup Qt que construye el `ui_service.py` inspeccionado. Existencia no acredita ejecución. |

Esto acredita cableado por código, **no funcionamiento en una sesión real**. El
paquete refleja configuración histórica de botones; no se volvieron a leer páginas
personales de StreamController ni estado de servicios.

### Construcción real de la nota antigua

`phrase_anki.create_note` (`:249`) importa `jp.modules.anki.add_note`, con esta
transformación:

- `get_lookup_term` (`:52`) prioriza `expression`, `word`, `selected_text`, `surface`,
  `phrase`, `sentence`. La selección explícita gana por `expression`; para la
  frase completa suele acabar usando `sentence`.
- `parse_term` y `format_dictionary` vuelven a consultar los diccionarios locales
  fijados en `jp/modules/dictionary_formatter.py:46`. No consumen necesariamente
  las acepciones que el usuario acaba de desplegar en la tarjeta.
- `Lectura` prefiere `furigana_text`; si falta, se rellena antes con la frase o
  término. Por ello `WordReading` puede recibir frase anotada o texto sin lectura,
  incluso si existe otra lectura de diccionario. No equivale a lectura acreditada.
- `build_meaning_field` (`phrase_anki.py:214`) combina HTML de diccionario y
  traducción automática en `Significado` → `PrimaryDefinition`. El formateador
  incorpora secciones y ejemplos de diccionario; `_pair_examples` (`:886`) intenta
  emparejar textos por heurísticas. `Ejemplo` se rellena con **gramática del
  análisis**, no con la frase original, y acaba en `Sentence`.
- `Pitch` viene del parser del diccionario de acento. `parse_pitch` (`:1038`)
  acumula posiciones y conserva la primera lectura encontrada; no trasladar esa
  agregación como asociación exacta entre expresión y lectura. JLPT procede de
  atributos de kanji; `KanjiNotes` serializa datos parciales de tokens. No es una
  acreditación general de nivel o gramática.
- Los nombres `WordAudio`, `Sentenceaudio` y `Picture` existen en `build_fields`,
  pero el recorrido Phrase no les aporta datos ni llama a APIs de medios.
  Son campos vacíos, no una integración de audio/imagen. El CLI deja `Audio` vacío
  y obtiene ejemplos de una tabla local (`jp/modules/enrich.py:190`); no se leyó
  esa base de datos. El backend móvil tampoco transporta medios.

`jp/modules/anki.py:10` usa `requests.post` a un endpoint fijo, API v6 y JSON,
sin timeout propio. `add_note` (`:153`) fija mazo, tipo y nombres de campos
(`Default` y `JP Mining Note` son **literales antiguos**, no decisiones para Next).
No lista destinos/campos. Los opcionales ausentes pasan como cadenas vacías;
no hay validación del primer campo o de plantillas antes de enviar.

El comentario «permite duplicados» no corresponde a un `allowDuplicate: true`:
no manda esa opción. Genera `Key = palabra + tiempo`, que en un tipo cuyo primer
campo sea `Key` evita detectar como repetido el mismo contenido. No hay búsqueda
previa, bloqueo de doble clic ni reconciliación. No consta qué orden de campos
tiene la colección del usuario y no se consultó.

El popup invoca el subproceso sin worker, con límite de 60 s; la selección añade
antes un HTTP de análisis de 30 s. Puede bloquear GUI. Captura errores, JSON
inválido, salida vacía y `error` del conector, pero interpreta como éxito una
respuesta sin `error` aunque falte un ID válido. Anki cerrado falla por conexión;
un timeout no distingue nota no creada de nota creada sin respuesta.
`anki_phrase.sh` incluso notifica éxito sin comprobar el resultado del pipe.
El backend móvil usa timeout de 10 s y `allowDuplicate: false`, pero no comparte
la lógica del escritorio ni resuelve un resultado incierto. Ninguna de estas
rutas antiguas se ejecutó durante la revisión.

## 2. Comportamiento antiguo → propuesta en Next

| Antiguo | Propuesta |
|---|---|
| Enviar directamente desde Phrase | En ambos popups, solo **Agregar a Anki**; abre borrador/previsualización y nunca envía en ese primer clic. |
| Translator sin conexión Anki | Mismo acceso al compositor común, sin duplicar configuración. |
| Destino y campos fijados en código | Una sección **Anki** en configuración principal; listas reales solo tras comprobar conexión y selección explícita. |
| Reanalizar cualquier label seleccionado | Capturar una instantánea del editor/selección/token elegido, con origen y revisión; no usar un label de traducción como palabra por accidente. |
| Frase/lectura/definición mezcladas | Fuentes tipadas y controles independientes de inclusión/edición. |
| Reconsulta todos los diccionarios al enviar | Previsualizar las entradas elegidas, su diccionario y revisión; enviar esa instantánea confirmada. |
| Primer candidato móvil como fallback | Sin elección de palabra, proponer **Frase**; nunca elegir una palabra oculta automáticamente. |
| Clave temporal para cada clic | Un UUID por intento autorizado, bloqueo compartido y duplicados semánticos de Anki respetados. |
| Timeout tratado como error que invita a repetir | Estado **Envío sin confirmar**, consulta por identificador del intento y ningún reenvío automático. |
| Campos audio/imagen/JLPT vacíos que aparentan soporte | No ofrecer datos inexistentes; explicar ausencia cuando un mapeo los requiera. |
| JSON/errores técnicos en el recorrido | Estado comprensible y siguiente paso; parámetros/logs solo en **Opciones avanzadas / Diagnóstico**. |
| Servicios y temporales de otros proyectos | Worker y configuración propios de Next; sin importar módulos ni reutilizar bases/cachés antiguas. |
| Notificación sin verificar resultado | Éxito solo con ID positivo confirmado o reconciliación inequívoca; conservar edición ante error. |

## 3. Una única sección Anki: primer uso progresivo

No se duplica en Preferencias, Integraciones ni popups. Una sección de configuración
principal aloja todos los pasos y vuelve al paso pendiente. Los elementos de pasos
posteriores se ocultan hasta que haya datos, con explicación; no hay listas vacías
ni botones deshabilitados sin motivo.

| Estado visible | Contenido y siguiente paso | Todavía oculto |
|---|---|---|
| **Sin configurar** | «Para agregar tarjetas necesitas Anki para escritorio y el complemento AnkiConnect. No se enviará nada al comprobar». **Comprobar conexión**; enlace **No tengo Anki / Cómo instalarlo**. | Mazo, tipo y mapeo. |
| **Instalar Anki** — elegido por el usuario | Guía enlazada de descarga/instalación oficial según sistema. **Ver instalación oficial** abre una página; no instala. «Instala Anki, ábrelo y vuelve aquí». | Controles de destinos. |
| **Preparar AnkiConnect** — guía | En Anki: Herramientas → Complementos → Obtener complementos; abrir la ficha oficial, copiar su código y confirmar allí. Reiniciar Anki, abrir su perfil y **Comprobar conexión** en Next. | Mapeo, hasta que responda. |
| **Sin conexión** | «No responde Anki. Ábrelo con el perfil que quieres usar y vuelve a comprobar. Si no instalaste el complemento, consulta la guía». **Comprobar conexión**, **Cómo prepararlo**. | Selectores operativos; los valores anteriores se conservan sin presentarlos como verificados. |
| **Acceso pendiente / conexión no válida** | Distinguir permiso denegado, autenticación, respuesta incompatible o servicio equivocado. **Revisar acceso y comprobar**; diagnóstico expandible. | Envío y selección no verificada. |
| **Conectado · elige destino** | Mostrar mazos y tipos obtenidos de Anki, sin seleccionar el primero automáticamente. Si no hay ninguno, explicar cómo crearlo manualmente en Anki y volver a comprobar. | Mapeo hasta elegir tipo. |
| **Mapear campos** | Por cada campo real del tipo: «Qué recibirá», selector de fuente o **No incluir**, ejemplo y explicación. **Guardar configuración** cuando sea válida; **Cancelar** mantiene lo anterior. | No se añaden tarjetas de prueba al guardar. |
| **Configurado** | Resumen de mazo/tipo/mapeo, fecha de última comprobación y **Comprobar conexión**. «Listo para previsualizar tarjetas; Anki debe permanecer abierto». **Cambiar destino/campos** despliega los pasos existentes. | Parámetros técnicos. |

No poder conectar **no demuestra** que Anki esté desinstalado ni que falte el
complemento: también puede estar cerrado, sin colección abierta o bloqueado.
Una búsqueda negativa del ejecutable tampoco basta. Se ofrece la guía sin
presentar una causa no comprobada como hecho. No se solicita cuenta AnkiWeb,
sincronización ni complementos adicionales para el recorrido local.

La ayuda inicial enlaza [Anki oficial](https://apps.ankiweb.net/), su
[instalación Linux](https://docs.ankiweb.net/manual/platform/linux/installing),
[manual de complementos](https://docs.ankiweb.net/manual/addons) y la
[ficha AnkiConnect](https://ankiweb.net/shared/info/2055492159). El código
**2055492159** y el reinicio figuran en la documentación del mantenedor
[conservada en su repositorio oficial](https://raw.githubusercontent.com/FooSoft/anki-connect/1f7fc80/README.md).
La compatibilidad del paquete actual se verificará antes de implementar; no se
instala desde un fork ni se fija una versión antigua por copiar esta referencia.

Si se llega desde un popup sin configurar, primero se captura el borrador en
memoria y después se abre esta sección en el paso pendiente. Un aviso «Tu texto
se conserva» ofrece **Volver a la previsualización**. Guardar la configuración
habilita ese regreso; no envía, no reemplaza el texto de trabajo y no requiere
pegarlo de nuevo. Cancelar permite volver al popup o al borrador. El compositor
posee su instantánea aunque el popup original se oculte; no necesita prolongar
la vida de la aplicación al salir completamente.

### Bocetos de pantalla — texto de diseño, no interfaz implementada

```text
Anki                                      Sin configurar
Para empezar, abre Anki y prepara AnkiConnect.
[Comprobar conexión]     Cómo instalar Anki y AnkiConnect
▸ Opciones avanzadas / Diagnóstico
```

```text
Anki                                      Conectado
1. Destino   Mazo [elige uno de Anki ▾]  Tipo [elige uno ▾]
2. Campos    (aparece al elegir tipo)
   Campo devuelto por Anki | Qué recibirá [fuente ▾] | Ejemplo
   ...
[Guardar configuración] [Cancelar]
▸ Opciones avanzadas / Diagnóstico
```

**Opciones avanzadas / Diagnóstico** agrupa dirección local, puerto, API,
autenticación si hace falta, límites de espera, estado técnico y mensajes
redactados. Valores habituales no aparecen en el primer uso. No se escriben
claves ni texto de tarjetas en logs. Si se necesita clave, se solicita en un
campo oculto por sesión; persistir secretos requeriría un diseño adicional,
no texto plano en `settings.json`. No cambiar CORS, permisos, perfiles de Anki,
configuración del complemento ni servicios automáticamente.

## 4. Mapeo y previsualización editable

El mapeo se guarda para el destino elegido y la firma de campos del tipo; nombres
literales se reciben de Anki. No se presupone `Front`, `Back`, `Key` ni otro campo.
Cambiar tipo invalida el mapeo incompatible sin borrar el borrador. Actualizar las
listas no cambia silenciosamente mazo/tipo. Si desaparece el destino, conducir a
su selección y conservar el texto.

Las opciones de fuente son **Palabra**, **Lectura**, **Frase**, **Traducción
automática**, **Definiciones con origen**, **OCR original**, **Texto corregido**,
**Texto manual** y, cuando exista evidencia exacta, **Acento** / **Ejemplos de
diccionario**. Nunca presentar recursos ausentes como datos disponibles.
Para un tipo con pocos campos se permite composición explícita por bloques,
por ejemplo lectura + traducción + definiciones, con rótulos separados y ejemplo;
no hay fusión semántica implícita. No ofrecer crear mazos o tipos desde Next en
la primera entrega; la guía lleva a hacerlo deliberadamente en Anki. Cualquier
futura creación desde Next requerirá confirmación específica.

La previsualización muestra:

```text
Previsualizar tarjeta         Destino: [mazo real] · [tipo real]
Modo: Palabra / Frase          Ejemplo de ayuda: datos sintéticos
[✓] Palabra         日本          [editar]
[✓] Lectura         にほん        origen: recurso / edición del usuario
[✓] Frase           日本を読む。   [editar]
[ ] Traducción      ...          automática · ruta usada
[ ] Definiciones    ...          diccionario · revisión · acepción elegida
▸ OCR original / corrección / acento / ejemplos (si existen)
Campos finales de la nota: [revisión editable por campo]
[Volver] [Agregar a Anki]
```

El ejemplo japonés es ilustrativo y no acredita una lectura contextual ni una
definición de un recurso instalado. En uso real se sustituye por datos del
borrador; **las muestras de configuración nunca se envían como contenido real**.
Sin modelos/diccionarios puede escribirse texto manual; las ayudas sintéticas
siguen funcionando y explican por qué falta una fuente, sin fingir un resultado.

Cada bloque tiene inclusión explícita y conserva su procedencia. Editar una
lectura/definición la marca **editada por el usuario**, sin atribuirla íntegramente
al recurso. Campos finales editados a mano no se regeneran ni sobrescriben en
segundo plano. Se elige volver al mapeo o adoptar de nuevo una fuente de forma
explícita. Por defecto se incluye el texto elegido; traducción y acepciones se
revisan antes de incluir. Cancelar no cambia el popup ni la configuración guardada.

El **Agregar a Anki** del popup solo abre esta ventana. El **Agregar a Anki** de la
previsualización, con destino y contenido final visibles, es la confirmación
explícita del envío. No hay atajo de teclado implícito para enviar, envío al
consultar diccionario, al traducir, al cerrar ni al comprobar conexión.
La respuesta confirmada muestra «Nota agregada» e ID; se aclara que un tipo de
nota puede producir varias tarjetas. No se atribuye a Next el render exacto de
las plantillas/CSS de Anki: esta es una vista previa del **contenido de campos**.

Validación local: primer campo no vacío tras tratar HTML/espacios; campos del
modelo exactos, texto con límites, selección coherente. Los demás campos pueden
ser vacíos si las plantillas lo permiten. Un preflight compatible puede ayudar,
pero no prueba que una plantilla genere tarjetas válidas. Una plantilla cloze o
condicional exige revisión y una prueba del tipo; si no se acredita, explicar
la limitación y no prometer soporte. No rellenar huecos con datos inventados.

## 5. Puntos concretos en Next y datos reales

Todos son puntos de **implementación futura**; no se importará código antiguo.

| Punto actual | Adaptación prevista |
|---|---|
| `popup_presentation.build`, pie común (`:202`) | Un solo botón **Agregar a Anki** en Translator y OCR Phrase, junto a Copiar; sin ajustes de conexión/destino dentro del popup ni botones de envío en cada tarjeta. |
| `TextPopup.editor`, `revision`, `session`, `lookup_revision`; `open_text` (`popups.py:83`) | Capturar instantánea inmutable en el clic: editor actual, selección exacta y token elegido. Sin selección, modo Frase. Revisiones posteriores del popup no sobrescriben el borrador. |
| `lookup_token`, `lookup_selection`, `completed` (`popups.py`) | Conservar selección/entrada estructurada y sus resultados vigentes; actualmente el callback renderiza y no mantiene un contrato exportable completo. No extraer datos del HTML de un tooltip. |
| `token_data` y `phrase_worker.Analyzer.analyze` | Usar superficie/lema, offsets y lectura asociados a la revisión vigente y al recurso Fugashi/UniDic. Requiere adaptador de procedencia; no confundir furigana anotada con lectura limpia. |
| `Store.lookup` (`storage.py:127`) | Datos de diccionario con título, revisión, prioridad e identificador; elegir acepción. Acentos solo por expresión **y** lectura. Obtener digest del inventario cuando proceda; no asumir que el resultado ya lo incluye. |
| `dictionary_content` | Reutilizar renderizado seguro/estructura admitida; texto o HTML saneado por bloque, sin scripts, URLs remotas activas ni medios automáticos. |
| `Window.recognized`, `raw_text`, `text_changed`, `translated_source` (`app.py`) | El OCR original existe para la captura principal. Habría que pasar contexto explícito al compositor cuando proceda; no asociarlo a un popup por igualdad de textos. |
| `Window` y configuración principal | Un único controlador/sección Anki; red en worker supervisado. Navegar al paso pendiente conservando borrador y referencia al popup de origen. No tocar el propietario de instancia/cierre. |

| Dato | Disponible hoy / límite |
|---|---|
| Editor, selección, frase | Sí, en ambos popups. Texto de portapapeles/manual; el nombre «OCR Phrase» no prueba procedencia OCR. |
| OCR original y corrección | En la ventana principal, separados. Los popups actuales no reciben ese origen; allí `OCR original = no disponible` salvo un futuro contexto explícito. |
| Traducción automática | Solo resultado vigente para texto/ruta/revisión. Falta un adaptador que conserve esa asociación para exportación; nunca rellenar definiciones con ella. |
| Lecturas | Si el runtime y el léxico propios están instalados o una entrada de diccionario las acredita. Desconocidos permanecen sin lectura; se permite edición manual identificada. La procedencia léxica no garantiza corrección contextual. |
| Definiciones y origen | Recursos activos importados en Next; conservar título/revisión y selección. No copia automática de los ZIP/DB antiguos. La licencia de cada diccionario puede limitar su reutilización; no heredar la del motor. |
| Ejemplos | Algunos contenidos estructurados de diccionario los contienen. Falta extracción tipada con origen y emparejamiento acreditado; no convertir traducción automática en ejemplo de diccionario. |
| Acento | Datos importados por pareja expresión/lectura; hay renderer, falta serializador para nota. Sin recurso/coincidencia exacta, no disponible. |
| Imagen / audio | No hay flujo de adjuntos Anki ni audio producido aquí. La imagen de captura principal no se adjunta automáticamente. No ofrecerlos como campos resueltos; requieren trabajo/confirmación/licencia adicionales. |
| JLPT y gramática | Sin clasificador acreditado. Puede haber entradas/atributos de un diccionario identificadas como tales, no niveles o análisis inventados. No se ofrecen como capacidades generales. |

## 6. Conexión, errores y envío único

Diseño del cliente propio: biblioteca estándar HTTP/JSON en worker supervisado,
endpoint de loopback, sin proxy ambiental ni redirecciones a otros hosts. Límite
de respuesta y tiempos explícitos; cancelar lecturas no altera el borrador.
No importar `requests` o módulos de JapaneseMining. Endpoint/diagnóstico ocultos
en avanzadas; configurar otro equipo o acceso remoto no entra en esta entrega.

Al pulsar Comprobar: negociación documentada de permiso/versionado y consulta de
metadatos, no nota de prueba. Para el contrato inicial se evaluarán
`requestPermission`, `version`, `deckNames`, `modelNames`, `modelFieldNames`;
se verificarán forma/tipos de `result` y `error`, permisos y capacidades reales.
`requestPermission` usa la petición pública documentada, sin parámetros internos
que simulen autorización. Si Anki pide permiso, el usuario decide allí. No repetir
peticiones de permiso denegadas automáticamente. Autenticación requerida guía al
paso de acceso y no se confunde con Anki cerrado.

No se llama `getProfiles`, `loadProfile`, exportación, historial o enumeración de
notas para configurar. La sección opera sobre el perfil **ya abierto por el
usuario en Anki** y lo explica. No se puede identificar una colección únicamente
por URL o por nombres de mazos iguales. Tras reconexión se revalidan destino y
firma del tipo, y se pide comprobar el perfil antes de enviar. Un nombre de
perfil introducido como etiqueta no es evidencia de identidad.

Política inicial: sin duplicados deliberados ni actualizaciones silenciosas.
`allowDuplicate: false`, sin inventar una clave temporal en el primer campo.
La regla nativa de duplicados depende del tipo/primer campo; no garantiza detectar
sinónimos, distintas frases o el mismo concepto en otro tipo. Se explica esa
limitación. Preflight, si está acreditado para la versión, recibe **solo texto**
y no medios: el código antiguo del conector puede procesar medios al construir
una nota incluso para validarla. Un rechazo conserva el borrador para editar;
no se añade por fuerza.

### Doble clic, dos popups y resultado incierto

1. Antes de la única llamada mutante `addNote`, fijar contenido/destino revisados,
   UUID aleatorio del intento y digest canónico del contenido/destino, excluyendo
   UUID y etiqueta técnica de la comparación entre borradores. Un coordinador común bloquea
   clics simultáneos de ese borrador desde ambos popups. Mismo contenido/destino
   en dos borradores activos se detecta y se presenta como envío ya en curso.
2. Escribir **antes de enviar** un registro mínimo de recuperación en estado XDG
   propio (UUID, digest, destino, estado y posible ID; sin texto de tarjeta ni
   secretos). Incluir una etiqueta técnica única `naatik_tx_<uuid>` en la nota,
   explicada en el resumen de envío; no requiere crear campos/tipos. Si no puede
   registrarse el intento, no enviar. No es historial móvil ni publicación.
3. Solo un `addNote`, sin reintento automático de la capa HTTP. Éxito exige
   `error: null` e ID entero positivo; se marca confirmado en el registro. Una
   respuesta rota, cierre del worker, timeout tras despacho o error que pudo
   ocurrir después de crear la nota pasa a **Envío sin confirmar**. Un error solo
   se trata como rechazo definitivo cuando se sabe que no hubo mutación; no
   equiparar todo HTTP 500/JSON `error` a «no se creó».
4. Mostrar «No sabemos si Anki recibió la nota. No la enviaremos otra vez» y
   **Comprobar resultado**. Mantener la edición y bloquear otro envío de esa
   operación. Cancelar la espera no revierte una nota; cerrar ventana no autoriza
   reenviarla. Al reabrir Next se muestra que existe un intento pendiente, sin
   publicar ni reconstruir automáticamente el texto privado.
5. Comprobar resultado hace una búsqueda **acotada a esa etiqueta** (`findNotes`)
   en el destino de conexión confirmado, y `notesInfo` solo para esos IDs. Un
   resultado coherente con el tipo/digest devuelve confirmado. Varios resultados
   o contenido cambiado requieren revisión manual, sin borrar/editar notas.
6. Cero resultados **no demuestra** ausencia: el servidor podría terminar tarde,
   el usuario podría haber cambiado de perfil o quitado la etiqueta. Mantener
   incierto, permitir volver a comprobar y explicar cómo revisar en Anki. No
   reintentar `addNote` por ese cero. Si se abandona la recuperación, no borrar la
   nota ni liberar silenciosamente la protección; cualquier nueva creación con
   posible duplicado necesitaría una decisión explícita adicional, fuera del
   botón normal de reintento. En la primera entrega se prioriza revisión manual.

AnkiConnect no aporta aquí una clave de idempotencia transaccional del cliente.
El UUID facilita reconciliar; **no garantiza exactamente una creación** ante
cambios de perfil, modificaciones externas o respuestas tardías. Esta limitación
forma parte de la aceptación. Para errores de conexión comprobados antes del
envío, volver a comprobar y confirmar es seguro; para los inciertos, no.
El borrador se mantiene en memoria mientras esté abierto; guardarlo en disco
como texto requeriría una opción explícita adicional. El registro mínimo sí
permite detectar operaciones pendientes tras un cierre inesperado.

## 7. Dependencias y fuentes oficiales

No se añadió ni instaló ninguna dependencia en esta etapa. Anki de escritorio y
AnkiConnect son **requisitos externos futuros**, distintos de los recursos
lingüísticos de Next. La comunicación por HTTP no copia su código a Next.

| Elemento | Procedencia/licencia comprobada y límite |
|---|---|
| Anki | [Sitio de descarga oficial](https://apps.ankiweb.net/) y [LICENSE del proyecto](https://raw.githubusercontent.com/ankitects/anki/main/LICENSE): AGPL-3.0-or-later para el proyecto, con componentes/contribuciones bajo otras licencias. No atribuir una sola licencia a todos los binarios. No se instala ni redistribuye aquí. |
| AnkiConnect | La [licencia del repositorio oficial archivado](https://raw.githubusercontent.com/FooSoft/anki-connect/master/LICENSE) declara GPL-3.0-or-later. Su [README actual](https://raw.githubusercontent.com/FooSoft/anki-connect/master/README.md) remite al [repositorio del mantenedor en SourceHut](https://git.sr.ht/~foosoft/anki-connect). La consulta de SourceHut quedó bloqueada; licencia/versión exactas del paquete actual se deberán verificar antes de implementarlo o instalarlo. No presentar el archivo histórico como validación del paquete actual. |
| Protocolo | [README oficial histórico, revisión `1f7fc80`](https://raw.githubusercontent.com/FooSoft/anki-connect/1f7fc80/README.md) y [implementación oficial archivada](https://raw.githubusercontent.com/FooSoft/anki-connect/master/plugin/__init__.py). Se contrastaron puntos de API; las capacidades del paquete futuro deben probarse, no inferirse de una API v6 genérica. |
| Cliente Next | Previsto: biblioteca estándar de Python y PySide6/Task ya existentes. No se añade SDK, servidor Anki dentro de Next ni dependencia del entorno antiguo. |
| Lecturas, diccionarios, modelos y ejemplos | Inventario actual de Next. Licencias independientes; disponibilidad/origen no autorizan redistribuir corpus o adjuntos. No hay descarga/importación automática en esta revisión. |

La ficha AnkiWeb requiere JavaScript y no permitió inspeccionar su descripción en
esta herramienta. Se verificó el código de complemento en la documentación
histórica del mantenedor, sin tomar un fork como autoridad actual. El manual
oficial advierte que actualizaciones de Anki pueden afectar complementos.
Esa combinación exacta deberá quedar registrada con versión/procedencia/hash
cuando se prepare el perfil de prueba. [Inventario de dependencias](THIRD_PARTY_DEPENDENCIES.md).

## 8. Plan de pruebas — todo pendiente de implementación

No se ejecutó un servidor simulado ni un perfil real de Anki en esta revisión.
La siguiente matriz es el contrato de pruebas futuro, no resultados PASS.

| Prueba | Resultado exigido |
|---|---|
| Next con HOME/XDG nuevos, sin Anki ni recursos lingüísticos | Primer uso con guía y Comprobar conexión; sin listas vacías aparentando configuración. Ningún acceso a datos personales ni descargas. |
| Anki no instalado / instalado pero cerrado / sin complemento | Mensaje prudente de no conexión y pasos diferenciados por la guía/respuesta disponible; conservar borrador y no inventar la causa. |
| Servidor simulado en loopback y puerto efímero | Acciones permitidas registradas; ningún `addNote` al conectar, listar, mapear, previsualizar, cancelar, cerrar o traducir. No usar 8765 de la máquina del usuario. |
| Permiso denegado, clave requerida/incorrecta, API incompatible, JSON roto, límites y timeout | Estado recuperable, diagnóstico apartado, sin secretos ni contenido en logs; sin reintentos de escritura. |
| Mazos/tipos/campos con nombres arbitrarios y Unicode | Ningún nombre personal/fijo; sin selección del primero ni creación de elementos. Desaparición/cambio de tipo invalida solo el mapeo pertinente. |
| Recursos ausentes o respuestas lingüísticas antiguas | Palabra/frase manual posible, lectura/acento ausentes identificados, sin fuentes fingidas. Descarta resultados de otra revisión. |
| Original OCR, corrección, traducción y definiciones distintas | Cada bloque y procedencia llegan solo al campo elegido. Selección no sustituye frase; HTML se sanea; ningún adjunto remoto. |
| Configuración sin instalar Anki | Guía desde cero y muestra sintética claramente marcada; nunca enviar la muestra por confirmar configuración. |
| Cancelar configuración y borrador; volver desde configuración pendiente | Persistencia solo al guardar configuración, texto de trabajo intacto y edición recuperable; ningún envío automático al regresar. |
| Doble clic / dos popups / dos borradores equivalentes | Una llamada mutante por intento coordinado; rechazar repetición de operación confirmada. |
| Simulador guarda y después corta la respuesta / guarda tarde | Estado incierto y búsqueda acotada; no reenvío, incluso si la primera búsqueda devuelve cero. |
| Reiniciar cliente tras perder respuesta / cambiar perfil de Anki | Registro mínimo pendiente; sin escanear colección ni asumir que igual URL identifica el mismo perfil. Exigir revisión antes de resolver. |
| Duplicado nativo, primer campo vacío, campos opcionales, plantilla condicional/cloze | Rechazo claro sin perder edición; ningún relleno inventado o `allowDuplicate` silencioso. |
| ID inválido, varios IDs de reconciliación, nota modificada | No mostrar confirmación falsa ni borrar datos; revisión manual. |
| Fallo de escritura del registro antes de enviar | Cero escrituras en Anki; error recuperable local. |

### Prueba manual futura desde instalación limpia

1. Preparar una VM/cuenta de sistema de prueba o base de datos Anki totalmente
   separada, además de HOME/XDG de Next aislados. Anki permite una base alternativa
   con `anki -b /ruta/aislada`; verificarla en la
   [guía oficial de archivos](https://docs.ankiweb.net/manual/files). Un perfil
   nuevo en la misma base no aísla complementos: se comparten, según el
   [manual de perfiles](https://docs.ankiweb.net/manual/profiles). No copiar,
   enumerar, exportar ni abrir la colección personal. No iniciar sesión/sincronizar.
2. Antes de instalar nada, comprobar el primer uso sin Anki: seguir la ayuda
   oficial, instalarlo deliberadamente en esa máquina/base de prueba, abrir un
   perfil vacío, preparar AnkiConnect y reiniciar. Registrar versiones/orígenes y
   configurar manualmente un puerto local de prueba distinto del habitual en el
   complemento de esa base aislada y en las opciones avanzadas de Next. No hacer
   peticiones al puerto habitual de la colección personal. Comprobar que solo el
   perfil de prueba atiende ese endpoint. Si hay una instancia personal o destino ambiguo, detener la prueba real.
3. Crear manualmente un mazo y tipo de nota de prueba con nombres nuevos elegidos
   para la prueba, con consentimiento; comprobar conexión desde la sección Anki,
   elegirlos y mapear campos. No usar nombres o campos de una colección existente.
4. En Translator y OCR Phrase, con y sin recursos, abrir Agregar a Anki. Cancelar,
   cambiar de configuración y volver: preservar texto. Revisar las inclusiones,
   editar, confirmar una nota sintética y comprobar su ID en Anki de prueba.
5. Detener Anki, volver a comprobar, reabrirlo y recuperar la edición. Probar el
   resto de fallos/timeout incierto con el servidor simulado, nunca provocando
   cortes contra una colección personal. Revisar duplicado explícito y doble clic.
6. Separar informes: pruebas unitarias/offscreen, HTTP con simulador y escritorio
   real con Anki de prueba. No acreditar instalación desde cero o envío real por
   pasar pruebas simuladas. Arranque cerrado de Next sigue siendo un gate externo
   pendiente: esta revisión no modifica ni presupone resuelto ese comportamiento.

Antes de implementar envío: cerrar revisión de procedencia/capacidades del
paquete actual, concretar el contrato de datos y cubrir la matriz de simulación.
La apariencia de Next puede evolucionar por su tarea propia; este diseño no
introduce su implementación ni acopla el envío a un tema visual específico.
