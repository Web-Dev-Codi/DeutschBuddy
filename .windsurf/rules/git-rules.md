---
trigger: always_on
description: This document defines the commit message conventions and workflow standards for this repository.Following these rules ensures clear project history, automated changelog generation, and improved team collaboration.
---

# Git Commit Rules

This document defines the commit message conventions and workflow standards for this repository.  
Following these rules ensures clear project history, automated changelog generation, and improved team collaboration.

## 1. Commit Message Format

Each commit message **must** have a clear structure:

<type>(<scope>): <short summary>

[optional body]

[optional footer(s)]

### Example

feat(api): add user authentication endpoint

Implements JWT-based authentication with refresh token support.
Updates routes and OpenAPI docs accordingly.

Closes #128

## 2. Allowed `<type>` Values

| Type | Description |
|------|--------------|
| **feat** | A new feature for the user or system |
| **fix** | A bug fix |
| **docs** | Documentation-only changes |
| **style** | Code style changes (formatting, no code effect) |
| **refactor** | Code restructure without behavior change |
| **perf** | Performance improvement |
| **test** | Adding or modifying tests |
| **build** | Changes to build system or dependencies |
| **ci** | Continuous integration configuration and scripts |
| **chore** | Routine tasks, maintenance, housekeeping |
| **revert** | Reverting a previous commit |

---

## 3. `<scope>` Guidelines

- Describes the area of the code affected (e.g., `ui`, `api`, `db`, `auth`, `docs`).
- Keep scope short and lowercase.
- Optional, but recommended for clarity.

**Example:**  

- `feat(ui): improve navbar accessibility`  
- `fix(db): correct migration structure`

## 4. Commit Summary Rules

- Use **imperative mood** (“add”, “update”, “remove”), not past tense.  
  ✅ `fix(auth): adjust token expiration logic`  
  ❌ `fixed auth module`

- Keep summary under **72 characters**.
- Do not capitalize the first letter after the colon.
- Do not end with a period.

## 5. Commit Body (Optional)

Use the body to explain **why** the change was made, not just **what** was done.

Include:

- Brief rationale behind the change  
- Key implementation notes or trade-offs  
- References to issues or PRs  

Wrap lines at 72 characters for readability.

## 6. Footer (Optional)

- Used for metadata or issue references.  
  Examples:
  - `Closes #42`
  - `Refs #128`
  - `BREAKING CHANGE: renamed config option "X" to "Y"`

## 7. Additional Recommendations

- Commit **small, logical units** of work.
- Run tests and linters **before** committing.
- Use `git rebase -i` before pushing to maintain a clean history.
- Avoid WIP or vague messages like “updates” or “misc fixes”.
- Each commit should be independently understandable.

## 8. Example Commit Series

feat(ui): add responsive navbar
fix(ui): correct logo sizing in mobile view
docs(readme): add setup section for environment variables
chore(deps): bump fastapi from 0.115 to 0.117

Adhering to these rules keeps the repository history clean, searchable, and release-ready.
Use a commit linter or Git hook (like `commitlint`) to enforce these conventions automatically.
