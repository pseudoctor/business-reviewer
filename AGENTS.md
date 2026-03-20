# Repository Guidelines

## Project Structure & Module Organization
- `scripts/` contains the Python pipeline; `scripts/data_processor.py` is the main entry point.
- `raw_data/` holds input Excel files (sales `YYYYMM.xlsx`, inventory `YYYYMM库存.xlsx`).
- `data/` stores generated artifacts like `analysis_data.json`.
- `reports/` stores the HTML report output (e.g., `business_sales_inventory_report.html`).
- `docs/` contains specs and integration notes (`report_template_specification.md`, `INTEGRATION_GUIDE.md`).
- `config.yaml` defines file lists and thresholds; `requirements.txt` tracks Python deps.

## Build, Test, and Development Commands
- `./run.sh` (macOS/Linux) or `run.bat` (Windows): creates `venv`, installs deps, runs the pipeline.
- `python scripts/data_processor.py`: runs processing directly (activate `venv` first).
- `python scripts/data_processor.py --config my_config.yaml`: use a custom config.
- `python scripts/data_processor.py --debug`: enable verbose diagnostics.

## Coding Style & Naming Conventions
- Python, 4-space indentation, `snake_case` for functions/variables, `PascalCase` for classes.
- Prefer small, focused methods and clear section headers (see `scripts/data_processor.py`).
- Config keys in `config.yaml` are `snake_case` and mirror `Config` attributes.

## Testing Guidelines
- No dedicated test suite is present. If you add tests, use `pytest` and place them under `tests/`.
- Name tests as `test_*.py` and keep fixtures minimal; focus on data loading, cleaning, and KPI logic.

## Commit & Pull Request Guidelines
- Commit history follows Conventional Commits style (e.g., `feat:`, `fix:`, `refactor:`, `docs:`).
- Keep commits scoped to one change and update docs when you modify output format or calculations.
- No PR template is defined; include a clear description, config changes, and a sample report or JSON diff when output changes.

## Configuration & Data Notes
- Update `config.yaml` when changing input file names or risk thresholds.
- Inputs are expected in `raw_data/`; outputs are written to `data/` and `reports/`.
- If you add new fields to `analysis_data.json`, preserve existing structure to avoid breaking the report template.
