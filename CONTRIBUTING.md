# Contributing to IntentGuard

Welcome to the IntentGuard project! To maintain a high standard of code quality and ensure a clean, readable project history, we follow strict development hygiene practices.

## Development Workflow

We use a feature branch workflow. All new features, bug fixes, or enhancements should be developed on a separate branch and merged into `main` via a Pull Request.

1. **Branch Naming**: Use descriptive branch names.
   - `feature/short-description` for new features
   - `fix/short-description` for bug fixes
   - `chore/short-description` for routine tasks

2. **Atomic Commits**: We require incremental, atomic commits.
   - **Avoid burst-style commits**: Do not lump unrelated changes (e.g., a UI update and a database migration) into a single commit.
   - **One logical change per commit**: Each commit should represent a single, cohesive change that passes tests on its own.
   - **Why?**: This makes the history easier to read, simplifies code review, and makes `git bisect` much more effective for tracking down regressions.

3. **Descriptive Commit Messages**:
   - Write clear, concise commit messages.
   - Start with a capitalized verb in the imperative mood (e.g., "Add", "Fix", "Update").
   - Do not end the subject line with a period.
   - If the commit requires explanation, leave a blank line after the subject and provide a detailed body.

## Code Quality and CI/CD

Our CI/CD pipeline runs on every push and pull request to `main`. It will automatically:
1. **Lint the code** using `flake8` to enforce Python style guidelines.
2. **Run tests** using `pytest`.
3. **Build containers** to ensure the Dockerfile is valid.

Your code must pass all CI checks before it can be merged.

## Running Tests Locally

Before committing, always run the test suite to ensure your changes haven't broken existing functionality:

```bash
# Run all tests
pytest backend/tests/ -v

# Run linting
flake8 backend/
```

Thank you for contributing to IntentGuard and helping us maintain a clean, professional codebase!
