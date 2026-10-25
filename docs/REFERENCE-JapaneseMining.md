> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# JapaneseMining — Arquitectura del sistema

Este documento describe la arquitectura general de JapaneseMining, sus componentes principales, la comunicación entre procesos y el flujo de datos desde una captura OCR hasta el popup final o el envío a Anki.

---

## 1. Objetivo del sistema

JapaneseMining es una herramienta local para estudiar japonés desde cualquier parte del escritorio.

Sus funciones principales son:

- Capturar texto japonés mediante OCR.
- Analizar palabras y frases.
- Consultar diccionarios locales.
- Generar lecturas y furigana.
- Detectar gramática.
- Traducir texto.
- Mostrar resultados en ventanas flotantes.
- Enviar vocabulario y frases a Anki.
- Integrarse con Stream Deck.

El sistema está diseñado para funcionar localmente, sin depender de servicios externos para las consultas de diccionario.

---

## 2. Vista general

```text
┌─────────────────────┐
│     Stream Deck     │
│ Atajos / botones    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Scripts de captura  │
│ Bash + Spectacle    │
└──────────┬──────────┘
           │
           ▼
┌────────────────────────────┐
│ Procesamiento OCR          │
│ PaddleOCR / MangaOCR       │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ JapaneseMining Server      │
│ server/server.py           │
│ Puerto 9876                │
└──────────┬─────────────────┘
           │
           ├── Diccionarios locales
           ├── Tokenización
           ├── Furigana
           ├── Gramática
           ├── Traducción
           └── Lookup
           │
           ▼
┌────────────────────────────┐
│ UI Service                 │
│ ui_service.py              │
│ Puerto 9877                │
└──────────┬─────────────────┘
           │
           ├── Phrase Analyzer
           └── Translator Popup
           │
           ▼
┌────────────────────────────┐
│ Usuario                    │
│ Consulta / Minado / Anki   │
└────────────────────────────┘
```

---

## 3. Componentes principales

## 3.1 Stream Deck

El Stream Deck sirve como punto de entrada rápido para ejecutar acciones.

Funciones habituales:

- Capturar una región de pantalla.
- Ejecutar OCR.
- Analizar una frase.
- Traducir texto.
- Consultar una palabra.
- Enviar datos a Anki.

Los botones ejecutan scripts ubicados principalmente en:

```text
scripts/streamdeck/
```

Ejemplo:

```text
scripts/streamdeck/ocr_capture_streamdeck.sh
```

Los scripts del Stream Deck deben ser pequeños lanzadores y no deben contener bucles infinitos ni relanzarse a sí mismos.

---

## 3.2 Captura de pantalla

La captura de región se realiza con Spectacle.

Flujo básico:

```text
Usuario selecciona región
        │
        ▼
Spectacle genera imagen PNG
        │
        ▼
La imagen se guarda temporalmente en /tmp
```

Ejemplo de archivo temporal:

```text
/tmp/ocr_clipboard.png
```

El script debe:

1. Borrar capturas anteriores.
2. Abrir Spectacle.
3. Esperar la creación de la imagen.
4. Cancelar la espera después de un tiempo límite.
5. Limpiar los archivos temporales al finalizar.

---

## 3.3 OCR

JapaneseMining dispone de varios motores OCR.

### MangaOCR

Servicio:

```text
japanese-mining-mangaocr.service
```

Responsabilidad:

- Reconocer texto japonés, especialmente manga y texto estilizado.
- Mantener el modelo cargado en memoria.
- Evitar recargar el modelo en cada captura.

### PaddleOCR

Servicio:

```text
japanese-mining-paddleocr.service
```

Responsabilidad:

- Detectar regiones de texto.
- Procesar imágenes.
- Complementar el reconocimiento OCR.

Archivo principal:

```text
scripts/paddleocr_server.py
```

### Tesseract

También puede utilizarse en scripts simples.

Ejemplo:

```bash
tesseract imagen.png stdout -l jpn --psm 6
```

Tesseract resulta útil para capturas rápidas o como alternativa cuando no se necesita el servidor residente.

---

## 3.4 Servidor principal

Servicio:

```text
japanesemining.service
```

Archivo:

```text
server/server.py
```

Puerto:

```text
9876
```

El servidor principal mantiene recursos pesados cargados en memoria para evitar reinicializarlos en cada consulta.

