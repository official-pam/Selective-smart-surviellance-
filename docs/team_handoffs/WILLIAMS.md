# Williams: detection and restricted-zone handoff

**Repository:** [official-pam/Selective-smart-surviellance-](https://github.com/official-pam/Selective-smart-surviellance-)

## Your files

- `src/selective_surveillance/detection/engine.py`
- `src/selective_surveillance/detection/README.md`
- `configs/bytetrack.yaml`
- `configs/default.toml` only for agreed detector or zone settings
- Add focused detection checks under `tests/` when you change behavior. Coordinate before editing the shared `tests/test_core_behaviour.py`.

These files are already in the repository. Start from the latest `main`; do not replace the project with an old ZIP or overwrite other modules.

## Your responsibility

Return each detected person with a stable track ID, person box, zone state, and entry/exit transition. Keep detection and zone logic independent of identity decisions and alert wording. Use the zone and frame dimensions supplied by the application consistently. Do not add `best.pt`, private camera-zone files, face images, or videos to Git.

Before changing shared contracts or the controller, coordinate with Josiah. Describe behavior changes and measurements in your module README. Report measured detection/zone results and FPS only when you have run and recorded the scenario.

## Push your work with Git

Open a terminal and run:

```powershell
git clone https://github.com/official-pam/Selective-smart-surviellance-.git
cd Selective-smart-surviellance-
git switch -c williams/detection
```

Make and save your changes, then stage only your files and push the branch:

```powershell
git add src/selective_surveillance/detection configs/bytetrack.yaml
git add configs/default.toml
git commit -m "Improve person detection and zone tracking"
git push -u origin williams/detection
```

If you did not change `configs/default.toml`, omit it from `git add`. Then open the repository on GitHub, choose **Compare & pull request**, and create a pull request from `williams/detection` into `main`. The repository ruleset requires pull requests for `main`; do not force-push or commit directly to `main`.

## Before opening the pull request

- Confirm the changed files are limited to your module and agreed settings.
- Check `git status` and make sure no weights, `.env`, private data, logs, or videos are staged.
- Summarize what changed and include the scenarios or measurements you actually ran.
