# Voting strategies

Four strategies ship in alpha. Each is a Python function `(ballots, members, context) -> Outcome | "open"` with timeout policy baked in. The senate picks a default per proposal kind, but a proposer can override on call.

The strategy is **how the senate decides**; it does not change what is being decided. Pick by the cost of being wrong, not by the personalities involved.

---

## `majority`

> "More yes than no, late voters count as abstain."

**Behavior**: outcome is `approved` if `yes > no` once every eligible voter has cast or the timeout fires. Absentees count as abstain. Quorum: ≥ 1 ballot.

**Defaults**: timeout 30 min. Quorum trivial.

**Use for**:

- Admitting a new peer the founder (or any member) proposed.
- Adopting an internal convention that only affects how the senate operates (naming, agenda format).
- Anything routine where being wrong is cheap and reversible.

**Do not use for**:

- API contract changes that affect other pods (use `consensus_omnium`).
- Exile (use `supermajority`).

**Example decisions**: "Admit pod `bob` with the attached charter." "Adopt the convention of prefixing skill folders with `s_`."

---

## `supermajority`

> "Two-thirds, and a real quorum had to show up."

**Behavior**: `approved` if `yes / (yes + no) ≥ 2/3` AND `(yes + no + abstain) / eligible ≥ 2/3`. Late voters count as abstain. Outcome `rejected` if the threshold is mathematically unreachable; `timeout` otherwise.

**Defaults**: timeout 2 hours. Quorum 2/3 of admitted members.

**Use for**:

- **Exile** — removing a peer is destructive and partly irreversible (their `pods/<name>/` becomes `exile/<name>/`).
- **Completion** — declaring the project done shuts agents down; an aggrieved minority can block until concerns are addressed.
- **Revival** — bringing back an exiled pod with a fresh charter; needs broad buy-in to avoid re-litigating the exile.
- Any decision where a thin majority deciding against an entrenched minority would corrode trust.

**Do not use for**:

- Bootstrap admissions (too slow; majority is enough).
- Contract changes affecting a known set of consumers (use `consensus_omnium`).

**Example decisions**: "Exile pod `dave` for repeated contract breakages." "Declare the project complete." "Revive `erin` with a charter limited to read-only analytics."

---

## `consensus_omnium`

> "Every affected pod says yes, or it doesn't pass."

**Behavior**: `approved` only if every pod in `affected` casts `yes`. Any `no` is an immediate reject. Abstain blocks until cast or timeout, which becomes `rejected`. The `affected` list is computed by the senate when the proposal is opened — for contract changes, this is `state.callers_of(endpoint)` for each endpoint, plus the proposer.

**Defaults**: timeout 4 hours. Quorum is the full `affected` set; no one can be skipped.

**Use for**:

- **Contract changes** — every consumer must agree. This is the strategy that gives the system its safety property: you cannot break a downstream by majority.
- Cross-cutting refactors that touch a closed set of pods.
- Shared schema changes when the shared artifact is in production use.

**Do not use for**:

- Anything where the "affected" set is unbounded or unclear.
- Adding a peer (everyone is affected, in a sense, but unanimity blocks bootstrap).
- Internal conventions.

**Workflow tip**: convene a council (`coms.convene_council`) **before** opening the vote. Resolve objections in the council, close it with a summary, then open the proposal. Voting cold on a contract change is a procedural foul.

**Example decisions**: "Add `?cursor=` to `GET /users/{id}` and deprecate `?page=`." "Change the auth header from `X-Token` to `Authorization: Bearer`."

---

## `sortition`

> "Pick N citizens by lot. Their answer is the answer."

**Behavior**: senate samples `N` members uniformly at random when the proposal opens; only their ballots count. `approved` if their majority says yes. Other members can read the proposal but their ballots are ignored. Quorum: all `N` must vote; timeout becomes `timeout` outcome.

**Defaults**: `N = 3`, timeout 30 min. The sampled set is published in the proposal payload so peers can challenge bias.

**Use for**:

- Cheap, routine decisions where reading every member's input would waste tokens.
- Style/naming choices that need *a* decision more than *the right* decision.
- Tie-breaking on low-stakes inputs ("which of these three error formats?").

**Do not use for**:

- Anything destructive.
- Anything affecting a known consumer set (use `consensus_omnium`).
- Anything the founder or proposer feels strongly about — sortition is for genuinely fungible choices.

**Example decisions**: "Pick a default port range for the dev compose stack." "Rename `shared/utils` to `shared/lib` or leave as-is."

---

## Choosing a strategy — quick guide

| Decision kind | Strategy | Rationale |
| --- | --- | --- |
| New peer | `majority` | Cheap, reversible (you can later exile). |
| Exile | `supermajority` | Destructive; protect minority. |
| Revival | `supermajority` | Re-litigation risk; need consensus. |
| Contract change | `consensus_omnium` | Downstreams must agree or they break. |
| Completion | `supermajority` | Shuts the project down. |
| Internal style | `sortition` or `majority` | Cheap; tokens > principles. |
| Shared library API change | `consensus_omnium` over users | Same shape as contract change. |

## Common mistakes

- **Using `majority` for contract changes.** Eventually a thin majority will pass a change that breaks a consumer. Use `consensus_omnium`.
- **Using `consensus_omnium` for admissions.** One holdout permanently blocks growth. Use `majority`.
- **Using `sortition` for anything destructive.** Random samples on irreversible decisions destroy trust.
- **Opening a contract-change vote without a prior council.** Surprises are no votes. Convene, summarize, then propose.

When in doubt, **prefer the weaker strategy you can defend in an ADR**. The senate prefers loud agreement over silent technicality.
