#!/usr/bin/env bash
# Install the base, or the optional Next-owned CPU OCR runtime. No legacy fallback.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$project_dir"
unset PYTHONPATH PYTHONHOME
export PYTHONNOUSERSITE=1
python_cmd="${NAATIK_NEXT_PYTHON:-python3.14}"
mode=base
language_args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --language) [[ $# -ge 2 ]] || exit 2; language_args=(--language "$2"); shift 2;;
    base|--manga-cpu|--phrase) mode="$1"; shift;;
    *) echo 'Uso / Usage: tools/install.sh [--manga-cpu|--phrase] [--language es|en]' >&2; exit 2;;
  esac
done
# This gate precedes environment creation, pip, downloads and desktop registration.
export NAATIK_NEXT_UI_LANGUAGE
NAATIK_NEXT_UI_LANGUAGE="$(cd -- "$project_dir" && "$python_cmd" -m naatik_next.install_language "${language_args[@]}")" || exit $?
msg() {
  "$python_cmd" -m naatik_next.install_language --language "$NAATIK_NEXT_UI_LANGUAGE" --message "$1" --suffix "${2:-}"
}
case "$mode" in base|--manga-cpu|--phrase) ;; *) echo 'Uso: tools/install.sh [--manga-cpu|--phrase]' >&2; exit 2;; esac
if ! command -v "$python_cmd" >/dev/null 2>&1; then msg "Falta Python 3.14. En Fedora 44: sudo dnf install python3 python3-pip" >&2; exit 2; fi
"$python_cmd" -c 'from naatik_next.i18n import t; import sys,platform; assert sys.version_info[:2] == (3,14) and sys.platform == "linux" and platform.machine() == "x86_64", t("Locks disponibles: CPython 3.14 Linux x86_64 (no free-threaded)"); import sysconfig; assert not sysconfig.get_config_var("Py_GIL_DISABLED"), t("No se admite Python free-threaded")'
if [[ "$mode" == base ]]; then
  env_dir="$project_dir/.venv"; lock="$project_dir/requirements.lock"
  wheel_dir="${NAATIK_NEXT_WHEELHOUSE:-$project_dir/.wheelhouse}"
elif [[ "$mode" == --phrase ]]; then
  env_dir="$project_dir/.venv-phrase"; lock="$project_dir/requirements-phrase.lock"
  wheel_dir="${NAATIK_NEXT_WHEELHOUSE:-$project_dir/.wheelhouse-phrase}"
else
  env_dir="$project_dir/.venv-mangaocr"; lock="$project_dir/requirements-manga-cpu.lock"
  wheel_dir="${NAATIK_NEXT_WHEELHOUSE:-$project_dir/.wheelhouse-manga}"
fi
if [[ -L "$env_dir" ]]; then msg "Se rechaza un entorno enlazado fuera de la instalación: " "$env_dir" >&2; exit 1; fi
if [[ ! -x "$env_dir/bin/python" ]]; then "$python_cmd" -m venv "$env_dir"; fi
"$env_dir/bin/python" -c 'from naatik_next.i18n import t; import sys,pathlib; assert sys.version_info[:2] == (3,14) and sys.prefix != sys.base_prefix; assert "include-system-site-packages = false" in (pathlib.Path(sys.prefix)/"pyvenv.cfg").read_text().lower(), t("El entorno contiene paquetes del sistema; usa una venv aislada")'
install_lock() {
  local selected_lock="$1"
  if [[ "${NAATIK_NEXT_ONLINE:-0}" != 1 && ( "${NAATIK_NEXT_OFFLINE:-0}" == 1 || -d "$wheel_dir" ) ]]; then
    "$env_dir/bin/python" "$project_dir/tools/offline_install.py" "$selected_lock" "$wheel_dir"
  else
    "$env_dir/bin/python" -m pip --isolated install --index-url https://pypi.org/simple --no-cache-dir --only-binary=:all: --no-binary=unidic-lite --no-build-isolation --no-deps --require-hashes --timeout 20 --retries 1 -r "$selected_lock"
  fi
}
# UniDic Lite is published as sdist. Its builder must exist before pip's build stage.
if [[ "$mode" != base ]]; then install_lock "$project_dir/requirements-manga-build.lock"; fi
install_lock "$lock"
if [[ "$mode" == base ]]; then
  NAATIK_NEXT_PROJECT="$project_dir" "$env_dir/bin/python" -c 'import sys,os; sys.path.insert(0,os.environ["NAATIK_NEXT_PROJECT"]); from PySide6.QtWidgets import QApplication; from naatik_next.translation import package_api; package_api(); import ctranslate2; import sentencepiece; from PIL import Image; from naatik_next.i18n import t; print(t("Base importada; OCR/modelos se prueban desde la aplicación"))'
  if [[ "${NAATIK_NEXT_SKIP_DESKTOP:-0}" != 1 ]]; then "$env_dir/bin/python" "$project_dir/tools/install_desktop.py"; fi
elif [[ "$mode" == --phrase ]]; then
  "$env_dir/bin/python" -m pip --isolated check
  "$env_dir/bin/python" -c 'from fugashi import Tagger; import unidic_lite; from naatik_next.i18n import t; print(t("Recursos de frase importados; prueba el análisis desde OCR Phrase"))'
else
  "$env_dir/bin/python" -m pip --isolated check
  "$env_dir/bin/python" -c 'import torch; from manga_ocr import MangaOcr; assert torch.version.cuda is None; from naatik_next.i18n import t; print(t("Runtime CPU importado; falta probar modelo e inferencia desde la aplicación"))'
fi
(cd -- "$project_dir" && "$env_dir/bin/python" -m naatik_next.install_language --language "$NAATIK_NEXT_UI_LANGUAGE" --save)
msg "Abre: " "$project_dir/launch"