Responsabilidades:

- Consultar diccionarios.
- Analizar frases.
- Generar lecturas.
- Añadir furigana.
- Detectar gramática.
- Traducir con Argos.
- Devolver resultados en formato JSON.

Endpoints principales:

```text
GET  /health
POST /lookup
POST /analyze
```

### `/health`

Comprueba que el servidor está activo.

Ejemplo:

```bash
curl http://127.0.0.1:9876/health
```

### `/lookup`

Consulta una palabra o expresión.

Entrada aproximada:

```json
{
  "term": "日本"
}
```

### `/analyze`

Analiza una frase completa.

Entrada aproximada:

```json
{
  "text": "発売開始しました"
}
```

Salida aproximada:

```json
{
  "sentence": "発売開始しました",
  "reading": "はつばいかいししました",
  "furigana_text": "発売開始(はつばいかいし)しました",
  "translation": "Sales have started.",
  "grammar": [],
  "tokens": []
}
```

---

## 3.5 Motores de análisis

El servidor utiliza módulos internos del proyecto.

### Tokenización

Responsabilidad:

- Separar la frase en palabras y morfemas.
- Identificar forma base.
- Detectar conjugaciones.
- Obtener parte de la oración.

Tecnología principal:

```text
SudachiPy
```

Ejemplo:

```text
発売開始しました
```

Puede separarse como:

```text
発売
開始
し
まし
た
```

### Diccionarios

Los diccionarios locales incluyen información como:

- Expresión.
- Lectura.
- Significado.
- Parte de la oración.
- Kanji.
- Acento tonal.
- Ejemplos.
- Gramática.

La base principal se encuentra en:

```text
db/japanese.db
```

También existen índices y archivos importados en:

```text
data/
dictionaries/
temp/
```

### Furigana

Responsabilidad:

- Generar lecturas para palabras con kanji.
- Integrar lectura y superficie de cada token.
- Construir la frase con furigana.

Archivo relacionado:

```text
furigana_engine.py
```

### Gramática

Responsabilidad:

- Detectar patrones gramaticales.
- Mostrar su significado.
- Añadir nivel JLPT aproximado.
- Generar información para el popup.

### Traducción

El servidor principal utiliza Argos Translate.

Flujo actual:

```text
Japonés
   │
   ▼
Argos ja → en
```

El traductor se carga durante el warmup del servidor.

---

## 3.6 Interfaz gráfica residente

Servicio:

```text
japanese-mining-ui.service
```

Archivo:

```text
ui_service.py
```

Puerto:

```text
9877
```

Tecnología:

```text
PySide6 / Qt
```

El servicio UI no realiza directamente el análisis lingüístico pesado.

Responsabilidades:

- Recibir datos ya procesados.
- Crear ventanas Qt.
- Mostrar el Phrase Analyzer.
- Mostrar el popup de traducción.
- Mantener la aplicación Qt residente.
- Crear las ventanas desde el hilo principal de Qt.

Componentes principales:

```text
phrase_popup_qt.py
translator_popup_qt.py
```

La comunicación entre el servidor HTTP interno y Qt se realiza mediante señales.

Ejemplo conceptual:

```text
Petición HTTP
     │
     ▼
Hilo del servidor
     │
     ▼
Signal de Qt
     │
     ▼
Hilo principal
     │
     ▼
Ventana
```

Esto evita crear widgets desde un hilo secundario.

---

## 3.7 Phrase Analyzer

Archivo principal:

```text
phrase_popup_qt.py
```

Responsabilidades:

- Mostrar la frase original.
- Mostrar furigana.
- Mostrar lectura.
- Mostrar traducción.
- Mostrar tokens.
- Mostrar gramática.
- Mostrar kanji.
- Mostrar niveles JLPT.
- Permitir minar palabras o frases.

El popup recibe un diccionario con los datos ya analizados.

Ejemplo:

```json
{
  "sentence": "発売開始しました",
  "reading": "はつばいかいししました",
  "furigana_text": "発売開始(はつばいかいし)しました",
  "translation": "Comenzó la venta.",
  "grammar": [],
  "tokens": []
}
```

---

## 3.8 Traductor

Servicio:

```text
japanese-translate.service
```

Componentes relacionados:

```text
translator_popup_qt.py
JapaneseTranslate/
```

