# Project

## Dev philosophy

- Small functions. Declarative top levels. Parse at edge, fail fast.
- Flat over nested — early returns, guard clauses, max 2 indentation levels.
- Explicit over implicit. No hidden side effects. Dependencies flow inward.
- Types as documentation. Prefer failing on uncertain cases over handling everything.
- Tests mock collaborators; production never bends to make tests possible.
- Three similar lines is better than a premature abstraction. Don't design for hypothetical future requirements.
- Default to no comments. Only add one when the WHY is non-obvious (hidden constraint, subtle invariant, workaround). Never explain WHAT — names do that.
- No belt and suspenders pattern. Fail fast and surface errors.
- Prefer reliable battle tested opensource components over custom ones.

## Tooling rules

- Always use scaffolding/init commands to set up projects and packages (`pnpm init`, `pnpm create`, `npm init`, `tsc --init`, `biome init`, etc.).
- Always use the package manager to add dependencies (`pnpm add`, `npm install`, `uv add`). Never hand-write dependency entries.
- Never hand-write auto-generatable config files (lockfiles, tsconfig defaults, etc.) — run the tool and edit the output if needed.
- All imports at the top of the file. Never import inside functions.

## Working style

- Don't add features, refactor, or introduce abstractions beyond what the task requires. A bug fix doesn't need surrounding cleanup.
- Don't add error handling, fallbacks, or validation for scenarios that can't happen. Trust internal code and framework guarantees. Validate only at system boundaries (user input, external APIs).
- No backwards-compatibility shims when you can just change the code. No feature flags for hypothetical rollbacks.
- No half-finished implementations. If you can't complete it, say so explicitly rather than leaving stubs.
- Root-cause obstacles instead of bypassing them (no `--no-verify`, no silencing type errors, no deleting failing tests).

## Important constraints

- Everything async where it matters — never block the UI or event loop.
- Every external process gets a hard timeout. No unbounded waits.
- Never commit secrets. Strip credentials from any environment a tool or agent inherits.
- Type checker and linter are gates, not suggestions. Fix the root cause, don't suppress.

## Writing style

- Be brief.

