# AC14 managed recognition refresh

Prospective current-source provider controls, 2026-11-03. `refresh.py` uses a newly owned local
service on port8135 and an exclusive output directory. Historical managed-recognition payloads
are read-only inputs; historical scripts and receipts are not modified.

The probe records verified startup generations, missing/wrong/admitted-generation HTTP outcomes,
replacement-byte startup refusal, sleep/wake, an in-flight streamed request crossing graceful
shutdown, restart/stale-generation behavior, and the actual application controller → isolated
public parser → service journey. It terminates only its own service process groups. It does not
modify an application database, defaults, model exports or host configuration.

Command:

```sh
uv run python docs/design_review/evidence/2026-11-03_ac14-acceptance/managed-recognition/refresh.py --output docs/design_review/evidence/2026-11-03_ac14-acceptance/managed-recognition/attempt-001
```

Current outcome: **passed, bounded, 2026-11-03**. `attempt-001.log` and its receipt directory
retain actual startup/control/application results. Both generations differed; stale-generation
requests refused and current-generation requests succeeded. The application retained two actual
requests with matching admitted/response generation. `cleanup.json` independently verifies the
owned port is reusable and all logged service process IDs have exited. vLLM's shutdown semaphore
warnings remain in raw startup logs; they did not leave an owned process alive.

`executed-refresh.py.txt` preserves the byte-exact executed harness. `executed-harness.json`
records its SHA256 and AST agreement with the current probe; no formatter ran on it. Historical
receipts remain unchanged. Source context hashes cover the launcher,
custody middleware, isolated worker, application controller and probe at invocation. AC's coordinator
owns final-source applicability and complete acceptance; this probe does not establish recognition
accuracy, full-book conversion, M1 family quality or complete AC14 qualification.
