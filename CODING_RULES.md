# AI Code Generation Rules

- Follow: KISS, YAGNI, DRY.
- Apply SOLID only when it improves maintainability.
- Apply Clean Code principles: prioritize readability, clarity, and maintainability.

## Implementation

- Implement only requested functionality.
- Use existing architecture, patterns, conventions, and dependencies.
- Prefer extending existing code over parallel solutions.
- Keep changes minimal and focused.
- Avoid unnecessary abstractions.
- Avoid premature optimization.
- Do not add dependencies without requirement.
- Do not refactor unrelated code.
- Do not introduce patterns without clear need.

## Code Quality

- Use clear, descriptive names.
- Keep functions focused.
- Prefer simple control flow.
- Use type hints where useful.
- Handle errors explicitly.
- Add comments only for non-obvious decisions or constraints.
- Group related comments instead of many small comments.

## Do Not

- Build for hypothetical requirements.
- Create unnecessary classes, interfaces, factories, services, or wrappers.
- Redesign existing architecture.
- Perform broad cleanup.

## Validation Workflow

- Run: Ruff.
- Run: Ruff Formatter.
- Run: mypy.
- Run: Bandit.
- Run: Radon/Xenon.
- Run: Vulture.
- Run: pytest + coverage.py.
- Run: pip-audit.

## Fix Workflow

- Fix only reported issues.
- Preserve behavior.
- Avoid unrelated refactoring.
- Keep changes minimal.