Responsabilidad:

- Mostrar una traducción rápida.
- Dar una idea general del texto.
- Mantener la traducción separada del análisis completo.

El traductor está diseñado para ser rápido y sencillo, no para sustituir el análisis detallado.

---

## 3.9 Anki

JapaneseMining se comunica con Anki mediante AnkiConnect.

Dirección habitual:

```text
http://127.0.0.1:8765
```

Responsabilidades:

- Crear notas.
- Añadir palabras.
- Añadir frases.
- Guardar lecturas.
- Guardar significados.
- Guardar ejemplos.
- Guardar datos JLPT.
- Guardar audio cuando esté disponible.

Modelo utilizado:

```text
JP Mining Note
```

Deck habitual:

```text
Default
```

Flujo:

```text
Phrase Analyzer
      │
      ▼
Datos de palabra o frase
      │
      ▼
Script Anki
      │
      ▼
AnkiConnect
      │
      ▼
Anki
```

---

## 4. Servicios systemd

Servicios principales:

```text
japanesemining.service
japanese-mining-ui.service
japanese-mining-mangaocr.service
japanese-mining-paddleocr.service
japanese-translate.service
```

Todos son servicios de usuario:

```bash
systemctl --user
```

No requieren ejecutarse como root.

Ubicación habitual de las unidades:

```text
~/.config/systemd/user/
```

---

## 5. Orden lógico de funcionamiento

Aunque systemd puede iniciarlos en paralelo, el flujo lógico es:

```text
1. Servidores OCR
2. Servidor principal
3. UI residente
4. Scripts de captura
5. Popups
6. Anki
```

Flujo de una captura:

```text
Stream Deck
    │
    ▼
Script Bash
    │
    ▼
Spectacle
    │
    ▼
Imagen PNG
    │
    ▼
OCR
    │
    ▼
Texto japonés
    │
    ▼
Servidor principal :9876
    │
    ▼
JSON analizado
    │
    ▼
UI Service :9877
    │
    ▼
PhrasePopupQt
```

---

## 6. Puertos

| Puerto | Componente |
|-------:|------------|
| 8765 | AnkiConnect |
| 9876 | JapaneseMining Server |
| 9877 | JapaneseMining UI Service |

Los servidores escuchan únicamente en:

```text
127.0.0.1
```

Esto significa que solo son accesibles desde la propia computadora.

---

## 7. Archivos temporales

Los scripts utilizan archivos en:

```text
/tmp/
```

Ejemplos:

```text
/tmp/ocr_clipboard.png
/tmp/japanese-mining-ui.log
/tmp/japanese-mining-ocr.lock
```

Estos archivos deben limpiarse al finalizar los scripts.

Los scripts Bash deberían usar:

```bash
trap cleanup EXIT INT TERM
```

para eliminar archivos temporales y bloqueos incluso cuando se cancelan.

---

## 8. Control de concurrencia

Los scripts OCR deben impedir que varias capturas se ejecuten simultáneamente.

Ejemplo:

```text
/tmp/japanese-mining-ocr.lock
```

Antes de iniciar una captura:

```bash
mkdir "$LOCK"
```

Si el directorio ya existe, significa que hay otro OCR activo.

Esto evita:

- Varias ventanas de Spectacle.
- Procesos OCR duplicados.
- Conflictos con archivos temporales.
- Consumo excesivo de CPU.

---

## 9. Rendimiento

Comportamiento esperado:

### En reposo

- CPU baja.
- Los servicios permanecen cargados.
- Los modelos y diccionarios permanecen en memoria.
- No deben existir scripts OCR activos.

### Durante OCR

- El uso de CPU puede aumentar temporalmente.
- PaddleOCR, MangaOCR o Tesseract procesan la imagen.
- Al terminar, el consumo debe volver a bajar.

### Durante análisis

- El servidor consulta diccionarios.
- Argos puede utilizar CPU para traducir.
- El popup se crea después de recibir el JSON.

### Procesos que no deben quedar activos

```text
ocr_capture_streamdeck.sh
ocr_to_clipboard.sh
spectacle
tesseract
```

Estos procesos deben terminar después de cada captura.

---

## 10. Riesgos conocidos

### Recursión en scripts

Un script lanzador nunca debe ejecutarse a sí mismo.

Incorrecto:

