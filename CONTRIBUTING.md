# Contribute using GitHub in your browser

Team members can upload source files through github.com; they do not need to use a terminal.

## 1. Get repository access

The repository is private. A team member must be invited with **Write** access and accept the invitation before they can upload or change code.

The repository owner can invite people at:

1. Open the repository on GitHub.
2. Choose **Settings**.
3. Under **Access**, open **Collaborators and teams** (the exact label can depend on whether the owner is a personal account or an organisation).
4. Choose **Add people** or **Add teams**.
5. Find the collaborator by their GitHub username, choose the **Write** role, and send the invitation.
6. Ask them to accept the invitation before uploading.

Only invited collaborators can access the project. Write access lets a member change project files, so the team should review each other's work.

## 2. Upload a module through the browser

1. Open the repository and select the module folder they own. If the folder does not exist yet, use **Add file → Create new file** and include the folder in the filename, for example `src/selective_surveillance/detection/README.md`.
2. Select **Add file → Upload files**.
3. Drag the Python file(s) into the upload area or use the file picker.
4. Review the file names and contents before committing. Do not upload photos, face embeddings, databases, model weights, `.env` files or other private data.
5. Upload or edit files only inside your assigned folder. Under **Commit changes**, use a short description such as `Add person zone detection`.
6. Choose **Create a new branch for this commit and start a pull request**. Give the branch and pull request a clear module name, then propose the change.
7. The integration lead reviews the pull request and checks it against `docs/INTERFACES.md` before merging.

For a quick team exercise, an owner can commit a small change directly to `main`, but feature branches and pull requests make it easier to review and recover from mistakes.

## Module destinations

- Williams Emehel: `src/selective_surveillance/detection/`
- Emmanuel John: `src/selective_surveillance/facial_recognition/`
- Abubakar Ahmed: `src/selective_surveillance/alerting/` and `src/selective_surveillance/storage/`
- Ugochukwu Okoroji: `src/selective_surveillance/dashboard/`
- Josiah Frank Achile: `src/selective_surveillance/integration/`
- Joseph Ekuma: `evaluation/` and `tests/`

Before changing a shared record in `src/selective_surveillance/contracts.py`, coordinate with the integration lead and update `docs/INTERFACES.md` so every module continues to agree on its inputs and outputs.

Each person's implementation and README belong in that person's assigned folder so they can work, upload, and commit their part independently. Notebooks belong in `notebooks/` or that owner's module folder and must contain Python cells only. The real-time app is Python launched with Streamlit; there is no R or Telegram component.
