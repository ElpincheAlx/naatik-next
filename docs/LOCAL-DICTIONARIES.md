> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Diccionarios locales: importación múltiple y consulta

Comprobación de los cinco ZIP reales de `${REFERENCE_ROOT}/dictionaries`, identificados
por **index.json y sus bancos**, sin inferir títulos de nombres truncados. Las pruebas
usaron SQLite/XDG aislados. No se importó ningún ZIP en el perfil normal.

## Archivos probados

| ZIP real | Título / revisión de index.json | Bancos | Soporte implementado | Entradas importadas | Consulta comprobada | Resultado |
| --- | --- | --- | --- | ---: | --- | --- |
| `[Bilingual] JMdict (Recommended).zip` | JMdict [2025-11-01] / `JMdict.2025-11-01` | term_bank × 52, tag_bank × 1 | términos/bilingüe | 513,033 | 日本 (4 filas de este diccionario) | Importación, consulta y comparación íntegra correctas |
| `[Bilingual] 新和英.zip` | 新和英 / `Shinwaei1` | term_bank × 25 | términos/bilingüe | 152,202 | 日本 (2 filas de este diccionario) | Importación, consulta y comparación íntegra correctas |
| `[Grammar] Dictionary of Japanese Grammar 日本語文法辞典 (Recommended).zip` | 日本語文法辞典(全集) / `DOJG_v1.01;2022-04-30;better formatting` | term_bank × 1 | gramática (términos) | 535 | くらい (2 filas de este diccionario) | Importación, consulta y comparación íntegra correctas |
| `[Kanji] KANJIDIC (English) (Recommended).zip` | KANJIDIC [2025-345] / `kanjidic2.2025-345` | kanji_bank × 2, tag_bank × 1 | kanji | 10,383 | 亜 (1 fila de este diccionario) | Importación, consulta y comparación íntegra correctas |
| `[Pitch] アクセント辞典v2.zip` | アクセント辞典 / `pitch1` | tag_bank × 1, term_meta_bank × 33 | acento tonal | 327,037 | 日本 (2 filas de este diccionario) | Importación, consulta y comparación íntegra correctas |

Las cantidades son filas de datos, excluyendo tags; se conservan también index y
tags. JMdict incluye filas de formas y lecturas: no se colapsan como supuestos duplicados.
Gramática contiene 535 filas de términos normales con tags DOJG y texto que empieza
por 文法項目; se reconoce esa estructura y se conserva completa. No existe un banco
Yomitan separado de gramática ni se detectan automáticamente patrones en frases.

## Usar desde la GUI

1. Cierra y vuelve a abrir Next con `${PROJECT_ROOT}/launch` para cargar la actualización.
2. En **Diccionarios → Agregar diccionarios**, selecciona varios ZIP con Ctrl/Shift.
   La inspección se ejecuta en un worker y no importa nada. Puedes cancelar.
3. Revisa **archivo, título, tipo, revisión, entradas y estado/avisos**. Marca los
   que quieras y pulsa **Importar seleccionados**. Duplicados y errores no son
   seleccionables. Los ZIP con omisiones declaradas empiezan desmarcados y requieren
   selección explícita; los detalles figuran en la columna y su tooltip.
4. Se procesa un ZIP cada vez, con progreso y resultado individual. Un fallo no
   revierte archivos anteriores ni impide continuar con los siguientes. **Cancelar
   operaciones** revierte solo el ZIP activo y descarta los pendientes. Los que ya
   terminaron permanecen importados. Si el commit terminó justo antes de la cancelación,
   se informa que ese ZIP ya está completo y se refresca la tabla. No se descarga
   ni se extrae sobre el original.
5. Activa/desactiva o ajusta la prioridad de cada diccionario en la tabla. Se guardan
   en SQLite entre sesiones. Quitar elimina únicamente sus registros administrados.
6. En Captura y resultado, selecciona **日本 → Consultar selección**: aparecen
   significados de JMdict/新和英 y acento separado para **にほん [2]** y **にっぽん [3]**.
   El acento adjunto a cada definición exige coincidencia de **expresión y lectura**;
   una lectura vacía no recibe una variante arbitraria. El apartado de acento muestra
   además cada registro con lectura y origen explícitos.
7. Selecciona **日** para KANJIDIC (significados, on/kun y atributos como strokes,
   grade, códigos y etiquetas presentes). Selecciona **くらい** para DOJG: explicación
   y ejemplos íntegros. La consulta sigue siendo exacta, sin tokenización automática
   ni descomposición de 日本 en kanji. La pestaña Diccionarios permite estas mismas
   consultas para comprobar recursos. Nada se envía a Argos como consecuencia de consultar.

## Alcance y protección de datos

- Se mantienen términos v3 y árboles enriquecidos admitidos (JMdict). Se añaden
  kanji_bank v3 de seis campos, term_meta/pitch con reading y pitches, posiciones
  enteras no negativas o patrones H/L, etiquetas y marcas nasal/devoice. Se conservan
  filas originales JSON y todos sus campos admitidos, no solo texto aplanado.
- El visor genera HTML desde elementos permitidos y escapa texto; no incorpora CSS
  crudo, código ejecutable, enlaces navegables ni recursos externos/locales. El acento
  se representa como posición de caída por mora ([0] sin caída) o patrón H/L explícito;
  no sintetiza pronunciación, audio ni una predicción nueva de acento.
