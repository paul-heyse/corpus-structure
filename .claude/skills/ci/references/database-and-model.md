# Database and model changes

## Choose authority and inspect the target

```sh
uv run ci host status --json
uv run ci db status --json
uv run ci db status --maintenance --json
```

`host status` checks the dedicated development cluster. `db status` checks the database
through the reader by default. The maintenance variant reads the private migration revision.
Use the acquired identity and purpose in the result when deciding whether to proceed.

Use the persistent working development database for ordinary work. Use `ci host provision`,
`ci host roles`, `ci host up` or `ci host down` when the authorized effect is to change the
dedicated cluster or its roles. Use `ci db migrate` for ordinary development migration and
the documented exact-predecessor route for migration recovery. Use explicit deployment
profiles and their purpose credentials for a separate deployment endpoint.
See the [database operations owner](../../../../docs/design/D3-database.md#13-operating-postgresql-on-this-machine).

## Review a coordinated model change

Use `ci schema check` for a compile check. Use a typed change request when the change needs
coordinated declaration, generated or native effects. Include the applicable baseline,
proposed inputs, native predecessor, revision and deployment profile in the request.
See the [request model](../../../../python/corpus-structure/src/corpus_structure/schema/model_change.py).

```sh
uv run ci model change preview CHANGE.yaml --json
uv run ci model change inspect PREVIEW_ID
uv run ci model change inspect PREVIEW_ID --view patch
uv run ci model change apply PREVIEW_ID --json
```

Read the preview and patch before the apply. Use `--view discovery` for consumer discovery,
and `--view patch --stdout` for an exact safe patch stream to a consumer such as
`git apply --stat`. The preview binds reviewed inputs and applicable
effects. Apply by exact preview ID. If the inputs or predecessor differ, inspect the refusal
and prepare a fresh preview when the intended change differs. Use the existing ID for
supported recovery of the same approved change.

For an approved native change, author a rollback-only candidate on the bound development
database. Registering a candidate writes the exact frozen migration files into the checkout.
Deploy uses the registered candidate's bound target. The profile is in the change request
and the candidate, so `model change deploy` takes the candidate ID as its target binding.
Run the stages individually at their authorized boundaries.

```sh
uv run ci model change candidate PREVIEW_ID --json
uv run ci model change inspect-candidate CANDIDATE_ID
uv run ci model change register CANDIDATE_ID --json
uv run ci model change deploy CANDIDATE_ID --json
```

For a deployed profile, inspect with `ci db status --target deployment`,
`ci db check --target deployment --release RELEASE_ID` and
`ci release check --target deployment --release RELEASE_ID` as applicable. Activation
and selecting a completed run are separate effects. Supply the exact project, release or
run and target when carrying them out.

```sh
uv run ci release activate RELEASE_ID --project PROJECT --target deployment --json
uv run ci promote RUN_ID --project PROJECT --target deployment --json
```

An unconfigured profile, mismatched predecessor, role refusal or missing authority has
its own remedy. Inspect the configured and acquired binding before retrying.
See the [model change and deployment plan](../../../../docs/plans/cli-operations/model-change-and-deployment.md).
