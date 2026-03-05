Perform a critical analysis of the following Python codebase across these dimensions:

Pay particular attention to async patterns, Textual widget lifecycle and conventions, and Ollama SDK usage.
---

## 1. Architecture & Design

- Does the project structure follow a clear separation of concerns?
- Are modules/packages logically organized and cohesive?
- Is there inappropriate coupling between components?
- Are abstractions meaningful, or is there over/under-engineering?
- Does it follow SOLID principles where applicable?

## 2. Performance

- Identify any obvious bottlenecks (blocking I/O, N+1 patterns, unnecessary loops)
- Are expensive operations cached where appropriate?
- Is memory usage efficient? (large objects in memory, list vs generators, etc.)
- Are async/await patterns used correctly, or are there missed opportunities?
- Are there any redundant computations or repeated work?

## 3. Python Best Practices

- Is idiomatic Python used? (list comprehensions, context managers, unpacking, etc.)
- Are type hints present and accurate?
- Is error handling specific and meaningful, or are bare excepts used?
- Are dataclasses, enums, or Pydantic models used where plain dicts/tuples shouldn't be?
- Is `__init__.py` usage sensible?

## 4. Coding Conventions & Consistency

- Does the code conform to PEP 8?
- Are naming conventions consistent (snake_case, UPPER_CONST, PascalCase for classes)?
- Is there inconsistency in style between modules that suggests multiple authors without a linter enforced?
- Are docstrings present and following a consistent format (Google, NumPy, or reStructuredText)?

## 5. Maintainability & Readability

- Is there dead code, commented-out blocks, or TODO debt?
- Are functions/methods doing too much (violating single responsibility)?
- Are magic numbers or hardcoded strings used instead of constants or config?
- Is the code self-documenting, or does it rely on comments to explain poor naming?

## 6. Testing

- Is there test coverage? Are tests unit, integration, or only end-to-end?
- Are tests isolated and deterministic (no reliance on external state)?
- Are edge cases and failure paths tested?
- Is `pytest` used effectively (fixtures, parametrize, mocking)?

## 7. Security & Reliability

- Are secrets/credentials ever hardcoded or logged?
- Is user input validated and sanitized?
- Are dependencies pinned and auditable?
- Are there unhandled exceptions that could cause silent failures?

---

For each issue found:

- State the **file and line** (if reviewing a snippet, reference the relevant section)
- Rate severity: `critical` / `major` / `minor` / `nitpick`
- Explain **why** it's a problem
- Provide a **concrete fix or refactor**

End with a prioritized list of the top 5 changes that would have the highest impact.
