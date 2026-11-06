# Tests

Run the automated checks from the project root with `python -m pytest`. `test_core_behaviour.py` checks the dashboard alert policy, face-match threshold selection, known/unknown/uncertain recognition decisions, and local event cooldown handling using synthetic data. These checks do not measure real-world accuracy.

Add owner-level checks here as modules are implemented, then add end-to-end tests that follow `docs/TEST_PLAN.md`. Use fake frames, synthetic event records and a mocked Streamlit alert state for automated checks; use consenting participants and a separately labelled camera dataset for recognition performance. Never commit real face images, embeddings or event databases as fixtures.
