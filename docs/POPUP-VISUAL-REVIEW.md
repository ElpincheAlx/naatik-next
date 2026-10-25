> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Recreación visual de Translator y OCR Phrase

Revisión 2026-10-20. Referencia de solo lectura: el paquete
`~/Naatik-validation/japanesemining-workflow-review/fuentes/JapaneseMining/`.
Se revisaron `build_interface`, `apply_qss`, las clases de cabecera, texto,
tooltip y tarjeta, y las acciones de `translator_popup_qt.py` y
`phrase_popup_qt.py`. Los hashes están en
[evidencia visual](evidence/popup-visual/visual-review.json).
No se iniciaron servicios, lanzadores, motores, consultas HTTP ni entornos antiguos.

## Distribución observada por código y reproducida

| Elemento | Referencia | Next |
|---|---|---|
| Ventana | 720 × 840, mínimo 520 × 560, sin marco, encima | Mismas dimensiones lógicas y flags; cabecera arrastrable y cierre ×; Esc cancela y oculta |
| Cabecera | Título 16 px/700, badge cian 11 px, cierre 34 × 34; márgenes 18/10/10/10 | Misma jerarquía; marca Na’atik Next |
| Contenido | Scroll vertical; márgenes 18/16/18/20, separación 14 | Mismos márgenes y separación; pie independiente del scroll |
| Colores | Fondo #f7f8fa, tarjetas blancas, bordes #e0e5eb, selección #b9d7ff | Mismos valores, radios de 14/12/10 px para frase/sección/palabra |
| Tipografía | Noto Sans/Noto Sans JP; frase Noto Serif CJK JP; fallbacks del sistema | Mismas familias solicitadas, sin instalar ni distribuir fuentes |
| Translator | OCR editable 29 px; pista de selección; Furigana 16 px; Translation 17 px; Copiar texto al pie | Mismo orden y tamaños; edición de texto plano, deshacer, selección; ruta Argos visible dentro de Translation |
| Diccionario Translator | Tooltip con título, texto seleccionable, cerca de la selección | Tooltip con selección como título y renderizador seguro de Next; limitado al área del monitor |
| Phrase | Frase 31 px, lectura/furigana 16 px, badge «frase»; Traducción; Palabras y diccionarios | Misma organización; editor de frase y ruta visibles; sin niveles inventados |
| Palabras Phrase | Tarjetas cerradas; flecha, palabra 22 px, lectura 13 px, categoría; consulta al expandir | Tarjetas plegables, lema cuando difiere, consulta exacta al abrir; varios cuerpos pueden quedar abiertos |
| Detalles | Diccionarios específicos, ejemplos/acento/kanji si existen en su respuesta | Diccionarios activos del usuario, por prioridad, con el renderizador seguro existente; no se fabrican campos ausentes |
| Pie | Copiar texto/frase; Phrase añade Anki | Copiar texto/frase; Opciones para las funciones implementadas; Anki omitido |

## Comparación visual y límites

Las imágenes muestran **izquierda: referencia UI; derecha: Next**, 720 × 840
cada una, Qt 6.11.1 offscreen a 96 DPI. Se inspeccionaron ambas comparaciones:

- Translator (referencia histórica no distribuida).
- OCR Phrase, primera tarjeta expandida (referencia histórica no distribuida).

El diagnóstico extrae mediante AST únicamente métodos de presentación permitidos
de los archivos indicados. Omite imports/top-level, constructores de ventanas,
workers, consultas y servicios; sustituye callbacks externos por funciones
inertes y usa texto/traducción/diccionario **sintéticos**. No se ejecuta el programa
antiguo. Esta extracción existe solo en la herramienta de revisión, nunca en la
aplicación, instalador o tests normales. La referencia es un argumento explícito;
Next funciona y se prueba sin ella.

En este renderizado los `QToolButton` originales de las tarjetas no reservan
altura para su layout interno: se ve la flecha pero no palabra/lectura/categoría.
Los fuentes sí especifican esos controles. Next les asigna altura explícita para
que sean visibles. **No se supone que el escritorio antiguo tuviera ese fallo.**
Para contrastar ese detalle hace falta una captura del OCR Phrase original a
720 × 840, con una tarjeta cerrada y otra abierta, mostrando palabra, lectura,
categoría y diccionario, junto con el porcentaje de escalado de KDE. No hace
falta arrancar sus servicios para validar Next y no se ha inventado ese estado
del escritorio original. Fuentes disponibles determinan los demás tamaños y
controles; el renderizado no acredita composición, movimiento, foco ni pegado real.

Diferencias deliberadas:

- Marca propia, no JapaneseMining. Las familias tipográficas son solicitudes al
  sistema; el fallback y el escalado pueden cambiar su apariencia en otra máquina.
