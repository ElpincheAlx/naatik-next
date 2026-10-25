#!/usr/bin/env bash
# Public-source validation, never a repair/install of the normal user profile.
set -euo pipefail
umask 077
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
review_parent="${HOME:?}/Naatik-validation"
mkdir -p -- "$review_parent"
review_dir="$(mktemp -d "$review_parent/public-install-XXXXXXXX")"
printf 'Resultados y logs: %s\n' "$review_dir"
normal_config="${XDG_CONFIG_HOME:-$HOME/.config}"
normal_data="${XDG_DATA_HOME:-$HOME/.local/share}"
[[ "$normal_config" = /* ]] || normal_config="$HOME/.config"
[[ "$normal_data" = /* ]] || normal_data="$HOME/.local/share"
python_cmd="${NAATIK_NEXT_PYTHON:-python3.14}"
if ! command -v "$python_cmd" >/dev/null 2>&1; then
  printf '%s\n' 'BLOCKED: falta CPython 3.14. En Fedora 44: sudo dnf install python3 python3-pip' | tee "$review_dir/summary.txt"
  printf '%s\n' '{"status":"BLOCKED","reason":"Missing CPython 3.14; see summary.txt","normal_profile_accessed":false}' >"$review_dir/result.json"
  exit 2
fi
python_cmd="$(command -v "$python_cmd")"
if [[ "$python_cmd" == *JapaneseMining* ]] || ! "$python_cmd" -I -c 'import sys,platform,sysconfig; assert sys.version_info[:2] == (3,14) and sys.prefix == sys.base_prefix and sys.platform == "linux" and platform.machine() == "x86_64" and not sysconfig.get_config_var("Py_GIL_DISABLED")' >"$review_dir/python-preflight.log" 2>&1; then
  printf '%s\n' 'BLOCKED: se necesita CPython 3.14 estándar Linux x86_64, fuera de cualquier venv. Consulta python-preflight.log.' | tee "$review_dir/summary.txt"
  printf '%s\n' '{"status":"BLOCKED","reason":"Interpreter/platform preflight failed; see python-preflight.log","normal_profile_accessed":false}' >"$review_dir/result.json"
  exit 2
fi
mkdir -p "$review_dir/home" "$review_dir/xdg/config" "$review_dir/xdg/data" "$review_dir/xdg/state" "$review_dir/xdg/cache" "$review_dir/tmp"
# Preserve only explicit network proxy/CA settings, never Python, pip or HF tokens/config.
network_env=()
for key in HTTPS_PROXY HTTP_PROXY ALL_PROXY NO_PROXY https_proxy http_proxy all_proxy no_proxy SSL_CERT_FILE SSL_CERT_DIR; do
  if [[ -v "$key" ]]; then network_env+=("$key=${!key}"); fi
done
set +e
env -i PATH=/usr/bin:/bin HOME="$review_dir/home" \
  XDG_CONFIG_HOME="$review_dir/xdg/config" XDG_DATA_HOME="$review_dir/xdg/data" \
  XDG_STATE_HOME="$review_dir/xdg/state" XDG_CACHE_HOME="$review_dir/xdg/cache" \
  TMPDIR="$review_dir/tmp" LC_ALL=C.UTF-8 QT_QPA_PLATFORM=offscreen \
  PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
  "${network_env[@]}" "$python_cmd" -I "$source_dir/tools/public_install_validation.py" \
  --source "$source_dir" --output "$review_dir" --normal-config "$normal_config" --normal-data "$normal_data" \
  >"$review_dir/console.log" 2>&1
status=$?
set -e
if [[ -f "$review_dir/summary.txt" ]]; then cat "$review_dir/summary.txt"; else
  printf 'FAIL: validación interrumpida (código %s); consulta console.log\n' "$status" | tee "$review_dir/summary.txt"
fi
printf 'Logs conservados en: %s\n' "$review_dir"
exit "$status"
