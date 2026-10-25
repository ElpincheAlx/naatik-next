# Apariencia — evidencia del 2026-10-21

Implementación sobre el árbol que ya contenía el trabajo de Anki sin commit.
Se conservan esos cambios y el script previo `naatik-next-capturar.sh`.

Validación ejecutada con perfiles HOME/XDG temporales:

- `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest tests.test_appearance -q`
  → **5 pruebas, OK**, 0.455 s. Incluye cancelar/restablecer sin escritura,
  guardar/reabrir, ambos popups existentes/nuevos, fuentes ausentes, entrada
  inválida, contraste, color cancelado y fallo al guardar. Verifica que texto y
  revisión del popup no cambian y que el tamaño de interfaz llega a los controles.
- `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -q`
  → **221 pruebas, OK, 2 omitidas**, 36.133 s. Las omisiones corresponden al
  listener HTTP Anki y gate IPC real restringidos por el sandbox.
- `QT_QPA_PLATFORM=offscreen .venv/bin/python -m tools.appearance_review`
  → PASS; capturas sintéticas de Claro/Oscuro y ambos popups, sin workers.
- `git diff --check` → PASS.

Capturas revisadas offscreen:

| Tema | Configuración | Translator | OCR Phrase |
|---|---|---|---|
| Claro | Ver (referencia histórica no distribuida) | Ver (referencia histórica no distribuida) | Ver (referencia histórica no distribuida) |
| Oscuro | Ver (referencia histórica no distribuida) | Ver (referencia histórica no distribuida) | Ver (referencia histórica no distribuida) |

La revisión visual permitió corregir fondos claros residuales en controles del
modo oscuro. No se instalaron ni descargaron fuentes, temas, paquetes o modelos.
Se usan la biblioteca estándar y PySide6 existentes. No se cambiaron la apariencia
ni las preferencias del perfil personal durante las pruebas. No hay envíos a Anki.

Pendiente: interacción en KDE real, selector de fuente/color nativo, cambio de
paleta comunicado por el escritorio, escalado y varios monitores. Las capturas
no acreditan esas comprobaciones. [Guía de uso](../../APPEARANCE.md).