- Ruta Argos elegible y estados de error/preparación visibles: ocupan espacio que
  el original de ruta fija no tenía. Phrase mantiene su editor visible, por lo
  que su tarjeta principal es más alta que la etiqueta original no editable.
- Las lecturas proceden de los recursos propios de Next; el recurso y su posible
  ambigüedad se indican. No se reproduce una lectura distinta solo por imitar una imagen.
- Opciones despliega Traducir/Analizar, Cancelar, Consultar selección,
  Configuración y Preparar lecturas. La gestión de modelos se trasladó a Traducción.
  No se mezclan estos controles de preparación con el área de lectura inicial.
- Las consultas usan un worker supervisado: una consulta en curso puede completar
  su propia tarjeta; las peticiones aún en cola se agrupan en la más reciente.
  Una petición desplazada se indica como sustituida y se puede reintentar abriendo
  la tarjeta. Editar/cancelar invalida todos los destinos previos.
- La selección manual en Phrase usa una sección aparte; las palabras usan su
  propio cuerpo desplegable. Translator recupera el tooltip de selección.
- No se muestran Anki, gramática, JLPT, historial ni móvil como funciones operativas.
  No se sustituye una traducción fallida por definiciones. No se fijan nombres de
  diccionarios ni se exige contenido de la instalación de referencia.
- Cabecera Qt con fondo blanco explícito y altura reservada para palabras;
  no se reproducen artefactos de tamaño/pintado de widgets del render de referencia.

La preparación vigente abre la sección **Traducción** de la ventana principal.
El popup muestra **Preparar traducción** cuando faltan recursos; las rutas se
actualizan automáticamente. [Recorrido vigente](TRANSLATION-SETUP.md).
Las comparaciones anteriores conservan el alcance histórico de la recreación.

## Reproducir y probar

Solo para comparar con una copia de revisión disponible (no requisito de instalación):

```bash
cd ${PROJECT_ROOT}
.venv/bin/python tools/popup_visual_review.py \
  --reference ~/Naatik-validation/japanesemining-workflow-review/fuentes/JapaneseMining \
  --output /tmp/HISTORICAL-REVIEW
```

La herramienta establece HOME/XDG temporales **antes de importar Qt o Next**;
no escribe preferencias reales ni ejecuta inferencia. Genera seis PNG y sus hashes.
La suite cubre además tarjetas/consulta diferida, respuestas cruzadas obsoletas,
reemplazo de tarjetas, cancelación de listas por tandas, tooltip, editor, rutas,
recursos ausentes, arranque aislado, IPC inyectado, independencia de acciones,
SIGINT/SIGTERM y workers. El análisis Fugashi/UniDic y diccionario sintético usan
procesamiento real propio. La traducción neural sigue **pendiente**, según indicó
el usuario: no se descargaron modelos. Ver resultados en la evidencia JSON.

Para ejecutar toda la suite con aislamiento desde antes de importar módulos:

```bash
cd ${PROJECT_ROOT}
profile=$(mktemp -d /tmp/HISTORICAL-REVIEW)
mkdir -m 700 "$profile/runtime"
env HOME="$profile" XDG_CONFIG_HOME="$profile/config" \
  XDG_DATA_HOME="$profile/data" XDG_CACHE_HOME="$profile/cache" \
  XDG_STATE_HOME="$profile/state" XDG_RUNTIME_DIR="$profile/runtime" \
  QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m unittest discover -v
```

Prueba breve en escritorio, pendiente en este entorno sin acceso a la sesión:

1. Copia una frase japonesa y ejecuta `${PROJECT_ROOT}/launch --translator`.
   Comprueba que solo abre Translator: edita, selecciona una palabra para su
   tooltip y revisa la ruta visible. Sin modelo debe explicar cómo importarlo
   en Opciones; con modelo debe traducir sin definiciones de sustitución.
2. Desde otra terminal, ejecuta `${PROJECT_ROOT}/launch --phrase`. Comprueba frase,
   lecturas y palabras; abre/cierra dos tarjetas. Sin diccionarios o sin
   coincidencias debe decirlo en esa tarjeta. Edita rápidamente y confirma
   que ninguna respuesta anterior reemplaza la nueva frase.
3. Repite los comandos: una ventana por acción; Esc cierra/cancela ese popup.
   Copiar texto/frase copia el editor. Prueba el script/atajo propio de cada
   acción. `${PROJECT_ROOT}/launch --capture-copy` debe seguir capturando y copiando
   sin abrir popups; `${PROJECT_ROOT}/launch` abre Configuración en la ventana principal.

La primera instancia queda residente: no la mates entre acciones; usa otra
terminal, KDE o StreamController. No se regeneró el script externo existente ni
se cambiaron atajos, botones o accesos del usuario. Su configuración independiente
continúa descrita en [POPUPS.md](POPUPS.md) y [STREAM-DECK.md](STREAM-DECK.md).
