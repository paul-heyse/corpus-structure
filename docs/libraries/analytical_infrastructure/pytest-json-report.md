# pytest-json-report — Comprehensive Python Library Overview

Research date: November 17, 2026 | Latest published release: 1.5.0 | License: MIT

## 1. Executive overview

`pytest-json-report` is a pytest reporting plugin that converts test-session events into a structured, machine-readable JSON document. It provides more than a pass/fail summary: it preserves test identities, collection results, execution phases, timing, captured output, logging records, failure diagnostics, warnings, and extensible metadata.

Its principal architectural value is turning pytest's event-driven reporting model into a data artifact that other software can analyze without parsing terminal output or reconstructing test execution from logs.

Official project: [https://github.com/numirias/pytest-json-report](https://github.com/numirias/pytest-json-report?utm_source=chatgpt.com)

Package: [https://pypi.org/project/pytest-json-report/](https://pypi.org/project/pytest-json-report/?utm_source=chatgpt.com)

### Capability map

| Capability               | What the library provides                                                                      |
| ------------------------ | ---------------------------------------------------------------------------------------------- |
| Session reporting        | Execution duration, exit status, collected and executed test counts, outcome distribution      |
| Collection introspection | Collected node identities, node types, source locations, deselection, collection errors        |
| Phase-level execution    | Separate setup, call, and teardown outcomes and durations                                      |
| Failure diagnostics      | Crash locations, structured traceback frames, assertion/error representations                  |
| Output capture           | Per-phase stdout, stderr, and Python logging records                                           |
| Structured annotations   | Per-test metadata, pytest user properties, session environment metadata                        |
| Report customization     | Hooks for per-test metadata, stage serialization, and whole-report mutation                    |
| Programmatic access      | In-memory report objects, explicit saving, and `pytest.main()` integration                     |
| Parallel execution       | Integration with pytest-xdist workers and controller-side aggregation                          |
| Output control           | Summary-only output, selective field omission, indentation, file paths, and terminal verbosity |

These capabilities support several distinct uses: test-result ingestion, automated failure classification, regression analysis, test inventory generation, execution observability, and construction of custom reporting systems.

The important boundary: the package is a report producer, not a test orchestration engine, historical results database, streaming event protocol, or analytics system. It consumes pytest-generated events and produces a snapshot of the session. Persisting results across runs, correlating history, and performing statistical analysis remain responsibilities of downstream systems.

### Version and maintenance status

Older published release

Version 1.5.0 · March 15, 2022

PyPI identifies 1.5.0 as the latest published release, despite the library continuing to appear in current pytest plugin listings. The package declares `pytest>=3.8.0` and depends on `pytest-metadata`, without an upper version bound. Its published classifiers and CI matrix cover Python 3.7–3.10. These declarations do not establish verified compatibility with recent pytest 9.x or Python 3.14 releases.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



A particularly consequential compatibility issue emerged from inspecting the source: `pytest-json-report` reads session metadata from `config._metadata`, whereas `pytest-metadata` 3.0.0 switched to `config.stash` in May 2023. Consequently, with modern `pytest-metadata`, the `environment` field is liable to be empty unless another integration restores the legacy attribute or explicitly populates the report. This is a source-supported interoperability mismatch, not a claim based on executing the combination.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



The analysis below describes the functionality of the published 1.5.0 implementation and distinguishes its documented behavior from limitations inferred from the source.

## 2. Execution model and pytest integration

The library's implementation is built around pytest's hook system, rather than a separate test runner or a postprocessing parser.

It is useful to think of the package as comprising three layers:

pytest execution engine

Collection, fixtures, setup, call, teardown, warnings, execution status

pytest-json-report hooks

Capture phase data, merge metadata, serialize events, aggregate test identities

Session report

In-memory Python dictionary → optional JSON file → external consumers

### 2.1 Plugin activation

The package registers itself through the `pytest11` entry-point mechanism. Installation makes its CLI options available to pytest, but ordinary execution does not automatically produce a report.

When `--json-report` is supplied, `pytest_configure` registers either:

- `JSONReport`, for the main pytest process, responsible for aggregation and output.
- `JSONReportWorker`, for pytest-xdist worker processes, responsible for capturing additional test-stage information.

Both inherit behavior from `JSONReportBase`.

This separation is important: parallel workers do not independently write competing JSON reports. They contribute execution data that the controller aggregates.

The relevant implementation is in `pytest_jsonreport/plugin.py`.

Source: [https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/plugin.py](https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/plugin.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 2.2 Hook-driven lifecycle

| Pytest hook                 | Role in JSON reporting                                           |
| --------------------------- | ---------------------------------------------------------------- |
| `pytest_sessionstart`       | Starts session-duration measurement                              |
| `pytest_collectreport`      | Captures collection nodes, their children, and collection errors |
| `pytest_deselected`         | Tracks deselection counts and annotates known collected items    |
| `pytest_runtest_protocol`   | Establishes per-test metadata/capture context                    |
| `pytest_runtest_setup`      | Captures logging during fixture setup                            |
| `pytest_runtest_call`       | Captures logging during test execution                           |
| `pytest_runtest_teardown`   | Captures logging during fixture teardown                         |
| `pytest_runtest_makereport` | Adds captured streams and custom metadata to stage reports       |
| `pytest_runtest_logreport`  | Aggregates stage reports by test node ID                         |
| `pytest_warning_recorded`   | Collects pytest warnings                                         |
| `pytest_sessionfinish`      | Builds and optionally saves the completed report                 |

The distinction between `pytest_runtest_makereport` and `pytest_runtest_logreport` is consequential.

The former still has access to the live pytest `Item` and `CallInfo` objects, enabling inspection of execution context and custom metadata creation. The latter receives the completed `TestReport`, which is the representation that can be transmitted from xdist workers to the controller.

The plugin attaches additional data to the report using `_json_report_extra`. This allows custom per-test information and captured logs to cross the worker/controller boundary without a separate application-level transport.

### 2.3 Report construction and output lifecycle

The plugin accumulates test information into an `OrderedDict` keyed by `nodeid`. At session completion, it builds a Python dictionary, invokes customization hooks, exposes the report as `JSONReport.report`, and optionally writes JSON to disk.

The file is written once at the end of the session, using Python's `json.dump`.

Consequences include:

- Normal test failures do not prevent report creation. The session can exit unsuccessfully while still producing structured results.
- Hard process termination is different. A killed controller or machine failure may leave no completed report.
- Output is not incremental. It cannot be treated as an append-only execution log.
- Memory is consumed throughout the run. Per-test details, diagnostic content, and warning records remain in memory until report construction completes.
- The file is overwritten, rather than appended to or atomically replaced by an explicitly managed temporary file.

The plugin constructs `created` using the current time at report generation, whereas `duration` is measured from `pytest_sessionstart`.

Source: [https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/plugin.py](https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/plugin.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



## 3. Report structure and semantic contract

The report is a conventional nested JSON object, but its structure is derived from pytest's execution model rather than from a separately defined, versioned schema.

### 3.1 Top-level representation

| Field         | Type            | Interpretation                              |
| ------------- | --------------- | ------------------------------------------- |
| `created`     | Number          | Unix timestamp of report generation         |
| `duration`    | Number          | Elapsed session duration in seconds         |
| `exitcode`    | Integer         | Pytest exit status                          |
| `root`        | String          | Session root path                           |
| `environment` | Object          | Environment/session metadata when available |
| `summary`     | Object          | Outcome counts and collection information   |
| `collectors`  | Array, optional | Collection tree observations and errors     |
| `tests`       | Array, optional | Test-level results with execution phases    |
| `warnings`    | Array, optional | Session warning records                     |

For example, an abbreviated, illustrative report might look like this:

```
{
  "created": 1795000000.0,
  "duration": 1.24,
  "exitcode": 1,
  "root": "/workspace",
  "environment": {},
  "summary": {
    "collected": 1,
    "failed": 1,
    "total": 1
  },
  "tests": [
    {
      "nodeid": "tests/test_example.py::test_value",
      "lineno": 7,
      "outcome": "failed",
      "setup": {
        "duration": 0.01,
        "outcome": "passed"
      },
      "call": {
        "duration": 0.02,
        "outcome": "failed",
        "longrepr": "AssertionError: expected value"
      },
      "teardown": {
        "duration": 0.01,
        "outcome": "passed"
      }
    }
  ]
}
```

This is a structural illustration, not output from an executed test.

The actual fields depend on the test's behavior, pytest configuration, installed plugins, and the report's omission settings.

Schema documentation: [https://github.com/numirias/pytest-json-report/blob/v1.5.0/README.md](https://github.com/numirias/pytest-json-report/blob/v1.5.0/README.md?utm_source=chatgpt.com)

Serialization implementation: [https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/serialize.py](https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/serialize.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 3.2 Session summary

The summary captures two conceptually different measurements.

Collection counts describe pytest's test-discovery activity:

- `collected`: total collected test items, including those subsequently deselected.
- `deselected`: tests excluded by selection mechanisms, when nonzero.

Execution counts describe the test items for which result records were assembled:

- `total`: number of distinct test result entries in the report.
- `passed`, `failed`, `error`, `skipped`, `xfailed`, `xpassed`, and other outcome categories if produced by pytest.

Outcome keys are omitted when their counts are zero.

The plugin computes outcomes using pytest's `pytest_report_teststatus` hook rather than simply copying `TestReport.outcome`. This allows it to represent expected failures and execution errors using pytest's reporting classifications.

The source computes `summary.total` from the number of test objects in its `nodeid`-keyed result dictionary. It is therefore not equivalent to the number of individual execution-stage events. It also does not necessarily equal `collected - deselected`, particularly after collection failures or interrupted runs.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



Practical interpretation: use `exitcode` to assess overall session success and `summary` for observed execution outcomes. Do not infer that zero failed tests means collection and execution completed successfully.

### 3.3 Test identity and source location

Every test object contains:

- `nodeid`: pytest's test identity, including parametrization identifiers where applicable.
- `lineno`: source line associated with the test.
- `outcome`: overall test result.

Optional `keywords` expose names and markers associated with the pytest test report.

For example:

```
tests/test_validation.py::TestParser::test_valid_input[unicode]
```

This provides a useful linking key for external systems, but its stability is conditional. Renaming tests, moving modules, changing parametrization IDs, or modifying pytest's collection behavior can change node IDs.

The test and collector `lineno` values come from pytest's `location[1]`, which uses zero-based line indexing. Diagnostic `crash` and `traceback` locations are taken from pytest's traceback representations and should be interpreted according to those structures rather than assuming identical indexing.

Pytest's node-ID semantics: [https://docs.pytest.org/en/stable/example/markers.html](https://docs.pytest.org/en/stable/example/markers.html?utm_source=chatgpt.com)

### 3.4 Collection results are first-class data

The `collectors` array is an easily overlooked capability.

A collector entry includes:

| Field      | Meaning                                          |
| ---------- | ------------------------------------------------ |
| `nodeid`   | Identity of the collector                        |
| `outcome`  | Collection result, independent of test execution |
| `result`   | Child nodes discovered                           |
| `longrepr` | Textual collection error, when applicable        |

Child entries contain `nodeid`, a pytest node class name such as `Module` or `Function`, an optional `lineno`, and an optional `deselected` flag.

This makes it possible to distinguish:

- Tests that exist but were deselected.
- Modules that failed to import.
- Files that produced syntax or collection errors.
- Successful discovery without corresponding execution.
- Tests whose execution reports were actually emitted.

An external tool can therefore build a test inventory or identify discovery failures without reconstructing information from pytest's terminal output.

Important qualification: the collector representation is not a general-purpose, persistent AST or fixture-dependency graph. It reflects pytest's collection events and discovered nodes.

Under xdist, successful collector records are generally absent, which limits its suitability as a complete discovery inventory during parallel execution. That distinction is discussed in Section 6.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 3.5 Phase-level test results

The library models the three pytest execution phases separately:

setup

Fixtures and preparation

call

Test body execution

teardown

Fixture cleanup

Each phase can have its own outcome, duration, diagnostics, and captured output.

This distinction is much more useful than a single test status for diagnosing fixture-related failures.

For example, a test may have:

```
{
  "outcome": "error",
  "setup": {
    "outcome": "failed",
    "duration": 0.04
  },
  "teardown": {
    "outcome": "passed",
    "duration": 0.01
  }
}
```

There is no `call` object because the test body did not execute.

A teardown failure is similarly distinguishable from an assertion failure inside the test body.

For timing analysis, phase durations are independent measurements. They are not an exclusive attribution of all session time: collection, plugin overhead, scheduling, and other activities occur outside or around them. In parallel runs, summed phase durations can also exceed wall-clock session duration.

## 4. Diagnostic capture and failure information

The plugin's diagnostic capabilities are particularly valuable because they provide both structured fields and representations that retain pytest's original context.

### 4.1 Failure and traceback representation

A failed stage can contain:

| Field       | Description                                |
| ----------- | ------------------------------------------ |
| `crash`     | Primary error location and message         |
| `traceback` | Sequence of structured traceback locations |
| `longrepr`  | Pytest's formatted error representation    |

A `crash` location has:

```
{
  "path": "tests/test_example.py",
  "lineno": 42,
  "message": "AssertionError"
}
```

A `traceback` is an array of similarly structured locations, representing entries pytest exposes for that error.

The distinction matters when building failure-analysis tools:

- `crash` offers a concise candidate failure location.
- `traceback` supports navigation across relevant frames.
- `longrepr` preserves information that may not be captured by those structured fields, including pytest assertion explanations.

The structured representation is not guaranteed for every failure or traceback configuration.

The package specifically handles cases in which pytest's `longrepr` does not expose normal traceback-entry objects. Its own tests confirm that `--tb=long` and `--tb=short` can provide structured tracebacks, whereas `--tb=native`, `--tb=line`, and `--tb=no` omit that structure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



Omitting `traceback` does not necessarily remove failure information from `longrepr` or `crash`. These are separate fields.

This is significant for both size optimization and redaction.

### 4.2 Captured stdout and stderr

The plugin extracts captured streams from pytest's per-item report sections and associates them with the appropriate execution phase.

It can distinguish, for example:

- Output from fixture initialization.
- Output emitted by the test body.
- Output emitted during cleanup.

This is more precise than attributing all captured output to a test without phase information.

The capture behavior still depends on pytest. Disabling capture with `-s` or using a different `--capture` mode changes what pytest makes available.

`--json-report-omit=streams` suppresses the `stdout` and `stderr` JSON fields. It does not independently change pytest's global capture configuration.

Pytest capture documentation: [https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html](https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html?utm_source=chatgpt.com)

Implementation and tests: [https://github.com/numirias/pytest-json-report/blob/v1.5.0/tests/test_jsonreport.py](https://github.com/numirias/pytest-json-report/blob/v1.5.0/tests/test_jsonreport.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 4.3 Structured Python logging

Rather than storing only preformatted log text, the plugin serializes attributes from Python `logging.LogRecord` instances.

Important preserved fields can include:

- Logger name and severity.
- Source pathname, filename, module, function, and line number.
- Record creation time.
- Thread and process identifiers.
- Other attributes present on the record.

The library normalizes several fields:

- `msg` becomes the formatted message.
- `args` is set to `None`.
- `exc_info` is set to `None`.

The resulting dictionary can be passed to `logging.makeLogRecord()` to reconstruct a record-like object, although this cannot restore information that was discarded during serialization.

The source implements this through an additional handler on Python's root logger, installed separately around each execution phase.

This has useful but subtle consequences:

1. The logger's existing propagation and filtering behavior still matters.
2. Records emitted by unrelated concurrent threads can potentially be captured during the active phase because the root handler is not filtered by test identity.
3. Additional custom `LogRecord` attributes can enter the report, subject to serialization behavior.
4. The representation is focused on standard Python logging; it is not an automatic adapter for every structured-logging system.

The `--json-report-omit=log` option avoids installing these handlers during the test phases, making it more than a cosmetic output filter.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 4.4 Warning records

Warnings are collected from pytest's warning-reporting hooks and serialized as objects containing:

```
{
  "message": "example warning",
  "category": "UserWarning",
  "when": "runtest",
  "filename": "tests/test_example.py",
  "lineno": 15
}
```

The `when` field identifies the warning phase, such as configuration, collection, or test execution.

An important documentation discrepancy exists here: the README's illustrative warning JSON includes fields such as `code`, `path`, and `nodeid`, but the actual 1.5.0 serializer emits `message`, `category`, `when`, `filename`, and `lineno`. The upstream tests confirm the implementation's five-field format.

For consumers, the tagged serializer and tests are more reliable evidence of this contract than the stale example.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



## 5. Metadata and extensibility

The extension mechanisms are arguably the library's most distinctive capabilities. They permit both enrichment of the standard report and replacement of portions of the serialization process.

### 5.1 Per-test metadata through `json_metadata`

The `json_metadata` fixture provides a mutable dictionary associated with the current test item.

```
def test_parser(json_metadata):    json_metadata["component"] = "parser"    json_metadata["scenario"] = {        "category": "malformed-input",        "expected": "rejection",    }
```

The resulting test record can include:

```
{
  "metadata": {
    "component": "parser",
    "scenario": {
      "category": "malformed-input",
      "expected": "rejection"
    }
  }
}
```

Metadata can be populated during fixture setup, test execution, and teardown because the dictionary belongs to the test's reporting context rather than solely to the test function call.

This supports domain-specific annotations without creating a separate reporting transport.

For example, consumers may want to preserve test scenario attributes, dataset identifiers, input categories, model configuration labels, or other structured descriptors.

Serialization constraint: metadata must be JSON-serializable. The implementation validates the accumulated metadata using `json.dumps`. If serialization fails at a reporting stage, it issues a warning and removes the entire `metadata` entry rather than selectively removing the offending value.

Empty metadata is not included in the final test record.

Also notable: when JSON reporting is inactive, the fixture returns a dummy empty dictionary. Tests that declare `json_metadata` can therefore run without activating JSON report generation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



### 5.2 Dynamic metadata through hooks

The library provides three custom reporting hooks.

| Hook                                       | Invocation point                    | Extension capability                        |
| ------------------------------------------ | ----------------------------------- | ------------------------------------------- |
| `pytest_json_runtest_metadata(item, call)` | During stage report construction    | Produce/merge per-test metadata             |
| `pytest_json_runtest_stage(report)`        | During phase serialization          | Replace a stage's serialized representation |
| `pytest_json_modifyreport(json_report)`    | After assembling the session report | Modify the entire output dictionary         |

These hooks have materially different semantics.

#### `pytest_json_runtest_metadata`: enrich the test item

This hook receives the pytest `Item` and `CallInfo`. It can add metadata derived from the current execution phase.

```
import pytest@pytest.hookimpl(optionalhook=True)def pytest_json_runtest_metadata(item, call):    if call.when != "call":        return {}    return {        "phase_started": call.start,        "phase_finished": call.stop,        "nodeid": item.nodeid,    }
```

Returned dictionaries are merged into the current test's metadata.

When multiple implementations return dictionaries, the plugin updates a shared metadata dictionary sequentially. Colliding keys can therefore overwrite earlier values according to hook result order.

The hook can expose valuable context available at execution time without requiring all data to be encoded into pytest markers.

#### `pytest_json_runtest_stage`: replace stage serialization

This hook can control how a pytest `TestReport` becomes a JSON phase object.

```
@pytest.hookimpl(optionalhook=True)def pytest_json_runtest_stage(report):    return {        "outcome": report.outcome,        "duration": report.duration,    }
```

The hook specification uses `firstresult=True`. The plugin provides its default serializer with `trylast=True`, allowing a user implementation to return its own representation.

Crucially, this is replacement, not augmentation. Returning only `outcome` and `duration` removes the standard stage's `stdout`, `stderr`, `log`, `crash`, `traceback`, and `longrepr` fields unless the custom serializer explicitly includes them.

This is useful for specialized downstream schemas, but introduces responsibility for retaining information that matters.

#### `pytest_json_modifyreport`: transform the completed document

This hook receives the whole mutable report dictionary.

```
@pytest.hookimpl(optionalhook=True)def pytest_json_modifyreport(json_report):    json_report["schema_family"] = "internal-test-report"    json_report["schema_version"] = 1
```

This is the natural integration point for:

- Adding a consumer-defined schema version.
- Restructuring fields for a destination system.
- Redacting sensitive fields.
- Adding derived summaries.
- Normalizing or supplementing environment metadata.
- Removing unwanted data before serialization.

The plugin does not restrict these mutations to predefined report fields.

Because consumers can arbitrarily change the structure, one deployment's JSON output is not necessarily interchangeable with another deployment's output even if both use `pytest-json-report` 1.5.0.

Source: [https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/plugin.py](https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/plugin.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 5.3 Optional-hook registration

An important pluggy integration detail: the package registers its custom hook specifications only when JSON reporting is active.

A `conftest.py` containing a `pytest_json_*` implementation may otherwise produce an unknown-hook validation error.

The documented solution is:

```
@pytest.hookimpl(optionalhook=True)def pytest_json_modifyreport(json_report):    ...
```

Using `optionalhook=True` allows the same pytest configuration to operate whether or not `--json-report` is enabled.

This is especially relevant to reusable pytest plugins and test suites where JSON reporting is optional.

### 5.4 Integration with pytest's `record_property`

The plugin also preserves pytest's existing `record_property` user properties.

```
def test_example(record_property):    record_property("dataset", "dataset-A")    record_property("run", 42)    record_property("dataset", "dataset-B")
```

The report stores them in a `user_properties` array:

```
[
  {"dataset": "dataset-A"},
  {"run": 42},
  {"dataset": "dataset-B"}
]
```

This capability is not prominently documented in the README, but it is implemented and explicitly tested.

The representation has several important differences from `metadata`:

| Property                 | `metadata`                               | `user_properties`                               |
| ------------------------ | ---------------------------------------- | ----------------------------------------------- |
| Source                   | `json_metadata` fixture or metadata hook | Pytest's `record_property` fixture              |
| Representation           | Object/dictionary                        | Array of single-key objects                     |
| Duplicate keys           | Overwritten through dictionary updates   | Preserved as separate entries                   |
| Serialization validation | Whole metadata dictionary checked        | Whole user-properties array checked             |
| Report timing            | Accumulated across phase reporting       | Copied into the JSON test on teardown reporting |

Because `user_properties` are only attached when a teardown report is processed, unusual execution interruptions can leave them absent even when some earlier test information survives.

This feature can reduce the need to invent a separate annotation mechanism when another pytest integration already uses `record_property`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



## 6. Parallel execution, reruns, and collection semantics

### 6.1 pytest-xdist integration

`pytest-json-report` contains explicit integration for `pytest-xdist`.

The source distinguishes a worker by the presence of `config.workerinput`, instantiates `JSONReportWorker`, and relays additional information through attributes attached to pytest's reports.

The controller receives stage reports and aggregates them by `nodeid`.

The project's tests exercise both single-worker and multiworker configurations.

However, parallel execution changes several observable properties of the report.

Collector coverage is asymmetric. In the upstream tests, successful collection nodes are not available in the controller's report under xdist. Failed collectors are still represented.

This means the `collectors` array is not a complete discovery inventory in the same way as it can be during normal, nonparallel execution.

Warning counts can differ. A warning during collection may be emitted by multiple workers. The upstream tests explicitly acknowledge incomplete warning relay/deduplication behavior.

Ordering reflects event receipt. The report uses an insertion-ordered dictionary, but insertion order under xdist depends on when results arrive. It is not a deterministic test-suite order.

Worker crashes can lose detail. The implementation handles reports whose custom `_json_report_extra` attribute is missing, including replacement reports arising from a crashed worker. The test outcome may survive while its associated custom metadata or captured diagnostics do not.

These distinctions are visible in the upstream source and tests; they are not guarantees about every modern xdist release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



### 6.2 Reruns and flaky-test plugins

The aggregation key is the test's `nodeid`.

When multiple reports for the same test identity arrive during one session, they update the same test object. Phase fields are assigned by phase name and may be replaced by later reports.

This has an important implication for integrations such as `pytest-rerunfailures`: the native report representation is oriented around one aggregated test result per node ID, not a durable sequence of every execution attempt.

Although reruns may influence the eventual pytest outcome, the standard schema does not provide a first-class attempt-history array with timestamps, outcomes, and diagnostics for each retry.

Capturing complete retry histories would require additional instrumentation or a reporting format with explicit attempt events.

The distinction is not merely cosmetic: a test that fails twice and passes on the third attempt can have materially different reliability implications from one that passes immediately.

### 6.3 Deselection and selective execution

Pytest selection mechanisms such as `-k`, `-m`, and `--last-failed` affect which tests receive execution records.

The plugin preserves the overall deselection count and, where collector objects are available, marks individual collected items as deselected.

The source also handles cases in which an item was deselected without a corresponding earlier JSON collector item—for example, some `--last-failed` paths.

Thus, the report can often distinguish tests omitted by selection from tests that executed and were skipped.

That distinction is valuable for coverage-of-test-execution analysis, but it is not equivalent to source-code coverage measurement.

## 7. Configuration and programmatic interfaces

### 7.1 Command-line configuration

| Option                      | Behavior                                                                              |
| --------------------------- | ------------------------------------------------------------------------------------- |
| `--json-report`             | Enables report generation                                                             |
| `--json-report-file=PATH`   | Sets output path; default `.report.json`                                              |
| `--json-report-file=none`   | Builds the report but skips automatic saving                                          |
| `--json-report-summary`     | Retains session fields and summary, omitting detailed tests, collectors, and warnings |
| `--json-report-omit ...`    | Omits selected detail categories                                                      |
| `--json-report-indent=N`    | Controls JSON indentation                                                             |
| `--json-report-verbosity=N` | Controls the plugin's terminal status output                                          |

The supported omission categories are:

`collectors`, `log`, `traceback`, `streams`, `warnings`, `keywords`.

For example:

```
pytest tests/ \
  --json-report \
  --json-report-file=artifacts/results.json \
  --json-report-omit log streams keywords
```

The omission argument accepts a space-separated sequence, not a comma-separated string.

A report containing just aggregate information:

```
pytest tests/ --json-report --json-report-summary
```

A report retained only in memory:

```
pytest tests/ --json-report --json-report-file=none
```

A human-readable report:

```
pytest tests/ --json-report --json-report-indent=2
```

The `--json-report-verbosity` option only controls the terminal status section associated with JSON reporting. It does not adjust the information density of the JSON document itself.

The plugin's source uses `nargs='+'` for `--json-report-omit`; place positional test paths before that option to avoid ambiguity about which arguments are omission fields.

Source: [https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/plugin.py](https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/plugin.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 7.2 Direct use with `pytest.main()`

The package exposes the `JSONReport` class for programmatic execution.

```
import pytestfrom pytest_jsonreport.plugin import JSONReportreporter = JSONReport()exit_code = pytest.main(    [        "tests/",        "--json-report-file=none",    ],    plugins=[reporter],)report = reporter.reportif report is not None:    print(report["summary"])    reporter.save_report("artifacts/results.json")
```

The `report` attribute is a Python dictionary containing the constructed session report.

This provides several architectural possibilities:

- Calling pytest as part of an existing Python process.
- Accessing structured results without writing and rereading a temporary file.
- Passing the report to other Python components for immediate transformation.
- Saving the same report after applying an external policy or transformation.

It is not necessary to serialize and deserialize the report merely to consume it from the calling process.

This interface is documented upstream and exercised by tests.

Note that embedding pytest inside an application inherits the ordinary lifecycle and state-management considerations of `pytest.main()` itself; it is not equivalent to isolated subprocess execution.

Documentation: [https://github.com/numirias/pytest-json-report/blob/v1.5.0/README.md](https://github.com/numirias/pytest-json-report/blob/v1.5.0/README.md?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 7.3 Access from other pytest hooks

The README also documents access to the active reporter through:

```
session.config._json_report.report
```

For example, within `pytest_sessionfinish`, another hook can inspect the report after it has been constructed, provided hook execution ordering permits it.

The reporter uses `pytest_sessionfinish` with `tryfirst=True`, but another implementation could still affect ordering.

The `_json_report` attribute is an implementation-specific, private configuration attribute. The explicit `JSONReport` instance interface is more suitable where the caller controls invocation.

### 7.4 Output persistence behavior

`JSONReport.save_report(path)` creates missing parent directories and serializes the report as UTF-8 JSON.

The serializer calls:

```
json.dump(    self.report,    file,    default=str,    indent=indent,)
```

This has two non-obvious properties:

- Values that reach the final report and are not otherwise encodable can be converted to strings using `str`.
- The behavior is not the same as schema validation. A successfully written report is not proof that every field matches an intended consumer contract.

The plugin catches `OSError` during automatic saving and reports the failure through its terminal status output. It does not comprehensively convert every possible serialization exception into a recoverable reporting status.

The result is a convenient persistence mechanism, but it does not supply atomic writes, historical retention, or transaction semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



## 8. Integration boundaries and architectural implications

### 8.1 pytest-metadata compatibility

`pytest-metadata` is a dependency and, historically, supplies the report's `environment` section.

This can include interpreter information, platform information, installed package/plugin versions, CI metadata, and user-supplied session metadata.

However, as noted in the version assessment, `pytest-json-report` 1.5.0 reads:

```
getattr(config, "_metadata", {})
```

Modern `pytest-metadata` stores its data using a `pytest.StashKey` and `config.stash`, rather than the previous `_metadata` attribute.

The 3.0.0 release notes explicitly document that migration.

Sources:

- `pytest-metadata` source: [https://github.com/pytest-dev/pytest-metadata/blob/master/src/pytest_metadata/plugin.py](https://github.com/pytest-dev/pytest-metadata/blob/master/src/pytest_metadata/plugin.py?utm_source=chatgpt.com)
- Change history: [https://github.com/pytest-dev/pytest-metadata/blob/master/CHANGES.rst](https://github.com/pytest-dev/pytest-metadata/blob/master/CHANGES.rst?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1

A compatibility adapter can use `pytest-metadata`'s own hook to bridge the old and new representations:

```
import pytest@pytest.hookimpl(optionalhook=True)def pytest_metadata(metadata, config):    config._metadata = metadata
```

This is an illustrative compatibility workaround, not a supported public API of `pytest-json-report`. It assigns a private attribute because that is what the older plugin reads.

An alternative is to inject desired environment values directly through `pytest_json_modifyreport`.

The second approach avoids restoring an obsolete attribute, but places environment population under the consuming application's explicit control.

The more general lesson is that the environmental metadata path must be verified independently from ordinary test reporting when integrating the package with modern pytest installations.

### 8.2 Interaction with other pytest plugins

`pytest-json-report` largely relies on standard pytest reporting surfaces. That makes it naturally composable with many pytest extensions, but does not automatically expose every extension's internal data.

| Companion                  | Interaction boundary                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------------------- |
| `pytest-xdist`             | Parallel execution; reports are aggregated by the controller                                      |
| `pytest-metadata`          | Session environment data, subject to the compatibility issue above                                |
| `pytest-cov`               | Coverage instrumentation; coverage-specific results are not native `pytest-json-report` fields    |
| `pytest-rerunfailures`     | Retry behavior may affect final outcomes, but full attempt history is not a native schema element |
| `pytest-html`              | Separate HTML reporting; does not derive its richer presentation from this JSON format by default |
| Pytest's `record_property` | Existing user properties are serialized into `user_properties`                                    |
| Custom pytest plugins      | Can participate through the three JSON-specific reporting hooks                                   |

This makes the plugin useful as a common execution-results artifact, but not as a universal serialization mechanism for all pytest plugin state.

For example, coverage metrics might be inserted via a report customization hook, but retrieving those metrics belongs to the coverage-producing integration.

Similarly, test metadata can describe a model evaluation or data-validation scenario, but `pytest-json-report` has no native understanding of such domains.

### 8.3 Comparison with adjacent reporting approaches

| Approach             | Primary distinction                                                                                | When it may be more suitable                                     |
| -------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `pytest-json-report` | A single rich JSON session document with pytest phases, diagnostic fields, and customization hooks | Structured in-process consumption and whole-session analysis     |
| Pytest JUnit XML     | Widely recognized test-report exchange format                                                      | CI platforms that already ingest JUnit-compatible artifacts      |
| `pytest-reportlog`   | JSON Lines event stream written incrementally                                                      | Event processing, partial-run visibility, or streaming ingestion |
| `pytest-json-ctrf`   | Emits the Common Test Report Format                                                                | Cross-framework normalization and CTRF-oriented tooling          |

There is no universal best option because these formats preserve different information and support different operational models.

In particular, `pytest-reportlog` is built around a stream of individual events, whereas `pytest-json-report` accumulates a single final document.

For long-running jobs where partial results must survive unexpected termination, this is a major architectural difference.

Conversely, a complete nested session object can be easier to work with when a consumer wants immediate access to summaries, per-test stages, and diagnostics without first assembling an event log.

Primary references:

- Pytest JUnit XML: [https://docs.pytest.org/en/stable/how-to/output.html](https://docs.pytest.org/en/stable/how-to/output.html?utm_source=chatgpt.com)
- pytest-reportlog: [https://github.com/pytest-dev/pytest-reportlog](https://github.com/pytest-dev/pytest-reportlog?utm_source=chatgpt.com)
- pytest-json-ctrf: [https://pypi.org/project/pytest-json-ctrf/](https://pypi.org/project/pytest-json-ctrf/?utm_source=chatgpt.com)
- CTRF specification: [https://ctrf.io/docs/specification/overview](https://ctrf.io/docs/specification/overview?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2

### 8.4 Schema design and durable storage considerations

The 1.5.0 implementation does not supply a formal versioned JSON Schema or an explicit schema-version field.

Its output structure is documented descriptively through the README and the serializer.

This matters for durable storage and integration because optional fields can disappear for several independent reasons:

- The associated phase never ran.
- No captured data was available.
- A report omission option excluded the field.
- A plugin customization removed or replaced it.
- The underlying pytest report lacked a usable structured representation.

Consequently, downstream consumers should distinguish:

Missing field versus empty value. The absence of `log` is not necessarily equivalent to a present empty array, nor does absence prove that no logging took place.

Failure of observation versus absence of a test. An unreported test may never have executed, may have been deselected, or may have been interrupted before its reports were received.

Stable identity versus stable semantic meaning. `nodeid` identifies a pytest collection item, but it is not a persistent external ID guaranteed across test refactors.

Outcome versus attempt history. A final test outcome does not retain the full causal sequence of retries.

Reported environment versus actual environment. The environment object can be incomplete, especially with the metadata compatibility issue.

For downstream normalization, these distinctions are more consequential than the mechanics of loading JSON.

### 8.5 Performance and resource characteristics

The library's design introduces relatively straightforward overhead mechanisms, with no substantiated quantitative benchmark in the inspected primary sources.

Its principal costs arise from:

- Hook callbacks for collection and execution phases.
- Installation and removal of phase-specific logging handlers.
- Capturing and copying log-record dictionaries.
- Accumulating report data in Python objects.
- Generating formatted diagnostic representations.
- Encoding the final document as JSON.
- Writing the completed artifact to storage.

The impact depends on workload characteristics.

For a suite with many small tests and extensive logging, report collection and serialization can represent a more significant fraction of runtime than for a suite dominated by long-running computations.

For suites producing large tracebacks or substantial stdout/stderr, report size and memory overhead can grow materially.

The `log` omission option suppresses logging-handler installation, whereas most other omission options primarily reduce material retained or serialized. Summary-only mode excludes detailed result structures from the final document, although the implementation still performs some intermediate collection and aggregation.

These are qualitative deductions from the implementation, not claims of measured performance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



### 8.6 Security and data exposure

The report can contain sensitive information by virtue of pytest's own captured data:

- Absolute filesystem paths.
- Assertion messages containing input values.
- Tracebacks and exception text.
- Captured stdout/stderr.
- Logging records and custom log attributes.
- Environment and CI metadata.
- User-defined per-test metadata.

The package does not provide a comprehensive native secret-redaction framework.

A whole-report customization hook can remove or transform fields, but redacting only `traceback` may still leave the same information in `longrepr`, `crash.message`, logging fields, or streams.

For sensitive workloads, redaction must operate across all representations that could contain the relevant data.

## 9. Important limitations and decision boundaries

Several limitations are worth distinguishing from the library's established capabilities.

| Area                   | Verified behavior or limitation                            | Architectural significance                                        |
| ---------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------- |
| Maintenance/versioning | Latest published release is 1.5.0 from 2022                | Compatibility with contemporary pytest/Python needs verification  |
| Modern metadata        | Reads legacy `config._metadata`                            | Current `pytest-metadata` integration can lose environment data   |
| Streaming              | Writes final JSON at session end                           | Does not provide incremental event durability                     |
| Parallel collectors    | Successful collection records generally absent under xdist | Cannot assume complete discovery inventory                        |
| Warning aggregation    | Potential duplicates with xdist                            | Warning counts may not represent unique warning conditions        |
| Test retries           | Aggregates by `nodeid`                                     | Does not naturally retain all retry attempts                      |
| Schema governance      | No native schema-version field                             | External consumers need their own validation/version conventions  |
| Phase serialization    | Can be wholly replaced by a custom hook                    | Extensions can unintentionally discard diagnostics                |
| Metadata validation    | Rejects an entire metadata dictionary when nonserializable | A single invalid value may eliminate otherwise useful annotations |
| Capture completeness   | Dependent on pytest's capture and traceback settings       | Field absence can reflect configuration rather than behavior      |
| Security               | Raw diagnostics and metadata can be included               | Sensitive data requires explicit handling                         |
| Process crashes        | No continuous, durable write stream                        | Abrupt termination can prevent a complete report                  |

The implementation additionally uses several private or historically version-sensitive pytest surfaces, including `session.fspath`, `_report_sections`, and private configuration attributes. These are reasons to verify behavior against the exact current pytest version rather than assuming its broad `pytest>=3.8.0` dependency declaration constitutes a modern compatibility guarantee.

The project's source and tests establish what 1.5.0 was designed to do, but they do not demonstrate that the same combination has been tested against every newer pytest, xdist, or Python release.

## 10. Capability combinations and higher-order uses

The library becomes more interesting when its mechanisms are considered together, rather than as isolated reporting fields.

### 10.1 Structured failure classification

Phase identity, outcome, crash location, traceback frames, and captured logs form a richer diagnostic object than a plain failure string.

A downstream classifier can distinguish setup failures, assertion failures, teardown failures, collection failures, and expected failures before attempting any deeper error interpretation.

This allows straightforward deterministic categorization, with exception text and log content reserved for more nuanced cases.

The limitation is that pytest reports are observations, not causal proofs. The crash location may be a symptom rather than the underlying cause.

### 10.2 Test inventory and execution reconciliation

Collection nodes, deselection flags, executed test IDs, and summary counts can be combined to compare the intended test inventory with the tests that actually ran.

This can reveal a distinction between selection, discovery, execution, and interruption.

The capability is strongest in non-xdist collection, where successful collection records are available. Under xdist or interrupted execution, additional sources may be required for a complete inventory.

### 10.3 Rich evaluation metadata without a separate event protocol

`json_metadata` and `pytest_json_runtest_metadata` allow arbitrary structured annotations to travel with the test's result.

An external system can associate tests with dataset versions, scenario categories, feature flags, or parameter groups while retaining pytest's failure diagnostics.

This can remove the need for a separate custom JSON writer within every test function.

The tradeoff is that annotations must remain JSON-serializable and the report is still emitted only at session completion.

### 10.4 Schema adaptation at the reporting boundary

`pytest_json_runtest_stage` and `pytest_json_modifyreport` allow the standard pytest reporting model to be transformed into an application-specific representation.

These hooks can replace substantial custom postprocessing, especially where the destination requires a modest extension to the default format.

The distinction between stage replacement and whole-report mutation matters: stage replacement changes what data reaches the assembled report, while whole-report mutation operates on the representation after the individual stages have already been serialized.

### 10.5 Report ingestion without intermediate files

The direct `JSONReport` interface allows a Python application to invoke pytest, inspect the completed dictionary, and hand it directly to another component.

This avoids a write/read cycle and allows the caller to control persistence independently.

It remains synchronous, session-scoped integration. It does not establish an independent execution service or continuously queryable results database.

## 11. Primary-source reference map

The following sources provide the most useful routes for deeper investigation. They are listed as direct URLs so they remain usable independently of this overview.

| Area                                       | Primary source                                                                                                                                                                                                |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Package metadata and published releases    | [https://pypi.org/project/pytest-json-report/](https://pypi.org/project/pytest-json-report/?utm_source=chatgpt.com)                                                                                           |
| Official README, CLI, hooks, and format    | [https://github.com/numirias/pytest-json-report/blob/v1.5.0/README.md](https://github.com/numirias/pytest-json-report/blob/v1.5.0/README.md?utm_source=chatgpt.com)                                           |
| Core plugin implementation and lifecycle   | [https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/plugin.py](https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/plugin.py?utm_source=chatgpt.com)       |
| Serialization and report-field definitions | [https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/serialize.py](https://github.com/numirias/pytest-json-report/blob/v1.5.0/pytest_jsonreport/serialize.py?utm_source=chatgpt.com) |
| Behavior tests and edge cases              | [https://github.com/numirias/pytest-json-report/blob/v1.5.0/tests/test_jsonreport.py](https://github.com/numirias/pytest-json-report/blob/v1.5.0/tests/test_jsonreport.py?utm_source=chatgpt.com)             |
| Package dependency declarations            | [https://github.com/numirias/pytest-json-report/blob/v1.5.0/setup.py](https://github.com/numirias/pytest-json-report/blob/v1.5.0/setup.py?utm_source=chatgpt.com)                                             |
| Tagged release history                     | [https://github.com/numirias/pytest-json-report/tags](https://github.com/numirias/pytest-json-report/tags?utm_source=chatgpt.com)                                                                             |
| pytest hook and plugin reference           | [https://docs.pytest.org/en/stable/reference/reference.html](https://docs.pytest.org/en/stable/reference/reference.html?utm_source=chatgpt.com)                                                               |
| Pytest capture behavior                    | [https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html](https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html?utm_source=chatgpt.com)                                             |
| pytest-metadata implementation             | [https://github.com/pytest-dev/pytest-metadata/blob/master/src/pytest_metadata/plugin.py](https://github.com/pytest-dev/pytest-metadata/blob/master/src/pytest_metadata/plugin.py?utm_source=chatgpt.com)     |
| pytest-metadata compatibility changes      | [https://github.com/pytest-dev/pytest-metadata/blob/master/CHANGES.rst](https://github.com/pytest-dev/pytest-metadata/blob/master/CHANGES.rst?utm_source=chatgpt.com)                                         |

## 12. Overall assessment

`pytest-json-report` remains a capable and unusually extensible JSON reporter for pytest. Its greatest value is not the mere production of JSON, but the combination of phase-specific execution records, structured diagnostics, collection information, metadata enrichment, and programmable serialization hooks.

The features most worth understanding beyond basic report generation are:

1. The separation of collection, setup, call, and teardown, which preserves important execution semantics.
2. The three extension hooks, particularly their different merge, replacement, and mutation behavior.
3. The ability to collect arbitrary per-test metadata, including values originating in fixtures and pytest reporting hooks.
4. The native preservation of pytest `record_property` values, an easily overlooked interoperability feature.
5. The in-memory `JSONReport` interface, which allows embedding reporting directly into Python applications.
6. The significant differences in completeness and interpretation under pytest-xdist and retry-oriented plugins.

The principal concern is the age of the published implementation relative to the current pytest ecosystem. The verified `pytest-metadata` compatibility mismatch provides a concrete example of why that matters. A second fundamental limitation is its single-document, end-of-session design: the library offers a rich final representation, not continuous event capture or durable execution history.

Within those boundaries, it provides a substantial amount of reporting machinery that would otherwise require writing multiple pytest hooks, managing execution-phase capture, implementing aggregation, and maintaining custom serializers.