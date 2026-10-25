> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Diagnóstico de 日本 → Japanese — 2026-10-19

## Conclusión

El resultado se reproduce sin captura ni OCR. El adaptador de Next y la API
oficial de Argos 1.11.0 devuelven **Japanese** con los mismos archivos locales
ja→en (paquete 1.1). La selección incorrecta de palabra ya está en los tokens
producidos por la inferencia, antes de decodificar. No se encontró un defecto de
tokenización, inferencia o decodificación del adaptador que explique este caso.
Se trata de una limitación de estos modelos locales, no de una traducción fiable
de 日本 aislado. No se introdujeron sustituciones ni consultas de diccionario en
el traductor. No se cambiaron automáticamente motor, idioma o dirección.

## Qué se sabe de la captura y qué no

- La captura del usuario muestra `日本` en el editor, ruta directa `ja → en`, salida
  `Japanese` y la etiqueta «Texto corregido por el usuario».
- Las preferencias actuales, leídas sin escribirlas, indican Tesseract / `jpn` y
  ruta `ja → en`. Eso no permite reconstruir las preferencias de cada acción pasada.
- El OCR original está en `Window.raw_text`, separado del editor. No se persiste
  en SQLite, preferencias ni log. La captura no muestra el diálogo «Ver original
  OCR». Por tanto **no se pudo recuperar ni validar el OCR original histórico**.
- El editor visible contiene 日本; no se dispone de un registro histórico del
  payload enviado. El código toma `editor.toPlainText()` en `translation_input`,
  lo envía por JSON al worker sin sustituirlo y conserva esa instantánea como
  `translated_source` al recibir el resultado. Esto es consistente con la imagen,
  pero no prueba retrospectivamente los bytes de aquella petición.
- El log contiene errores de OCR vacío y cancelación de captura, sin texto ni un
  identificador que permita asignarlos a la imagen. No se atribuyen a este ejemplo.
- No se inspeccionó memoria de otro proceso ni se alteró la ventana en ejecución.

Una regresión de UI con **OCR simulado y explícitamente distinto** comprueba que
traducir 日本 envía exactamente ese texto editado y ja→en, conserva el original,
no cambia motor/idioma/ruta y no llama a consulta de diccionarios. Si el editor
cambia mientras llega la respuesta, esta sigue asociada a la instantánea enviada.
Esto comprueba el contrato del código, no la exactitud del OCR real del usuario.

## Reproducción y etapas reales

Entorno aislado de Next: Argos 1.11.0, CTranslate2 4.8.1 y SentencePiece 0.2.2.
Modelos locales, sin instalar ni descargar otros:

- `~/.local/share/argos-translate/packages/ja_en`, versión 1.1.
- `~/.local/share/argos-translate/packages/en_es`, versión 1.0.

El informe JSON adjunto registra ruta, entrada y salida de cada etapa, tokens
reales, parámetros y SHA-256 de metadata, tokenizador y todos los archivos del
modelo. La observación del adaptador delega al método real sin cambiar sus opciones.

| Paso | Entrada | Tokens de entrada | Hipótesis del modelo | Decodificación |
| --- | --- | --- | --- | --- |
| ja→en | 日本 | `['▁日本']` | `['▁Japanese']` | Japanese |
| en→es, solo al pedir esa ruta explícitamente | Japanese | `['▁Japanese']` | `['▁japonés']` | japonés |

Los prefijos de destino de ambos paquetes son vacíos. Se utiliza el tokenizador
que proporciona cada paquete Argos, sin transliteración, traducción por
vocabulario ni concatenación manual de símbolos. El token ▁ es la marca de
espacio de SentencePiece, no una alteración de 日本.

Parámetros de Next: CPU, dos hilos intra/inter=1, beam=4, replace_unknowns=True,
length_penalty=0.2, máximo de decodificación 1024. Para estos textos cortos no se
alcanza el límite. No hay segmentación que cambie 日本: constituye una sola línea.

## Contraste oficial con dependencias locales

Se pudo importar la implementación oficial completa usando `/usr/bin/python3`
y las dependencias **ya instaladas** en el entorno del usuario. Ese entorno se
usó solo como referencia; no se incorporó al entorno de ejecución de Next.

La API oficial usa Stanza para estos paquetes. Por defecto intenta actualizar
`resources.json`; ese intento no pudo acceder a la red. Para la comparación se
estableció explícitamente `stanza.Pipeline(download_method=None)` y se bloquearon
DNS/conexiones en el proceso de diagnóstico. Se usaron el segmentador y los
modelos Stanza ya presentes, sin sustituir su algoritmo ni falsear módulos.

Se ejecutaron dos comparaciones:

1. API pública real `argostranslate.translate.translate`, con segmentación Stanza
   local y rutas directas/compuestas.
2. Función oficial real `apply_packaged_translation` para ja→en, pasando un
   segmentador de una sola línea explícito para igualar la unidad del adaptador.
   Esta segunda comparación no equivale a probar segmentación lingüística.

Ambas devuelven Japanese para 日本. La segunda devuelve score
`-3.8894195556640625`; es una puntuación de la hipótesis, no una confianza semántica.

| Entrada explícita, sin OCR | Next ja→en | API oficial ja→en | Next y oficial ja→en→es |
| --- | --- | --- | --- |
| 日本 | Japanese | Japanese | japonés |
| 日本語 | English | English | Inglés |
| 日本に行きます。 | Go to Japan | Go to Japan | Ir a Japón |

El informe confirma `same_package_files: true` y `same_outputs: true`. Las seis
salidas coinciden; las versiones de las tres bibliotecas también. La frase con
contexto demuestra que el resultado no es una sustitución fija de 日本 en Next.
Esta conclusión está limitada a estos archivos de modelos y parámetros.

La implementación oficial usa las mismas operaciones encode/translate_batch/
decode, beam mínimo 4, replace_unknowns y length_penalty=0.2. Difiere en
segmentación por frases, batching, número de hipótesis cuando se solicita más de
una y límite de decodificación por defecto. Ninguna diferencia explica este
caso: coinciden tanto la API completa como la unidad de una línea.

## Diccionario, separado de traducción

La base administrada del usuario se abrió en modo SQLite **solo lectura**. No
había diccionarios activos ni coincidencias disponibles para 日本. No se activó,
importó ni modificó ninguno. La prueba anterior de 新和英 en una base temporal
había encontrado 日本 / にほん / Japan; eso es una **definición de diccionario**,
no la traducción de la frase ni evidencia del OCR.

La regresión de UI comprueba además que un resultado identificado como
«Diccionario de prueba» se muestra en la consulta sin reemplazar `Japanese` en
el panel de traducción. El dato de esa prueba es simulado y está etiquetado.

## Repetir las pruebas

```bash
cd ${PROJECT_ROOT}
.venv/bin/python -m tools.diagnose_translation --official-python /usr/bin/python3
.venv/bin/python -m unittest discover -v
```

Se puede usar `--text 'otro texto'` repetidamente. Sin `--official-python`, solo se
prueba el adaptador de Next. El informe se imprime por petición explícita; no se
agrega registro automático de textos privados en el funcionamiento normal.

Evidencia de esta ejecución: [translation-日本-evidence.json](translation-日本-evidence.json).
**19 pruebas correctas**; no hay sustitución que fuerce 日本→Japan ni un test que
exija perpetuar la traducción errónea del modelo. Los archivos de producción
permanecen sin cambios. La captura interactiva y el OCR original histórico
siguen sin estar validados por esta investigación.
