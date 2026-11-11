"""Проверка примера профиля dsh перед переносом на другую машину.

Запуск (из каталога integrations/dsh):
    python scripts/check_example.py
    python scripts/check_example.py --patch path/to/cordis.patch.yml

Что проверяется:
  1. patch-файл — YAML-массив записей загрузчика; у строк есть id, нет дублей;
  2. провайдеры Qwen Cloud: https baseURL, имя credential-ссылки, модель по
     умолчанию существует в списке моделей своего провайдера;
  3. в шаблоне credentials имя ссылки совпадает с apiKeyEnv;
  4. package.json — валидный JSON с непустым dsh.profile.bundles;
  5. в файлах нет значений, похожих на API-ключ.

Зависимость: PyYAML (есть в dsh-runtime). Скрипт не ходит в сеть и ничего
не изменяет; все найденные ошибки печатаются, код возврата 1 — если они есть.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - зависит от окружения
    sys.stderr.write("нужен PyYAML: python -m pip install pyyaml\n")
    raise SystemExit(2)

ROOT = pathlib.Path(__file__).resolve().parent.parent
SECRET_RE = re.compile(r"sk-[A-Za-z0-9._-]{8,}")
EFFORTS = {"off", "low", "medium", "high", "xhigh", "max"}


def read_text(path: pathlib.Path) -> str:
    """Прочитать файл как UTF-8 и снять BOM, который добавляет PowerShell."""
    return path.read_text(encoding="utf-8-sig")


def check_patch(path: pathlib.Path, failures: list[str]) -> dict:
    """Проверить patch-файл и вернуть разобранный провайдер llm-pi-ai."""
    try:
        entries = yaml.safe_load(read_text(path))
    except yaml.YAMLError as error:
        failures.append(f"{path.name}: YAML не разбирается: {error}")
        return {}

    if not isinstance(entries, list):
        failures.append(f"{path.name}: ожидался массив записей загрузчика")
        return {}

    ids = [entry.get("id") for entry in entries if isinstance(entry, dict) and "insert" not in entry]
    if any(not entry_id for entry_id in ids):
        failures.append(f"{path.name}: у записи нет id")
    duplicates = {entry_id for entry_id in ids if ids.count(entry_id) > 1}
    for entry_id in sorted(duplicates):
        failures.append(f"{path.name}: id '{entry_id}' повторяется")

    config = {}
    for entry in entries:
        if isinstance(entry, dict) and entry.get("id") in {"llm-pi-ai", "agent-default-model"}:
            config[entry["id"]] = entry.get("config") or {}

    routes = (config.get("llm-pi-ai") or {}).get("providers") or {}
    if not routes:
        failures.append(f"{path.name}: нет config.providers у llm-pi-ai")
        return config

    for route_name, route in routes.items():
        if not str(route.get("baseURL", "")).startswith("https://"):
            failures.append(f"{route_name}: baseURL должен начинаться с https://")
        if not route.get("apiKeyEnv"):
            failures.append(f"{route_name}: нет apiKeyEnv — ключ должен жить в credential-ссылке")
        models = route.get("models") or []
        if not models:
            failures.append(f"{route_name}: пустой список models")
        model_ids = [model.get("id") for model in models]
        if len(model_ids) != len(set(model_ids)):
            failures.append(f"{route_name}: id моделей повторяются")
        for model in models:
            for effort in (model.get("reasoningEfforts") or {}):
                if effort not in EFFORTS:
                    failures.append(f"{route_name}/{model.get('id')}: неизвестный уровень reasoning '{effort}'")

    default = config.get("agent-default-model") or {}
    if default:
        route = routes.get(default.get("provider"))
        if route is None:
            failures.append(f"agent-default-model: провайдер '{default.get('provider')}' не объявлен")
        elif default.get("model") not in [model.get("id") for model in route.get("models") or []]:
            failures.append(f"agent-default-model: модели '{default.get('model')}' нет у провайдера")

    return config


def check_credentials(path: pathlib.Path, config: dict, failures: list[str]) -> None:
    if not path.exists():
        return
    try:
        document = yaml.safe_load(read_text(path)) or {}
    except yaml.YAMLError as error:
        failures.append(f"{path.name}: YAML не разбирается: {error}")
        return

    if document.get("version") != 1:
        failures.append(f"{path.name}: ожидался version: 1")
    refs = document.get("refs") or {}
    routes = (config.get("llm-pi-ai") or {}).get("providers") or {}
    for route_name, route in routes.items():
        reference = route.get("apiKeyEnv")
        if reference and reference not in refs:
            failures.append(f"{path.name}: нет ссылки {reference} для провайдера {route_name}")


def check_package(path: pathlib.Path, failures: list[str]) -> None:
    if not path.exists():
        return
    try:
        manifest = json.loads(read_text(path))
    except json.JSONDecodeError as error:
        failures.append(f"{path.name}: JSON не разбирается ({error}); комментарии // и # запрещены")
        return
    bundles = ((manifest.get("dsh") or {}).get("profile") or {}).get("bundles")
    if not bundles:
        failures.append(f"{path.name}: пустой dsh.profile.bundles")


def check_secrets(directory: pathlib.Path, failures: list[str]) -> None:
    for file in sorted(directory.rglob("*")):
        if not file.is_file() or file.suffix not in {".yml", ".yaml", ".json", ".example", ".md"}:
            continue
        if SECRET_RE.search(read_text(file)):
            failures.append(f"{file.name}: похоже на API-ключ — секреты в репозиторий не попадают")


def main() -> int:
    parser = argparse.ArgumentParser(description="Проверка примера профиля dsh")
    parser.add_argument("--patch", type=pathlib.Path, default=ROOT / "examples" / "cordis.patch.qwen.yml")
    parser.add_argument("--credentials", type=pathlib.Path, default=ROOT / "examples" / ".credentials.yaml.example")
    parser.add_argument("--package", type=pathlib.Path, default=ROOT / "examples" / "package.json")
    arguments = parser.parse_args()

    failures: list[str] = []
    config = check_patch(arguments.patch, failures)
    if config:
        check_credentials(arguments.credentials, config, failures)
        default = config.get("agent-default-model") or {}
        print(f"модель по умолчанию: {default.get('provider')}/{default.get('model')}")
        for route_name, route in ((config.get("llm-pi-ai") or {}).get("providers") or {}).items():
            models = ", ".join(model.get("id", "?") for model in route.get("models") or [])
            print(f"провайдер {route_name}: {route.get('apiKeyEnv')} -> {len(route.get('models') or [])} моделей")
            print(f"  {models}")
    check_package(arguments.package, failures)
    check_secrets(ROOT, failures)

    for failure in failures:
        print(f"FAIL: {failure}")
    print("OK" if not failures else f"провалено проверок: {len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())