- **Ninguno de los cinco ZIP contiene imágenes/audio locales**: solo índices y bancos
  JSON. No hay medios necesarios omitidos en estas pruebas. Medios no se renderizan.
  Si otro ZIP contiene archivos de imagen/audio accesorios, se enumeran como recursos
  no importados; si una definición exige un elemento no admitido, como img, se rechaza
  el ZIP completo con error, evitando presentar una definición recortada como completa.
- Un ZIP mixto puede importar a la vez términos, gramática, kanji y pitch. Los bancos
  de frecuencia/IPA no están integrados: se cuenta y declara su omisión, tanto en la
  revisión como en el resultado y metadata persistente. Un ZIP sin datos compatibles
  se rechaza. Un modo desconocido o una fila admitida inválida también se rechazan.
- Se conservan límites de 512 MiB de archivo/expansión, 32 MiB por miembro, 10.000
  miembros, relación máxima 300:1 y 2 millones de filas, más límites de árboles/filas.
  Se rechazan rutas peligrosas, enlaces simbólicos, miembros duplicados y cifrado.
  Se trabaja con snapshot privado único, sin extracción. El SHA-256 se vuelve a
  comprobar antes de importar: si cambió desde la revisión se pide revisar de nuevo.
- La migración es aditiva y transaccional a **user_version=2**: agrega kanji/pitches
  e índices sin reconstruir términos ni borrar metadata, activación o prioridad.
  Una versión de esquema futura se rechaza. Las consultas con esquema 2 no ejecutan
  DDL en cada worker. Se conservan claves foráneas/cascada por diccionario.

## Esquemas oficiales consultados

Los validadores son código local para el subconjunto documentado, sin añadir
Yomitan ni un validador JSON Schema como dependencias de ejecución. No se afirma
compatibilidad con todo ZIP o con todas las variantes presentes/futuras del formato.

- [dictionary-index-schema.json](https://github.com/yomidevs/yomitan/blob/master/ext/data/schemas/dictionary-index-schema.json)
- [dictionary-term-bank-v3-schema.json](https://github.com/yomidevs/yomitan/blob/master/ext/data/schemas/dictionary-term-bank-v3-schema.json)
- [dictionary-tag-bank-v3-schema.json](https://github.com/yomidevs/yomitan/blob/master/ext/data/schemas/dictionary-tag-bank-v3-schema.json)
- [dictionary-kanji-bank-v3-schema.json](https://github.com/yomidevs/yomitan/blob/master/ext/data/schemas/dictionary-kanji-bank-v3-schema.json)
- [dictionary-term-meta-bank-v3-schema.json](https://github.com/yomidevs/yomitan/blob/master/ext/data/schemas/dictionary-term-meta-bank-v3-schema.json)
- [dictionary-kanji-meta-bank-v3-schema.json](https://github.com/yomidevs/yomitan/blob/master/ext/data/schemas/dictionary-kanji-meta-bank-v3-schema.json)

Consulta de esquemas: 2026-10-19, rama oficial master. No se copian sus fuentes
en el runtime. Su licencia no se atribuye a los diccionarios ni a sus conversiones.

## Evidencia y límites de validación

`.venv/bin/python -m tools.multidictionary_smoke` ejecutó
los cinco ZIP reales: inspección, importación, comparación JSON de cada una de las
1.003.190 filas, consulta de entradas reales, duplicado por SHA, activación y
prioridad persistidas, cancelación/rollback de cada ZIP y eliminación sin perder
los otros diccionarios. Los originales conservaron sus hashes. Se verificó también
una migración sobre backup de la base normal: 513.033 términos y la fila de
configuración de diccionario conservaron sus huellas lógicas; la base y settings
normales conservaron sus SHA-256 antes/después. No hubo importación normal.
Los campos de procedencia/licencia del JSON se anotaron después por revisión manual.

La GUI utilizó el **worker real de consulta**, renderer Qt **offscreen** y las
entradas 日本, 日 y くらい; el bucle Qt siguió operativo. Se inspeccionó el panel en
`/tmp/HISTORICAL-REVIEW`. Original OCR y Argos fueron centinelas de
prueba, conservados: esto no valida OCR/traducción ni captura interactiva nuevos.
La selección múltiple y confirmación se ejercitaron con workers reales y diálogo
aceptado de forma inyectada; falta revisar el selector/diálogo de manera interactiva
en el escritorio. No se declara esa interacción a partir de pruebas offscreen.

Además hay regresiones sintéticas de ZIP mixtos, omisiones explícitas, asociación
de variantes, prioridad, borrado aislado, migración idempotente, contenido malicioso,
cambio después de preflight y cancelación del lote durante un worker de kanji.
Ver [VALIDATION.md](VALIDATION.md). No se repitieron inferencias OCR/Argos ajenas al cambio.

Versiones, hashes, procedencia y licencias verificadas/pendientes:
[inventario de terceros](THIRD_PARTY_DEPENDENCIES.md#8-diccionarios) y
[evidencia completa](local-dictionaries-evidence.json). Se reconocen los datos de
James William Breen/EDRDG utilizados en JMdict y KANJIDIC, sujetos a su
[documentación y licencia](https://www.edrdg.org/edrdg/licence.html); los permisos
de las conversiones y demás diccionarios no se deducen de esta licencia.

Para repetir solo esta comprobación real (no vuelve a ejecutar OCR ni Argos):

```bash
cd ${PROJECT_ROOT}
.venv/bin/python -m tools.multidictionary_smoke --output /tmp/HISTORICAL-REVIEW
```

La suite completa final aprobó **68 pruebas** (`unittest discover`), además del
ensayo real de los cinco ZIP descrito arriba.