```bash
exec "$HOME/JapaneseMining/scripts/streamdeck/ocr_capture_streamdeck.sh"
```

dentro del propio archivo `ocr_capture_streamdeck.sh`.

Esto produce una recursión infinita y consume un núcleo completo.

### Esperas infinitas

Incorrecto:

```bash
while [[ ! -s "$IMG" ]]; do
    sleep 0.1
done
```

sin límite de tiempo.

Debe existir un contador o timeout.

### Procesos duplicados

Las pulsaciones repetidas del Stream Deck pueden iniciar varias capturas.

Debe usarse un archivo o directorio de bloqueo.

### Servicios duplicados

No deben existir dos servicios realizando exactamente la misma función.

Antes de crear un servicio nuevo, comprobar:

```bash
systemctl --user list-unit-files | grep japanese
```

---

## 11. Diagnóstico

### Ver servicios activos

```bash
systemctl --user --type=service --state=running |
grep -Ei 'japanese|mining|ocr'
```

### Ver consumo de CPU

```bash
ps -eo pid,pcpu,pmem,comm,args --sort=-pcpu | head -20
```

### Ver procesos del proyecto

```bash
pgrep -af JapaneseMining
```

### Ver puertos

```bash
ss -ltnp |
grep -E '8765|9876|9877'
```

### Ver logs del servidor

```bash
journalctl --user -u japanesemining.service -f
```

### Ver logs de la UI

```bash
journalctl --user -u japanese-mining-ui.service -f
```

### Ver logs de MangaOCR

```bash
journalctl --user -u japanese-mining-mangaocr.service -f
```

### Ver logs de PaddleOCR

```bash
journalctl --user -u japanese-mining-paddleocr.service -f
```

---

## 12. Reinicio de componentes

### Reiniciar servidor principal

```bash
systemctl --user restart japanesemining.service
```

### Reiniciar UI

```bash
systemctl --user restart japanese-mining-ui.service
```

### Reiniciar MangaOCR

```bash
systemctl --user restart japanese-mining-mangaocr.service
```

### Reiniciar PaddleOCR

```bash
systemctl --user restart japanese-mining-paddleocr.service
```

### Reiniciar traductor

```bash
systemctl --user restart japanese-translate.service
```

### Recargar unidades después de modificarlas

```bash
systemctl --user daemon-reload
```

---

## 13. Estructura simplificada del proyecto

```text
JapaneseMining/
├── ARCHITECTURE.md
├── SERVICES.md
├── VERSION
├── CHANGELOG.md
├── db/
│   └── japanese.db
├── data/
├── dictionaries/
├── jp/
├── scripts/
│   ├── paddleocr_server.py
│   └── streamdeck/
├── server/
│   └── server.py
├── phrase_engine.py
├── furigana_engine.py
├── phrase_popup_qt.py
├── translator_popup_qt.py
├── ui_service.py
└── ocr_to_clipboard.sh
```

---

## 14. Principios de diseño

JapaneseMining sigue estos principios:

1. Procesamiento local.
2. Diccionarios residentes para consultas rápidas.
3. Separación entre lógica y UI.
4. Servicios independientes.
5. Comunicación mediante HTTP local y JSON.
6. Scripts de captura pequeños.
7. Limpieza de archivos temporales.
8. Protección frente a procesos duplicados.
9. Integración directa con Anki.
10. Historial de cambios mediante Git local.

---

## 15. Mejoras futuras

Posibles mejoras:

- Reducir el uso de memoria.
- Unificar servicios redundantes.
- Añadir health checks automáticos.
- Añadir timeouts HTTP.
- Añadir métricas de tiempo de OCR.
- Añadir métricas de tiempo de análisis.
- Mejorar la detección de conjugaciones.
- Mejorar el merge de palabras compuestas.
- Añadir JLPT por token y frase.
- Añadir minado completo de frases.
- Añadir audio automático.
- Crear un comando único para administrar todos los servicios.

---

## 16. Resumen

La arquitectura se divide en cuatro capas:

```text
Entrada
  └── Stream Deck y capturas

Procesamiento
  └── OCR, diccionarios, tokenización y traducción

Presentación
  └── UI Service y popups Qt

Persistencia
  └── SQLite, archivos locales y Anki
```

La separación permite actualizar cada componente de forma independiente sin modificar todo el proyecto.
