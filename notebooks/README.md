# Python notebooks

This folder is for cell-by-cell data science work using the Python kernel only. Put each notebook in a clearly named folder for its owner or scenario, for example `notebooks/joseph_scenario_evaluation/` or `notebooks/williams_zone_accuracy/`.

Use notebooks to inspect datasets, compare lighting/appearance/spoofing scenarios, calculate metrics, and explain experiments step by step. Keep the live application in the owner's importable Python module folder under `src/selective_surveillance/`; do not copy a second version of the application into a notebook. Never save private participant images, embeddings or event records into a notebook committed to Git.

Start with [`joseph_scenario_evaluation.ipynb`](joseph_scenario_evaluation.ipynb). It contains a plain Python trial format, input checks, scenario-level summaries, and aggregate CSV export. The example trial list is intentionally empty until real measurements are collected.
