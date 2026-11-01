---
name: Visualize 3D
description: Построить живую 3D/WebGPU-визуализацию в панели OpenCode: поверхность по формуле или данным, меш/облако точек, шейдерная сцена, иллюстрация алгоритма или концепции. Использовать, когда просят «покажи/визуализируй/отрисуй в 3D», «построй поверхность/график/сцену/шейдер», или когда ответ понятнее как 3D-сцена. Работает без вмешательства человека: viz-сервер поднимается сам, панель открывается сама (focus=true).
---

# visualize — 3D-визуализация через плагин wgslviz

Инфраструктура: viz-сервер `opencode-plugins/wgsl-viz/server/server.py` (порт 8787)
хранит текущую сцену; плагин `wgslviz` рендерит её в нативной панели
«WGSL Viz» (OpenCode Desktop) и во вкладке встроенного браузера
`http://localhost:8787/index.html`. Подробности и troubleshooting —
`references/infra.md`. Контракт WGSL и схемы геометрии — `references/contract.md`.

> Пути даны от корня репозитория `opencode-skills/skills`. Если OpenCode
> запускается из другого каталога, замените `opencode-plugins/wgsl-viz` на
> абсолютный путь к этой папке.

## Workflow

1. **Сервер.** `GET http://127.0.0.1:8787/api/state?meta=1`.
   Не отвечает → запусти в фоне: `python opencode-plugins/wgsl-viz/server/server.py`.
2. **Классифицируй запрос** и выбери путь визуализации:
   - **медицинский объём (DICOM/NIfTI: CT, MRI…)** → два уровня:
     *интерактивный 3D в нашей панели*: `scripts/vol_prep.py --dicom <dir> --max-dim 256
     --out opencode-plugins/wgsl-viz/volumes/<name>` → push `geometry {kind:"volume", url, dims,
     spacing, min, max, mode, threshold}`; в панели: drag — орбита, wheel — зум,
     `1/2/3` — isosurface/MIP/transfer-function, `-`/`=` — порог HU;
     *интерактив рендерером ferrum (феррумовские TF/клип)*: frame-server
     `ferrum-cli serve -w <ws> --port 8788 --size 640` (держится в фоне) → push
     `geometry {kind:"stream", url:"http://127.0.0.1:8788/frame", preset:"lung_vessels",
     clipStr:"0,0.42,0:1,1,1", size:640, dragSize:320}`; drag — орбита (кадры 320px),
     отпустил — 640px; wheel — зум;
     *анализ и публикационные кадры*: FERRUM headless через MCP `tools.ferrum.*`
     (`ferrum_study_scan` → `ferrum_study_open` → `ferrum_view_slice` / `ferrum_view_mpr` /
     `ferrum_view_volume`); числа брать только из `ferrum_probe`/`ferrum_stats`;
     окно ferrum не запускать — рендер только через плагин;
   - поверхность по формуле, волны, heightfield → геометрия
     `{kind:"grid", nx:128, ny:128, size:6}` + `templates/heightfield.wgsl`
     (высота и нормали аналитически в vertex-шейдере, анимация через `params.z`);
   - поверхность/меш по данным (массив высот, CSV, точки) →
     `scripts/gen_geometry.py --surface "<формула>" …` (или собрать custom-меш
     своим скриптом) → геометрия `kind:"custom"`;
   - объект: сфера, тор, меш из данных → `kind:"sphere"` или custom
     (`gen_geometry.py --sphere …`);
   - шейдерное демо, освещение, материалы → `kind:"cube"|"sphere"` +
     `templates/phong.wgsl` или `templates/rim.wgsl`.
3. **Подготовь WGSL**: возьми шаблон из `templates/` и правь под задачу,
   не нарушая контракт (точки входа `vs_main`/`fs_main`, uniform
   `@group(0) @binding(0)` фиксированы — см. `references/contract.md`).
4. **Отправь сцену** инструментом плагина `push`:
   `{code, title, geometry, focus:true}`. Фокус сам открывает панель —
   человека дёргать нельзя. Без плагина fallback:
   `curl -X POST -H "Content-Type: application/json" -d @scene.json http://127.0.0.1:8787/api/scene`.
5. **Проверь**: инструмент `status` (версия/тайтл); при наличии browser-инструментов —
   скриншот вкладки `http://localhost:8787/index.html`. Ошибка WGSL → правь и пушь
   снова: рендереры пересобирают пайплайн горячо, без перезагрузки.
6. **Доложи**: что отрисовано, где смотреть (панель «WGSL Viz» / вкладка браузера),
   как управлять (drag — вращение, колесо — зум, Space — пауза).

## Принципы

- Никаких просьб к человеку «открой/нажми»: сервер и панель поднимаются сами.
- Сцена = WGSL + геометрия. Данные уходят в геометрию (`custom`), время — в
  `params.z`, параметры материала — в `params.x/y` (shininess, specStrength).
- Индексы > 65535 поддерживаются (uint32), но держись ≲ 200k треугольников.
- custom-меш: flat-массивы `positions/normals/colors` по 3 float на вершину +
  `indices`; согласованность длин обязательна.
- Если панель в Desktop не открылась (GUI-часть плагина отключена) — сцена всё
  равно видна во вкладке браузера и внешнем окне; сообщи об этом одной строкой.
