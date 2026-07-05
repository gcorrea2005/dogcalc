# DogCalC — Structural Analysis Desktop App

Desktop app for 3D frame structural analysis, inspired by STAAD.Pro V8i workflow.

## Tech Stack

- **GUI:** PySide6 (Qt 6) + QGraphicsView (no OpenGL)
- **FEM Engine:** PyNite v3.0 — `pip install PyniteFEA[all]`
- **Persistence:** SQLite (.dogcalc files) + STAAD .std import/export
- **Export:** Excel (.xlsx) via openpyxl

## Quick Start

```bash
cd dogcalc
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

Or double-click `launch.command` from Finder.

## Controls (Mac)

| Action | Shortcut |
|--------|----------|
| Rotate view | LEFT drag / ← → arrows |
| Pan | RIGHT drag / ↑ ↓ arrows |
| Zoom | Scroll wheel |
| Node tool | `N` then double-click |
| Member tool | `M` then click 2 nodes |
| Orbit tool | `Esc` |
| Analyze | `F5` |
| Deformed shape | `F6` |
| Delete | `Del` then click entity |

## Features

- 3D isometric viewport with grid
- Node, Member, Support, Select, Delete tools
- Screen Menu (right panel, 6 submenus)
- STAAD-style Command Line (`NODE x,y,z`, `MEMBER n1,n2`, `ANALYZE`)
- Bidirectional .std file parser/writer
- FEM engine via PyNite (static analysis)
- Save/Load .dogcalc (SQLite)
- Export results to Excel
- 26 passing tests

## Examples

```bash
# Load example portico
File > Open STD... > examples/portico_2v_2p.std
```

## Architecture

```
dogcalc/src/
├── model/          Document + entities (Node, Member, Material, Section, LoadCase)
├── engine/         Bridge → PyNite + solver + results
├── controller/     ToolManager + tools + commands
├── view/           StructView (QGraphicsView) + camera + renderer
├── io/             project_file (.dogcalc) + staad_file (.std) + export
└── services/       Reports
```

## Tests

```bash
python -m pytest tests/ -v   # 26 tests
```
