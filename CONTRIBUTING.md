# 🤝 Contributing to Stockly.ai

Thank you for your interest in contributing to **Stockly.ai**! All kinds of contributions are welcome — bug fixes, new features, AI model improvements, documentation updates, or design suggestions.

Please take a moment to read this guide before getting started.

---

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [How to Contribute](#how-to-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Features](#suggesting-features)
  - [Submitting a Pull Request](#submitting-a-pull-request)
- [Development Setup](#development-setup)
- [Style Guidelines](#style-guidelines)
- [Commit Message Guidelines](#commit-message-guidelines)

---

## 📜 Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone. Please be kind, constructive, and considerate in all interactions.

---

## 🚀 Getting Started

1. **Fork** the repository by clicking the "Fork" button on the [GitHub page](https://github.com/anshk1234/stockly.ai).

2. **Clone** your fork locally:

   ```bash
   git clone https://github.com/<your-username>/stockly.ai.git
   cd stockly.ai
   ```

3. **Set the upstream remote** so you can sync with the original repo:

   ```bash
   git remote add upstream https://github.com/anshk1234/stockly.ai.git
   ```

4. **Create a branch** for your changes:

   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## 📁 Project Structure

Understanding where things live will help you contribute to the right place:

```
stockly.ai/
├── .github/
│   └── workflows/       # CI/CD — GitHub Actions pipelines
├── .streamlit/          # Streamlit config (theme, secrets)
├── app/                 # Frontend — UI pages and Streamlit components
├── backend/             # Backend — data fetching, processing, API calls
├── models/              # AI/ML models — predictive analysis & summarisation
├── utils/               # Shared helpers and utility functions
├── requirements.txt     # Python dependencies
└── README.md
```

- **UI changes** → `app/`
- **Data / API logic** → `backend/`
- **AI model improvements** → `models/`
- **Shared helpers** → `utils/`
- **CI workflows** → `.github/workflows/`

---

## 🛠️ Development Setup

```bash
# Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app locally
streamlit run app/main.py
```

The app will be available at `http://localhost:8501`.

---

## 💡 How to Contribute

### Reporting Bugs

Found a bug? [Open an issue](https://github.com/anshk1234/stockly.ai/issues/new) with:

- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs. actual behaviour
- Screenshots or error messages (if applicable)
- Your Python version and OS

### Suggesting Features

Have an idea? [Open an issue](https://github.com/anshk1234/stockly.ai/issues/new) labeled `enhancement` and include:

- A clear description of the feature and its use case
- Which module it would live in (`app/`, `backend/`, `models/`, etc.)
- Any examples, mockups, or references (optional but appreciated)

### Submitting a Pull Request

1. Make sure your branch is up to date with `main`:

   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. Make your changes and **test them locally** by running the app.

3. If you're modifying AI models or backend logic, include a brief note in your PR description explaining your approach.

4. **Commit** your changes (see [Commit Message Guidelines](#commit-message-guidelines)):

   ```bash
   git add .
   git commit -m "feat(models): add LSTM-based price prediction model"
   ```

5. **Push** your branch:

   ```bash
   git push origin feature/your-feature-name
   ```

6. Open a **Pull Request** on GitHub against the `main` branch.
   - Provide a clear title and description of what your PR does.
   - Reference related issues (e.g., `Closes #12`).
   - The CI pipeline will run automatically — make sure it passes.

---

## 🎨 Style Guidelines

- Follow **PEP 8** for Python code style.
- Use meaningful, descriptive variable and function names.
- Keep functions small and focused — do one thing well.
- Add comments for non-obvious logic, especially in `models/` and `backend/`.
- Avoid committing unused imports or dead code.
- Keep `utils/` functions generic and reusable — no app-specific logic there.

---

## ✍️ Commit Message Guidelines

We loosely follow the [Conventional Commits](https://www.conventionalcommits.org/) format. Use a **scope** where relevant to indicate which part of the codebase was changed:

```
<type>(<scope>): <short description>
```

| Type | When to use |
|---|---|
| `feat` | Adding a new feature |
| `fix` | Fixing a bug |
| `docs` | Documentation changes only |
| `style` | Formatting, whitespace, no logic change |
| `refactor` | Code restructuring without feature/bug change |
| `chore` | Dependency updates, config changes |
| `ci` | Changes to GitHub Actions workflows |

**Scopes:** `app`, `backend`, `models`, `utils`, `ci`, `docs`

**Examples:**
```
feat(app): add candlestick chart to stock detail page
fix(backend): handle yfinance timeout on weekends
feat(models): add LSTM-based price trend prediction
docs: update project structure in README
ci: add linting step to main workflow
```

---

## ❓ Questions?

If you have any questions, feel free to open a [GitHub Discussion](https://github.com/anshk1234/stockly.ai/discussions) or drop a comment in an existing issue.

Thank you for helping make Stockly.ai better! 🚀
