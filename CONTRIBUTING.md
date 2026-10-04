# Contributing

Thank you for your interest in contributing to the **CIT Community Service Tracker**!
We welcome contributions from our team and the community. Please follow these guidelines to ensure smooth collaboration.

## Development workflow

1. **Fork the repository**
   - Go to [nncast/flask-community-service-tracker](https://github.com/nncast/flask-community-service-tracker).
   - Click the **Fork** button in the top-right corner to create a copy under your GitHub account.
   - Clone your fork locally:
     ```bash
     git clone https://github.com/<your-username>/flask-community-service-tracker.git
     cd flask-community-service-tracker
     ```
   - Add the original repository as an upstream remote so you can sync changes:
     ```bash
     git remote add upstream https://github.com/nncast/flask-community-service-tracker.git
     ```

2. **Create a branch** from `main` in your fork:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**, then commit and push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Open a pull request** against `nncast/flask-community-service-tracker:main`.

## Before you submit

- Keep commit messages clear and descriptive.
- Avoid committing secrets, credentials, local environment files, or virtual environments (`venv/`).
- Never commit the `instance/` folder — it holds the SQLite database (`dbcs.db`) and the session secret key.
- If you add or change behavior, update relevant documentation.
- Run the app locally (`python app.py`, see [`README.md`](README.md#quick-start)) and check the pages your change touches as both an **Admin** and an **Officer**.

## Code style

- Follow the existing project conventions.
- Prefer small, reviewable changes.
- Do not add unrelated formatting changes.

## Pull requests

Pull requests should include:

- a short summary of the change
- any relevant context or motivation
- testing steps or validation performed

## Security

Do not commit sensitive values such as database files, secret keys, passwords, tokens, or private configuration.

For security reports, follow [SECURITY.md](https://github.com/nncast/flask-community-service-tracker/blob/main/SECURITY.md).
