# pytest-xdist — Comprehensive Python Library Overview

Research date: November 6, 2026 | Latest stable release: 3.8.0 (July 1, 2025) | Python ≥3.9

pytest-xdist is a mature, extensible pytest plugin that distributes test execution across multiple Python processes, local interpreters, or remote machines. Its central value is not merely running tests concurrently: it provides a coordinated execution architecture with multiple scheduling strategies, worker lifecycle management, crash recovery, fixture-aware grouping, cross-process test identification, and extension hooks for implementing specialized distribution policies.

Version 3.8.0 is the latest published stable release verified against PyPI and upstream releases. This overview uses that version as its baseline and distinguishes unreleased development-branch functionality where relevant.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Primary project sources:

- Repository: [https://github.com/pytest-dev/pytest-xdist](https://github.com/pytest-dev/pytest-xdist?utm_source=chatgpt.com)
- Documentation: [https://pytest-xdist.readthedocs.io/en/stable/](https://pytest-xdist.readthedocs.io/en/stable/?utm_source=chatgpt.com)
- Version history: [https://pytest-xdist.readthedocs.io/en/stable/changelog.html](https://pytest-xdist.readthedocs.io/en/stable/changelog.html?utm_source=chatgpt.com)
- Version 3.8.0 source: [https://github.com/pytest-dev/pytest-xdist/tree/v3.8.0](https://github.com/pytest-dev/pytest-xdist/tree/v3.8.0?utm_source=chatgpt.com)

## 1. Architectural orientation

pytest-xdist is best understood as a distributed test scheduler and execution coordinator built on pytest and execnet, rather than simply a process-pool wrapper.

Its architecture separates test discovery, execution, scheduling, and reporting across independently running pytest processes.

Controller process

Worker management · scheduling · result aggregation · pytest reporting

execnet gateways and communication channels

Worker gw0

Own pytest session

Collect tests

Execute assignments

Report results

Worker gw1

Own pytest session

Collect tests

Execute assignments

Report results

Worker gw2

Own pytest session

Collect tests

Execute assignments

Report results

Conceptual example with three workers; workers can execute locally or through remote gateways.

### 1.1 Controller–worker execution model

The controller launches worker processes and coordinates them through execnet, the underlying interprocess and remote-execution library.

Each worker runs a genuine pytest session, including its own plugin initialization, fixture management, and test collection. The controller does not collect pytest items and serialize them to workers.

Instead, execution proceeds through several phases:

1. Workers independently collect the selected test suite.
2. Each worker transmits its ordered test node IDs to the controller.
3. The controller verifies that workers collected identical tests in identical order.
4. Test IDs are translated into compact integer indices for scheduling.
5. The scheduler assigns work to workers according to the chosen distribution policy.
6. Workers execute tests through pytest's normal runtest protocol and return reports.
7. The controller forwards appropriate reporting events into pytest's hook system.

The collection design avoids serializing complicated pytest `Item` objects, which can reference fixture managers, Python callables, configuration objects, and other process-local state.

Architectural consequence: pytest-xdist distributes execution, not Python object state. Workers are isolated pytest runtimes, and resource coordination across them must be explicit.

Source: [https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html](https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+1



### 1.2 Major capability families

| Capability                  | What pytest-xdist provides                                                       |
| --------------------------- | -------------------------------------------------------------------------------- |
| Parallel execution          | Independent pytest worker processes with configurable concurrency                |
| Dynamic scheduling          | Load balancing, work stealing, and bounded scheduling chunks                     |
| Affinity scheduling         | Module-, class-, file-, and marker-based grouping                                |
| Cross-environment execution | Multiple Python interpreters and remote execnet gateways                         |
| Worker coordination         | Shared run identifiers, worker metadata, environment variables, and custom hooks |
| Reliability                 | Worker crash reporting, restart controls, and collection consistency checks      |
| Extensibility               | Custom schedulers and hooks into worker creation, collection, and execution      |
| Development workflow        | Loop-on-failure mode, retained for compatibility but deprecated                  |
| Pytest interoperability     | Standard test reports and integration with the broader pytest plugin ecosystem   |

The most consequential design distinction is between how tests are assigned and how test resources are managed. Scheduling can improve reuse of fixtures and isolate execution, but it does not automatically make databases, files, services, or process-global state safe for parallel use.

## 2. Distribution strategies and scheduling

Scheduling is pytest-xdist's most important functional area. Different modes offer substantially different guarantees concerning test placement, locality, ordering, and workload balancing.

### 2.1 Distribution mode comparison

| Mode        | Scheduling behavior                                                   | Primary advantage                                        | Important limitation                               |
| ----------- | --------------------------------------------------------------------- | -------------------------------------------------------- | -------------------------------------------------- |
| `load`      | Assign individual tests dynamically to available workers              | General-purpose load balancing                           | No test affinity or execution-order guarantee      |
| `loadscope` | Assign entire module or class scopes to workers                       | Fixture reuse and scope locality                         | Large scopes can create scheduling imbalance       |
| `loadfile`  | Assign entire files to workers                                        | File-level isolation and locality                        | Large files become indivisible scheduling units    |
| `loadgroup` | Assign tests sharing an `xdist_group` marker to one worker            | Explicit resource or test affinity                       | Group size and selection require deliberate design |
| `worksteal` | Distribute tests initially, then steal queued tests from busy workers | Balancing uneven workloads while retaining some locality | No built-in scope/group affinity in 3.8.0          |
| `each`      | Execute the complete selected suite on every worker                   | Multi-interpreter and multi-platform testing             | Duplicates execution across environments           |
| `no`        | Disable distributed execution                                         | Conventional pytest behavior                             | No xdist execution parallelism                     |

Source: [https://pytest-xdist.readthedocs.io/en/stable/distribution.html](https://pytest-xdist.readthedocs.io/en/stable/distribution.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+2



### 2.2 Dynamic load scheduling: `--dist=load`

The default parallel scheduler assigns test items to workers without permanently partitioning the suite.

Its central responsibilities include maintaining a global pending queue, tracking worker-specific pending assignments, and replenishing worker queues as tests complete.

This makes `load` valuable when tests are substantially independent and have unequal execution durations.

An especially important option is `--maxschedchunk=N`, which limits the number of tests dispatched in a scheduling step.

Smaller chunks generally expose more work to dynamic load balancing. Larger consecutive chunks can improve fixture reuse by allowing related tests to execute together, but may leave other workers idle when a long-running chunk becomes a bottleneck.

For example:

```
pytest -n 8 --dist=load --maxschedchunk=1
```

A subtlety: setting `--maxschedchunk=1` does not mean workers always have exactly one outstanding item. The implementation initially assigns at least two tests per worker because pytest's runtest protocol needs to know the next test item.

The scheduling parameter is therefore a granularity and locality control, not a strict one-item-in-flight contract.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/load.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/load.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



### 2.3 Scope-aware scheduling: `--dist=loadscope`

This scheduler combines load balancing with fixture-oriented affinity.

Its grouping rules are:

| Test category               | Scheduling unit                |
| --------------------------- | ------------------------------ |
| Module-level test functions | Their containing Python module |
| Test methods within classes | Their containing test class    |

All tests in a particular scheduling unit execute on the same worker.

This can reduce repeated initialization of expensive module-scoped or class-scoped fixtures and improve reuse of process-local resources.

It is not a general fixture-dependency scheduler: it groups using test node identity rather than constructing an arbitrary dependency graph of the fixtures each test uses.

Large-scope-first scheduling. Since version 3.5.0, `loadscope` prioritizes larger scopes based on their number of tests. The objective is to reduce the risk of leaving a large group until the end of a run.

Ordering controls introduced in 3.8.0. Two flags modify this behavior:

```
pytest -n 8 --dist=loadscope --loadscope-reorder
pytest -n 8 --dist=loadscope --no-loadscope-reorder
```

The first is the default and prioritizes scheduling efficiency. The second retains more of the relative input ordering between scopes assigned to each worker.

This is useful when collection-order plugins are involved. However, preserving a relative order within workers is not equivalent to guaranteeing a single global test execution order across concurrent processes.

An additional architectural tradeoff is that the scheduler optimizes scope placement using the number of tests, not an explicit historical execution-time model. A scope containing two expensive integration tests could take substantially longer than one containing many trivial unit tests.

Sources:

[https://pytest-xdist.readthedocs.io/en/stable/changelog.html](https://pytest-xdist.readthedocs.io/en/stable/changelog.html?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+1



### 2.4 File-level scheduling: `--dist=loadfile`

`loadfile` treats the entire test file as an indivisible scheduling unit.

Unlike `loadscope`, which can distribute different classes from the same file to different workers, `loadfile` keeps every test in a file together.

This can be useful when a test module owns a substantial amount of setup state, uses module-scoped resources, or has assumptions about process-local state that require all its tests to share a worker.

The distinction is not merely organizational. The choice of module- or file-level scheduling affects how broadly setup costs can be amortized and how finely work can be redistributed.

Neither `loadfile` nor `loadscope` guarantees that two related files share a worker.

### 2.5 Explicit affinity: `--dist=loadgroup`

`loadgroup` provides the most flexible built-in mechanism for controlling which tests execute in the same process.

Tests are assigned to scheduling groups using the `xdist_group` marker.

```
import pytest@pytest.mark.xdist_group("database-primary")def test_insert():    ...@pytest.mark.xdist_group("database-primary")def test_update():    ...
```

When invoked with:

```
pytest -n 8 --dist=loadgroup
```

both tests execute on the same worker, even if they reside in different classes or modules.

This facility can support several architectural patterns, including resource affinity, fixture locality, colocating related integration tests, and avoiding concurrent execution of mutually incompatible tests assigned to the same group.

An important limitation is that group affinity does not provide resource locking. It only ensures that tests with the same effective group are assigned to one worker. Other tests using the same external service or resource can still execute concurrently unless they participate in the relevant isolation scheme.

#### Composable grouping through multiple markers

Version 3.7.0 introduced particularly useful behavior: multiple `xdist_group` marks are combined to form a composite group name, regardless of marker order.

For example, a parametrized fixture can attach environment-specific group marks:

```
@pytest.fixture(    params=[        pytest.param("postgres", marks=pytest.mark.xdist_group("postgres")),        pytest.param("sqlite", marks=pytest.mark.xdist_group("sqlite")),    ])def backend(request):    return request.param@pytest.mark.xdist_group("storage")def test_write(backend):    ...
```

The resulting test variants have separate composite group identities equivalent to `postgres_storage` and `sqlite_storage`.

This permits group membership to be assembled from multiple parts of the test definition, including fixture parameters, module-level marks, and test-level marks.

It is more expressive than assigning one monolithic group marker manually to every test.

A critical distinction is that composite grouping is based on the complete effective combination of marks. Tests tagged with different combinations are not automatically grouped merely because they share one constituent mark.

For example, `storage_postgres` and `storage_sqlite` are distinct groups, despite both containing `storage`.

Tests without a group mark are scheduled independently, similarly to individual-test load balancing.

Sources:

[https://pytest-xdist.readthedocs.io/en/stable/distribution.html](https://pytest-xdist.readthedocs.io/en/stable/distribution.html?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadgroup.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadgroup.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+2



### 2.6 Work-stealing scheduling: `--dist=worksteal`

Work stealing is an alternative to continuously assigning small pieces of work from a central pool.

The process begins by distributing test indices approximately evenly among workers. When a worker approaches the end of its assignment, the scheduler tries to reclaim tests that have not yet begun execution from another worker's queue and reassign them to the underutilized worker.

This design attempts to balance two objectives:

- Retain locality by giving workers contiguous or preassigned segments of the test collection.
- Recover parallel efficiency by redistributing outstanding work when worker execution times diverge.

The scheduler considers workers with fewer than two queued tests candidates for additional work. It coordinates stealing through explicit unscheduling requests, rather than simply assigning the same outstanding tests to another worker.

Atomic stealing in 3.7.0. The internal steal operation was changed so that either all requested tests are unscheduled or none are. This reduces the risk of partially accepting a reassignment request and leaving the scheduler with inconsistent ownership of work.

The changelog describes this as a prerequisite for future work involving grouped or scoped tests. It should not be interpreted as evidence that `worksteal` already implements `loadgroup` or `loadscope` affinity in 3.8.0.

Work stealing may perform well when test execution times differ considerably and contiguous initial assignment provides useful fixture reuse. Its results still depend on test order, execution duration, and the amount of queued work that can safely be moved.

Sources:

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/worksteal.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/worksteal.py?utm_source=chatgpt.com)

[https://pytest-xdist.readthedocs.io/en/stable/changelog.html](https://pytest-xdist.readthedocs.io/en/stable/changelog.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+2



### 2.7 Full-suite replication: `--dist=each`

`each` differs fundamentally from the other modes.

Rather than distributing unique portions of one test suite, it causes every execution environment to run the full selected suite.

```
pytest --dist=each \
  --tx=popen//python=python3.11 \
  --tx=popen//python=python3.12
```

This can test the same application against multiple interpreters or environments in a single coordinated pytest run.

An important distinction is that the number of executions scales with the number of workers. Given \\(T\\) collected tests and \\(W\\) workers, `each` normally produces \\(T \times W\\) test executions rather than dividing \\(T\\) tests across workers.

Thus, it is useful for cross-environment validation, not as a substitute for the normal load-balancing modes.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/each.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/each.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



## 3. Worker processes, fixture lifetimes, and shared resources

### 3.1 Worker isolation

Each xdist worker operates as an independent Python process with its own interpreter state and pytest runtime.

This provides several useful properties:

- Tests can execute concurrently without sharing one Python interpreter's Global Interpreter Lock.
- Process-local caches, module globals, and in-memory fixtures are isolated between workers.
- A worker's abrupt termination generally does not terminate the controller or other worker processes.
- Workers can be assigned different Python interpreters or remote execution environments.

However, process isolation does not imply infrastructure isolation. Workers can still share databases, network services, filesystem locations, ports, external APIs, and operating-system resources.

### 3.2 Fixture scope is local to each worker

One of the most significant behavioral distinctions from sequential pytest concerns fixture scopes.

A session-scoped fixture is normally instantiated once per pytest session, subject to pytest's regular fixture semantics. With xdist, each worker has a separate pytest session.

Consequently, a session-scoped fixture can be initialized once in each worker process, not once globally across the distributed run.

For example, with eight workers, a fixture that provisions a test database could provision eight databases if requested by tests running in all eight workers.

The resulting behavior depends on scheduling and fixture demand. It is not necessarily exactly eight initializations.

| Fixture scope | Implication under xdist                                          |
| ------------- | ---------------------------------------------------------------- |
| Function      | Instantiated according to normal pytest rules within each worker |
| Class         | Reused within the class scope of a worker                        |
| Module        | Reused within the module scope of a worker                       |
| Package       | Reused within the relevant package scope of a worker             |
| Session       | Reused within one worker's pytest session, not across workers    |

Affinity-aware scheduling can reduce repeated fixture initialization by colocating tests, but it does not implement global singleton fixtures.

Source: [https://pytest-xdist.readthedocs.io/en/stable/how-to.html](https://pytest-xdist.readthedocs.io/en/stable/how-to.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation



### 3.3 Once-per-run resource initialization

pytest-xdist documents a pattern for initializing shared resources exactly once using an external interprocess lock.

The pattern combines a shared temporary directory, a lock protecting resource initialization, and a persistent artifact indicating whether initialization has already occurred.

A condensed illustration:

```
import jsonimport pytestfrom filelock import FileLock@pytest.fixture(scope="session")def shared_data(tmp_path_factory, worker_id):    if worker_id == "master":        return build_data()    root = tmp_path_factory.getbasetemp().parent    data_path = root / "shared.json"    lock_path = root / "shared.json.lock"    with FileLock(str(lock_path)):        if not data_path.exists():            value = build_data()            data_path.write_text(json.dumps(value))        return json.loads(data_path.read_text())
```

This sketch assumes a shared filesystem and suitable initialization/error-handling semantics.

The important idea is that the lock coordinates independently executing pytest sessions, whereas the fixture cache operates only inside one session.

The locking pattern can be generalized to other shared resources, but remote machines without a shared filesystem require a coordination mechanism accessible to all participating workers.

The `filelock` library is not the implementation of distributed locking inside pytest-xdist. It is a companion dependency used by the documented example.

Source: [https://pytest-xdist.readthedocs.io/en/stable/how-to.html#making-session-scoped-fixtures-execute-only-once](https://pytest-xdist.readthedocs.io/en/stable/how-to.html?utm_source=chatgpt.com#making-session-scoped-fixtures-execute-only-once)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation



### 3.4 Worker identity and run identity

pytest-xdist provides two different classes of identifiers.

| Facility                    | Semantics                                                | Typical use                            |
| --------------------------- | -------------------------------------------------------- | -------------------------------------- |
| `worker_id` fixture         | Worker identity, such as `gw0`                           | Per-worker resources and filenames     |
| `testrun_uid` fixture       | Identifier shared by workers in the same distributed run | Per-run resources and namespaces       |
| `PYTEST_XDIST_WORKER`       | Worker ID exposed as an environment variable             | Code outside pytest fixture functions  |
| `PYTEST_XDIST_WORKER_COUNT` | Number of configured workers                             | Resource partitioning                  |
| `PYTEST_XDIST_TESTRUNUID`   | Shared run identifier                                    | Subprocesses and external integrations |
| `--testrunuid=VALUE`        | Explicitly select the distributed run identifier         | Coordinating externally named runs     |

The `worker_id` fixture returns `"master"` when distributed execution is disabled. This is a legacy naming convention, not evidence that a worker named `master` exists during a normal distributed run.

These identifiers enable a useful separation:

Run-level isolation gives an entire test execution a unique namespace, while worker-level isolation subdivides that namespace among concurrent processes.

For instance:

```
@pytest.fixture(scope="session")def database_name(testrun_uid, worker_id):    return f"test_{testrun_uid}_{worker_id}"
```

The same approach can be used for message queues, temporary object-storage prefixes, log files, and other independently provisioned resources.

Worker IDs identify an execution process within xdist's worker-management scheme; they are not stable logical resource identities across independent test runs or worker replacements.

Sources:

[https://pytest-xdist.readthedocs.io/en/stable/how-to.html#identifying-the-worker-process-during-a-test](https://pytest-xdist.readthedocs.io/en/stable/how-to.html?utm_source=chatgpt.com#identifying-the-worker-process-during-a-test)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+2



### 3.5 Temporary directories and worker-local files

For local `popen` workers, xdist creates worker-specific base temporary directories within a common temporary root.

This gives each worker an independent location for pytest temporary artifacts, while allowing the parent directory to serve as a coordination location.

The distinction supports two complementary designs: independent worker outputs, which avoid filename collisions, and intentionally shared artifacts, which require interprocess synchronization.

The same concept applies to logs. The official documentation shows how `PYTEST_XDIST_WORKER` can be used to create separate files such as `tests_gw0.log` and `tests_gw1.log`.

This matters because using a single append-only log file across several processes can produce interleaved records or introduce locking overhead.

Sources:

[https://pytest-xdist.readthedocs.io/en/stable/how-to.html#creating-one-log-file-for-each-worker](https://pytest-xdist.readthedocs.io/en/stable/how-to.html?utm_source=chatgpt.com#creating-one-log-file-for-each-worker)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+1



## 4. Process management and concurrency controls

### 4.1 Selecting worker counts

pytest-xdist supports explicit worker counts and automatic CPU-based selection.

```
pytest -n 8
pytest -n auto
pytest -n logical
pytest -n auto --maxprocesses=8
pytest -n 0
```

In version 3.8.0, automatic worker-count selection uses `psutil`, when available, to distinguish physical and logical CPU counts. Without `psutil`, it falls back to platform-dependent mechanisms, including CPU affinity and operating-system CPU-count functions.

The `psutil` extra is therefore useful when physical-versus-logical core detection matters.

Automatic worker counts are not workload-aware concurrency optimization. The number of cores is only a starting point. An appropriate worker count depends on CPU utilization, process memory, fixture cost, I/O contention, external service capacity, and test duration distribution.

### 4.2 Programmatic worker-count selection

The `pytest_xdist_auto_num_workers(config)` hook allows a plugin or test configuration to replace automatic CPU-based worker selection.

```
def pytest_xdist_auto_num_workers(config):    if config.option.numprocesses == "logical":        return 12    return 6
```

This can incorporate resource information that raw CPU counts do not capture, such as the maximum number of parallel integration environments a test infrastructure can support.

For 3.8.0, the `PYTEST_XDIST_AUTO_NUM_WORKERS` environment variable is a simpler external override.

An explicit integer supplied through `-n` bypasses the normal `auto`/`logical` calculation, while `--maxprocesses` caps automatically selected worker counts.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/plugin.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/plugin.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 4.3 Main-thread test execution

Since the 3.6 series, xdist uses execnet's `main_thread_only` execution model to ensure the worker's pytest execution runs on the main thread.

This addressed important compatibility issues with frameworks that expect main-thread execution, particularly event-loop frameworks and GUI toolkits.

Version 3.6.1 repaired a related compatibility regression involving pytest-cov and execnet remote information retrieval.

The guarantee concerns which thread runs pytest within a worker process. It does not mean tests within that worker are automatically parallelized using threads, nor does it eliminate application-created threads or asynchronous tasks.

Sources:

[https://pytest-xdist.readthedocs.io/en/stable/changelog.html](https://pytest-xdist.readthedocs.io/en/stable/changelog.html?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+1



## 5. Cross-interpreter and remote execution

pytest-xdist can execute tests in environments other than the controller's own Python interpreter.

The mechanism is based on execnet gateways, which provide communication channels and remote code execution.

### 5.1 Local interpreter selection

The `--tx` option specifies an execution environment using execnet's XSpec syntax.

For example:

```
pytest -d --tx=popen//python=python3.11
```

This runs tests in a subprocess using the specified Python interpreter.

Multiple workers can use the same interpreter:

```
pytest -d --tx=4*popen//python=python3.11
```

The numeric prefix expands one execution specification into multiple workers.

The principal distinction between `-n` and `--tx` is that `-n` provides a convenient worker-count abstraction, whereas `--tx` exposes lower-level control over execution environments.

Source: [https://pytest-xdist.readthedocs.io/en/stable/subprocess.html](https://pytest-xdist.readthedocs.io/en/stable/subprocess.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation



### 5.2 Remote SSH and socket-based execution

execnet supports remote gateways, including SSH and socket-server connections. pytest-xdist uses these gateways to start its worker runtime and coordinate test execution.

Examples of the supported execution-specification forms include:

```
pytest -d --tx=ssh=testhost//chdir=/workspace/tests
```

and:

```
pytest -d --tx=socket=192.168.1.102:8888
```

The socket form requires an appropriately configured execnet-compatible remote socket server.

These capabilities enable distribution onto dedicated test hosts, execution in different operating-system environments, and use of specialized external resources.

The important operational boundary is that pytest-xdist does not provide a complete environment-management or deployment system. Compatible Python runtimes, application dependencies, filesystem layouts, and access to required test services must still be arranged.

The tagged worker bootstrap source also distinguishes the pytest-xdist controller package from the code sent to remote workers: the remote bootstrap module is transferred through execnet, so the complete xdist plugin need not necessarily be installed separately in the remote environment. Pytest and the test's runtime dependencies remain necessary.

Sources:

[https://pytest-xdist.readthedocs.io/en/stable/remote.html](https://pytest-xdist.readthedocs.io/en/stable/remote.html?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+1



### 5.3 Proxy gateways introduced in 3.7.0

The `--px` option creates proxy gateways that other test-execution gateways can use through execnet's `via` mechanism.

The official example is:

```
pytest -d \
  --px=id=proxy1//socket=192.168.1.102:8888 \
  --tx=5*popen//via=proxy1
```

This creates one proxy gateway and five worker processes on the remote machine.

The proxy is not itself counted as a test worker.

This feature provides a means of multiplexing multiple worker connections through a remote gateway, rather than requiring a separate direct remote connection for each execution environment.

Source: [https://pytest-xdist.readthedocs.io/en/stable/remote.html#using-proxies-to-run-multiple-workers-on-remote-machines](https://pytest-xdist.readthedocs.io/en/stable/remote.html?utm_source=chatgpt.com#using-proxies-to-run-multiple-workers-on-remote-machines)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+1



### 5.4 Remote source synchronization is deprecated

Historically, pytest-xdist could synchronize test code and supporting files to remote machines using `--rsyncdir`, `--rsyncignore`, and corresponding pytest configuration settings.

This functionality remains available in 3.8.0 but has been deprecated since version 3.0, with removal planned for version 4.0.

The maintainers specifically identify difficulties reproducing the development environment correctly using this synchronization mechanism.

The deprecation applies to the rsync-based synchronization feature, not to SSH or socket-based execnet gateways themselves. The project documentation explicitly distinguishes those capabilities.

As an architectural matter, remote execution and remote environment provisioning are better regarded as separate responsibilities.

Source: [https://pytest-xdist.readthedocs.io/en/stable/remote.html](https://pytest-xdist.readthedocs.io/en/stable/remote.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation



## 6. Extension architecture and plugin hooks

pytest-xdist exposes dedicated pytest hooks for customizing worker selection, provisioning, scheduling, lifecycle management, and crash handling.

These are among its most easily overlooked capabilities because they allow developers to change the behavior of the distributed test system without replacing pytest itself.

### 6.1 Extension hook reference

| Hook                                                   | Purpose                                                                               |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| `pytest_xdist_auto_num_workers`                        | Replace automatic worker-count selection                                              |
| `pytest_xdist_make_scheduler`                          | Supply a custom scheduling implementation                                             |
| `pytest_xdist_setupnodes`                              | Observe or customize setup before remote nodes are created                            |
| `pytest_xdist_newgateway`                              | React to creation of an execnet gateway                                               |
| `pytest_configure_node`                                | Configure a worker controller before worker initialization                            |
| `pytest_testnodeready`                                 | Handle worker readiness                                                               |
| `pytest_testnodedown`                                  | Handle worker termination or loss                                                     |
| `pytest_xdist_node_collection_finished`                | Inspect collected test IDs from an individual worker                                  |
| `pytest_handlecrashitem`                               | Intercept reporting and possible rescheduling of a test interrupted by a worker crash |
| `pytest_xdist_getremotemodule`                         | Override the module used to bootstrap a remote worker                                 |
| `pytest_xdist_rsyncstart` / `pytest_xdist_rsyncfinish` | Legacy synchronization lifecycle hooks; deprecated                                    |

All these hooks are present in the 3.8.0 tagged hook specifications.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/newhooks.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/newhooks.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 6.2 Custom scheduler implementations

The `pytest_xdist_make_scheduler` hook is particularly significant.

It allows a pytest plugin to provide a scheduler instead of one of the built-in implementations.

The scheduler interface is represented by the `xdist.scheduler.protocol.Scheduling` protocol.

Its capabilities cover worker membership, collection submission, test completion, rescheduling, and tracking outstanding work.

| Protocol member                  | Responsibility                                  |
| -------------------------------- | ----------------------------------------------- |
| `nodes`                          | Expose active worker controllers                |
| `collection_is_completed`        | Indicate whether initial collection is complete |
| `tests_finished`                 | Indicate whether execution has finished         |
| `has_pending`                    | Indicate outstanding test work                  |
| `add_node`                       | Register a worker                               |
| `add_node_collection`            | Record a worker's collected test IDs            |
| `schedule`                       | Assign available work                           |
| `mark_test_complete`             | Account for a completed test and its duration   |
| `mark_test_pending`              | Return a test to the scheduling queue           |
| `remove_pending_tests_from_node` | Handle tests withdrawn from a worker            |
| `remove_node`                    | Remove a worker and account for unfinished work |

This interface opens the possibility of implementing scheduling policies that are not available as standard distribution modes.

Examples include duration-aware placement using historical timings, scheduling according to worker resource characteristics, specialized resource-affinity policies, and workload assignment driven by test metadata.

Those policies are possibilities enabled by the extension interface, not capabilities automatically provided by the default schedulers.

A custom scheduler must still respect xdist's worker/collection protocol, account for interrupted workers, and avoid duplicate assignments.

The protocol lives under xdist's scheduler implementation modules rather than a separately versioned external scheduling API. Its stability should therefore be evaluated against the targeted xdist version.

Sources:

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/protocol.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/protocol.py?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



### 6.3 Passing configuration from controller to workers

The controller can pass custom metadata to a worker using the worker's `workerinput` dictionary.

For example:

```
def pytest_configure_node(node):    node.workerinput["environment_name"] = "integration"
```

Worker-side pytest hooks and fixtures can subsequently access this information through `config.workerinput`.

The dictionary also contains xdist-provided fields such as `workerid`, `workercount`, `testrunuid`, and `mainargv`.

A worker receives these values during startup over its execnet channel. Consequently, values added to `workerinput` must be compatible with transport across that channel; arbitrary process-local Python objects are not shared transparently.

This mechanism can communicate worker-specific configuration without requiring separate command-line arguments for every worker.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

github.com



### 6.4 Controller-versus-worker detection

The `xdist` module exposes helper functions that let plugins distinguish their execution context:

| Function                         | Behavior                                     |
| -------------------------------- | -------------------------------------------- |
| `xdist.is_xdist_worker(...)`     | True inside an xdist worker                  |
| `xdist.is_xdist_controller(...)` | True in the active controller                |
| `xdist.get_xdist_worker_id(...)` | Return current worker identity or `"master"` |
| `xdist.is_xdist_master(...)`     | Older alias for controller detection         |

These helpers are valuable because ordinary pytest hooks can execute in different process contexts under xdist.

For example, creating a resource in `pytest_sessionstart` can have very different implications depending on whether that hook executes inside a worker or the controller.

Separating controller-only coordination from worker-local operations prevents accidental multiplication of global initialization logic.

Source: [https://pytest-xdist.readthedocs.io/en/stable/how-to.html](https://pytest-xdist.readthedocs.io/en/stable/how-to.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation



### 6.5 Custom crash-item handling

`pytest_handlecrashitem` allows a plugin to intercept a test whose worker died while it was executing.

The hook receives the crashing test's node ID, a generated test report, and the active scheduler.

A plugin can modify the report and request rescheduling with:

```
sched.mark_test_pending(crashitem)
```

This provides a specific extension point for recovery policies, including integration with retry mechanisms.

However, a crashing test may already have performed external side effects before its process terminated. Rescheduling cannot guarantee exactly-once execution of those effects.

A retry policy must distinguish safe re-execution from operations that require cleanup, idempotency, or other external coordination.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/newhooks.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/newhooks.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com+1



## 7. Failure handling, recovery, and execution reliability

### 7.1 Worker crash recovery

pytest-xdist can detect an unexpectedly terminated worker, report the test that was executing, and start a replacement worker.

This is particularly useful when testing native extensions or other code capable of terminating the Python process through segmentation faults, aborts, or similar failures.

A typical recovery sequence is:

1. A worker terminates unexpectedly.
2. The controller detects the lost execnet connection.
3. The scheduler identifies the test believed to be executing.
4. The controller generates a failure report for that test.
5. Unfinished pending work is returned to scheduling as appropriate.
6. If restarting is permitted, a replacement worker is created using the failed worker's execution specification.

This differs from conventional pytest, where an unrecoverable process crash can terminate the entire test run.

The recovery facility is not complete crash containment. An unexpected worker termination can leave external resources, subprocesses, or shared state in an uncertain condition.

Source: [https://pytest-xdist.readthedocs.io/en/stable/crash.html](https://pytest-xdist.readthedocs.io/en/stable/crash.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+1



### 7.2 Restart limits

The `--max-worker-restart` option controls how many replacement workers may be created after crashes.

```
pytest -n 8 --max-worker-restart=2
```

Setting the value to zero disables worker restarting.

The version 3.8.0 implementation computes a default restart limit of four times the configured worker count when `numprocesses` is set. The same helper returns no limit when neither an explicit restart setting nor `numprocesses` supplies one, which can matter for `--tx`-only configurations.

Therefore, an explicit restart limit provides a more predictable failure policy, especially for custom execution environments.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 7.3 Restarting workers versus retrying failed tests

Worker restarts and test retries are distinct capabilities.

| Mechanism                        | Behavior                                                                                       |
| -------------------------------- | ---------------------------------------------------------------------------------------------- |
| Worker restart                   | Replaces an unexpectedly terminated execution process                                          |
| Crash-item rescheduling hook     | Allows extensions to reconsider a test interrupted by a crash                                  |
| Ordinary assertion-failure retry | Requires an additional mechanism, such as a companion pytest plugin                            |
| `--looponfail`                   | Re-executes failed tests after source changes, rather than providing automatic failure retries |

The companion pytest-rerunfailures integrates with xdist and can rerun ordinary failures. Its documentation also describes recovery from hard crashes using xdist, subject to connectivity assumptions between workers and the controller.

This is a good example of a meaningful integration boundary: xdist manages distributed execution and worker replacement; pytest-rerunfailures supplies retry policies and associated reporting semantics.

Source: [https://github.com/pytest-dev/pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.4 Early termination and failure thresholds

pytest-xdist integrates with pytest's failure-count mechanisms, including `-x` and `--maxfail`.

The controller tracks reported failures and coordinates termination of the distributed session once stopping conditions are met.

However, concurrent execution introduces an unavoidable distinction between deciding to stop and having all workers finish or terminate.

Tests already executing may produce additional reports during shutdown. Thus, a maximum-failure threshold should not be interpreted as a guarantee that no other test will finish after the threshold is reached.

The 3.4 and 3.6 release series included fixes concerning preservation of in-progress reports and correct propagation of stopping conditions.

Source: [https://pytest-xdist.readthedocs.io/en/stable/changelog.html](https://pytest-xdist.readthedocs.io/en/stable/changelog.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+1



## 8. Reporting, observability, and ecosystem integration

### 8.1 Centralized pytest reporting

Workers perform test execution, but the controller forwards their results through pytest's normal reporting infrastructure.

The implementation transmits serialized test reports along with worker-specific metadata, including worker identifiers and test-run identifiers.

The controller then invokes relevant pytest reporting hooks.

This makes it possible for compatible plugins to construct aggregate test results without managing individual worker processes themselves.

For example, pytest's JUnit XML reporting can operate through the controller's report-processing path.

The distinction matters when building custom test instrumentation: an ordinary pytest reporting hook executed by the controller may receive reports generated elsewhere, not test `Item` objects local to the controller.

Sources:

[https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html](https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+2



### 8.2 Integration with pytest-cov

pytest-cov provides coverage collection and aggregation for distributed pytest execution.

For example:

```
pytest -n 8 --cov=mypackage --cov-report=term-missing
```

The separation of responsibilities is important:

| Component    | Responsibility                                            |
| ------------ | --------------------------------------------------------- |
| pytest-xdist | Worker creation, execution scheduling, and test reporting |
| pytest-cov   | Coverage collection, management, and aggregation          |
| coverage.py  | Underlying coverage measurement and data model            |

The pytest-cov documentation explicitly supports xdist's distributed execution modes, including execution across multiple hosts and interpreters.

It can combine results from workers running distinct subsets of the test suite and from environments running the entire suite using `each`.

pytest-cov also offers per-test coverage contexts through `--cov-context=test`, which can help associate coverage data with individual test cases.

Source: [https://pytest-cov.readthedocs.io/en/stable/xdist.html](https://pytest-cov.readthedocs.io/en/stable/xdist.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-cov.readthedocs.io\&sz=32)

pytest-cov 7.1.0 documentation+1



### 8.3 Observing worker execution

pytest-xdist can use the optional `setproctitle` package to update worker process titles.

Worker titles indicate whether a process is running a test or idle, making it easier to inspect a distributed run with operating-system process-monitoring tools.

The format is intended for human observation rather than stable machine parsing.

Additional observability is available through worker metadata attached to reports, separate worker log files, and the node lifecycle hooks described earlier.

These mechanisms provide enough information to build worker-aware reporting and instrumentation without introducing an independent process-management layer.

Source: [https://pytest-xdist.readthedocs.io/en/stable/how-to.html#identifying-workers-from-the-system-environment](https://pytest-xdist.readthedocs.io/en/stable/how-to.html?utm_source=chatgpt.com#identifying-workers-from-the-system-environment)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation



## 9. Important semantic limitations

### 9.1 Deterministic test collection

For the load-balancing schedulers, workers must collect the same tests in the same order.

This is fundamental to xdist's integer-index scheduling protocol: a test index can safely identify a test across workers only when their collected sequences agree.

Collection mismatches may arise from nondeterministic parametrization, environment-dependent discovery, unstable generated test IDs, or collection hooks that produce worker-specific results.

For example:

```
@pytest.mark.parametrize("value", {"alpha", "beta"})def test_value(value):    ...
```

An unordered set can produce inconsistent collection ordering.

The robust form is:

```
@pytest.mark.parametrize("value", sorted({"alpha", "beta"}))def test_value(value):    ...
```

A relevant implementation nuance is that `EachScheduling` maintains per-worker collections and does not perform the same initial cross-worker equality check as the load-balancing schedulers. This makes sense because `each` executes complete collections within separate environments rather than identifying a shared pool of unique test indices to distribute.

Thus, the identical-collection requirement is fundamental to the shared-index load-balancing architecture, not a universal constraint applied in exactly the same way by every scheduler.

Sources:

[https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html](https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/each.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/each.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+1



### 9.2 Standard output and interactive debugging

pytest-xdist does not support the usual `-s` / `--capture=no` behavior for displaying worker stdout and stderr directly in the terminal.

This is a limitation of the execnet communication architecture used by the plugin.

Standard pytest capture and reporting can still provide captured output associated with test results, but direct streaming of worker output is not equivalent to sequential execution.

Interactive PDB debugging is also incompatible with distributed execution. pytest-xdist disables `--pdb` when distributing tests.

The official documentation identifies remote debugging tools as a possible workaround when a failure occurs only under concurrency.

These limitations are consequential for suites that expect direct terminal interaction, use standard input during tests, or depend on the attached terminal's properties.

Source: [https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html](https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation



### 9.3 No global test execution ordering

The `load`, `worksteal`, and affinity-based schedulers do not provide a general cross-worker happens-before guarantee between arbitrary tests.

Even when scheduling groups preserve relative order within one worker, a test assigned to another worker may execute concurrently.

Consequently, test-ordering plugins and tests with implicit dependencies can exhibit different behavior under xdist.

`--no-loadscope-reorder` can preserve more relative ordering within the `loadscope` scheduler, but it does not turn distributed execution into a globally sequential schedule.

### 9.4 No built-in cross-worker resource lock manager

pytest-xdist does not centrally arbitrate arbitrary external resources.

`loadgroup` provides process affinity, but it is not a distributed semaphore or resource allocator.

This distinction matters for limited-capacity resources such as a single licensed service, fixed TCP port, test database instance, or exclusive hardware device.

Affinity can ensure that certain tests share a worker; it cannot prevent unrelated workers or non-pytest processes from accessing the same resource.

### 9.5 Worker process isolation is not test-level isolation

Workers persist across multiple assigned tests.

This permits fixture reuse and amortization of initialization costs, but also allows process-local state to survive from one test to another within the same worker.

pytest-xdist does not create a new interpreter for every test by default.

A fresh-process-per-test execution model is a different isolation strategy and should not be assumed merely because xdist uses subprocesses.

### 9.6 Terminal size and environment differences

The official limitations document also notes that worker processes may observe a different terminal width from the user's interactive terminal.

This can affect tests that assert exact formatting of terminal output.

The documented workaround is to control terminal width explicitly, for example through the `COLUMNS` environment variable or appropriate monkeypatching.

Source: [https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html](https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation



## 10. Performance characteristics and architectural tradeoffs

pytest-xdist's performance depends primarily on how much independently executable work exists relative to the cost of creating and coordinating workers.

Its theoretical advantage comes from executing tests concurrently across multiple processes rather than serially within one pytest session.

However, the effective runtime includes costs that differ from ordinary pytest.

| Performance consideration | Mechanism                                                | Implication                                                |
| ------------------------- | -------------------------------------------------------- | ---------------------------------------------------------- |
| Repeated collection       | Every worker performs test discovery                     | Collection CPU and memory costs increase with worker count |
| Process initialization    | Separate Python runtimes and plugin initialization       | Small suites can be dominated by startup costs             |
| Fixture duplication       | Session and higher-scoped state is per worker            | Expensive setup may recur across processes                 |
| Scheduling imbalance      | Workers receive workloads of different actual durations  | Long-running test groups can create idle capacity          |
| IPC and reporting         | Workers communicate results through execnet              | Coordination overhead grows with event volume              |
| Resource contention       | Workers may compete for CPU, memory, disk, or services   | More workers can reduce throughput                         |
| Cache locality            | Related tests can reuse worker-local fixtures and caches | Grouped execution can outperform fine-grained reassignment |
| Crash recovery            | Replacement workers must initialize and collect again    | Reliability improves at the cost of recovery overhead      |

A useful conceptual model is:

\\[ T\_{\text{parallel}} \approx T\_{\text{startup/collection}} + \max_i(T\_{\text{worker},i}) + T\_{\text{coordination}} \\]

Here, the worker term includes assigned test execution and relevant fixture costs. The expression is an explanatory approximation, not an upstream performance guarantee.

The cost of repeated collection is especially important in suites with expensive dynamic discovery or collection-time imports.

Meanwhile, fixture-heavy suites can benefit more from scheduling locality than from maximizing the number of individual scheduling decisions.

This explains why `load`, `loadscope`, `loadfile`, `loadgroup`, and `worksteal` represent genuinely different optimization policies rather than cosmetic variations.

The general architectural opportunity is to use test scheduling affinity, worker-local caching, and explicit resource partitioning together, reducing duplicated setup while preserving useful concurrency. The right combination remains workload-dependent.

## 11. Installation, dependencies, and version status

### 11.1 Required and optional dependencies

The 3.8.0 package metadata specifies Python 3.9 or newer, pytest 7.0 or newer, and execnet 2.1 or newer.

| Dependency     | Status                    | Role                                                       |
| -------------- | ------------------------- | ---------------------------------------------------------- |
| `pytest`       | Required                  | Test framework, collection, fixtures, and reporting        |
| `execnet`      | Required                  | Worker communication and execution gateways                |
| `psutil`       | Optional extra            | CPU-count detection                                        |
| `setproctitle` | Optional extra            | Human-readable worker process titles                       |
| `filelock`     | Testing extra / companion | Interprocess locking in documented shared-fixture patterns |

Installation can be as simple as:

```
pip install pytest-xdist
```

Or with optional integration facilities:

```
pip install "pytest-xdist[psutil,setproctitle]"
```

Version 3.8.0 explicitly lists Python 3.9–3.13 among its supported classifiers. Its metadata allows later Python 3.x versions through `>=3.9`, but this should not be confused with explicit upstream testing or a compatibility guarantee for every newer Python release.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/pyproject.toml](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/pyproject.toml?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 11.2 Significant release developments

| Release    | Important changes                                                                          |
| ---------- | ------------------------------------------------------------------------------------------ |
| 3.8.0      | Explicit `loadscope` reordering controls                                                   |
| 3.7.0      | Python 3.13 support, atomic work stealing, proxy gateways, composite `xdist_group` markers |
| 3.6.1      | Compatibility fix for execnet main-thread execution and pytest-cov                         |
| 3.6.0      | Main-thread worker execution; release subsequently yanked                                  |
| 3.5.0      | Largest-scope-first scheduling for `loadscope`                                             |
| 3.2.0      | Work-stealing scheduler and `--maxschedchunk`                                              |
| 3.0 series | Deprecation of legacy remote rsync functionality                                           |

Source: [https://pytest-xdist.readthedocs.io/en/stable/changelog.html](https://pytest-xdist.readthedocs.io/en/stable/changelog.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation



### 11.3 Development-branch functionality not present in 3.8.0

A version-sensitive documentation issue deserves specific attention.

The current upstream development documentation contains functionality beyond the published 3.8.0 release.

`--ramp=DURATION`

The development branch includes a mechanism for staggering the beginning of test execution across workers. According to the current development documentation, workers initialize and collect tests normally, but delay their first test execution.

This is not equivalent to gradually creating workers.

The option is present in upstream development documentation and source but absent from the tagged 3.8.0 plugin implementation.

Python CPU-count overrides

The development documentation also describes explicit support for Python's `-X cpu_count` interpreter option and `PYTHON_CPU_COUNT` environment variable, including an override precedence involving xdist's own worker-count hook and environment variable.

The corresponding explicit override handling is not present in the 3.8.0 tagged plugin source.

Consequently, the development documentation's full override semantics should not be attributed to 3.8.0 without testing or inspecting the actual installed version.

This is a concrete example of why `/en/latest/` documentation and the latest published stable package should not automatically be treated as identical.

Sources:

[https://pytest-xdist.readthedocs.io/en/latest/distribution.html](https://pytest-xdist.readthedocs.io/en/latest/distribution.html?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/plugin.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/plugin.py?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/master/src/xdist/plugin.py](https://github.com/pytest-dev/pytest-xdist/blob/master/src/xdist/plugin.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+2



### 11.4 Deprecated loop-on-failure mode

pytest-xdist retains `-f` / `--looponfail`, which runs tests in a subprocess and waits for watched files to change before rerunning failures.

After previously failing tests pass, the mechanism performs another full-suite run.

It is distinct from the ordinary parallel schedulers and is marked deprecated in the project's documentation.

The implementation also supports `looponfailroots` for configuring watched directories.

Because it remains present in 3.8.0 but is deprecated, it belongs in the capability inventory without being treated as an active area of architectural development.

Sources:

[https://pytest-xdist.readthedocs.io/en/stable/](https://pytest-xdist.readthedocs.io/en/stable/?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/looponfail.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/looponfail.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytest-xdist.readthedocs.io\&sz=32)

pytest-xdist documentation+1



## 12. Overall architectural assessment

pytest-xdist provides substantially more than elementary multiprocessing for pytest.

Its architectural capabilities are particularly meaningful in four areas.

Scheduling and placement. The library provides multiple production-ready scheduling policies, including work stealing, grouping, and fine-grained load balancing. These mechanisms can remove the need to implement independent test queues, worker assignment logic, and basic resource-affinity scheduling.

Distributed worker management. It supplies worker creation, communication, test collection validation, result transport, crash detection, and recovery. This infrastructure is built on execnet rather than a bespoke multiprocessing protocol.

Extensibility. Its hooks allow the controller to be adapted for worker provisioning, scheduling, metadata propagation, and crash handling. More specialized policies can therefore be implemented inside the pytest execution model rather than through an entirely separate test orchestration system.

Ecosystem composition. Because workers execute ordinary pytest sessions and the controller forwards standard reporting events, xdist interoperates with coverage, reporting, retry, and other compatible pytest plugins, while retaining a clear separation of responsibilities.

Its principal limitations arise from the same architecture: every worker performs collection, fixtures are process-local, external shared resources require coordination, global test ordering is not provided, and certain interactive debugging workflows are unavailable.

The most consequential choice when using pytest-xdist is therefore not simply the worker count. It is the relationship between scheduling granularity, fixture locality, shared-resource semantics, and test independence.

For advanced engineering use, the most valuable areas to understand in depth are the `loadscope`/`loadgroup` affinity mechanisms, `worksteal` and its limitations, worker identity and shared-resource initialization, and the custom `Scheduling` protocol. Together, these features provide a flexible foundation for sophisticated parallel testing without requiring the library to become a general-purpose distributed task framework.

## Primary source reference map

| Topic                              | Direct source                                                                                                                                                                                           |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Overall functionality              | [https://pytest-xdist.readthedocs.io/en/stable/](https://pytest-xdist.readthedocs.io/en/stable/?utm_source=chatgpt.com)                                                                                 |
| Distribution strategies            | [https://pytest-xdist.readthedocs.io/en/stable/distribution.html](https://pytest-xdist.readthedocs.io/en/stable/distribution.html?utm_source=chatgpt.com)                                               |
| Controller–worker architecture     | [https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html](https://pytest-xdist.readthedocs.io/en/stable/how-it-works.html?utm_source=chatgpt.com)                                               |
| Worker identification and fixtures | [https://pytest-xdist.readthedocs.io/en/stable/how-to.html](https://pytest-xdist.readthedocs.io/en/stable/how-to.html?utm_source=chatgpt.com)                                                           |
| Remote gateways                    | [https://pytest-xdist.readthedocs.io/en/stable/remote.html](https://pytest-xdist.readthedocs.io/en/stable/remote.html?utm_source=chatgpt.com)                                                           |
| Known limitations                  | [https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html](https://pytest-xdist.readthedocs.io/en/stable/known-limitations.html?utm_source=chatgpt.com)                                     |
| Crash recovery                     | [https://pytest-xdist.readthedocs.io/en/stable/crash.html](https://pytest-xdist.readthedocs.io/en/stable/crash.html?utm_source=chatgpt.com)                                                             |
| Changelog                          | [https://pytest-xdist.readthedocs.io/en/stable/changelog.html](https://pytest-xdist.readthedocs.io/en/stable/changelog.html?utm_source=chatgpt.com)                                                     |
| Extension hooks, v3.8.0            | [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/newhooks.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/newhooks.py?utm_source=chatgpt.com)                     |
| Scheduler protocol, v3.8.0         | [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/protocol.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/protocol.py?utm_source=chatgpt.com) |
| Controller implementation          | [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py?utm_source=chatgpt.com)                     |
| Worker manager                     | [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py?utm_source=chatgpt.com)             |
| Worker execution runtime           | [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py?utm_source=chatgpt.com)                         |
| pytest-cov interoperability        | [https://pytest-cov.readthedocs.io/en/stable/xdist.html](https://pytest-cov.readthedocs.io/en/stable/xdist.html?utm_source=chatgpt.com)                                                                 |
| Retry integration                  | [https://github.com/pytest-dev/pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures?utm_source=chatgpt.com)                                                                         |

Research basis: Context7's pytest-xdist documentation index, official stable and development documentation, the v3.8.0 tagged upstream implementation, PyPI release metadata, and primary documentation for relevant companion plugins. Architectural implications are distinguished from features implemented directly by pytest-xdist; no application-specific benchmarks were performed.

# pytest-xdist — Technical Capability Addendum

Research date: November 6, 2026 | Target release: pytest-xdist 3.8.0

This addendum supplements the original pytest-xdist overview with additional capabilities and implementation-level distinctions identified through the gap analysis. It concentrates on cross-process communication, custom reporting, scheduling internals, lifecycle hooks, execution isolation, and relevant companion libraries.

The baseline is pytest-xdist 3.8.0, which remains the latest published stable release. Features described here are verified against the versioned upstream implementation unless explicitly identified as companion-library functionality or architectural inference.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



## 1. Bidirectional communication between controller and workers

### 1.1 The `workerinput` and `workeroutput` data channels

pytest-xdist exposes two complementary mechanisms for transferring plugin-defined data across the controller–worker boundary:

| Mechanism                                   | Direction           | Availability                     | Purpose                                                             |
| ------------------------------------------- | ------------------- | -------------------------------- | ------------------------------------------------------------------- |
| `node.workerinput` / `config.workerinput`   | Controller → worker | During worker initialization     | Supply configuration, identifiers, and worker-specific metadata     |
| `config.workeroutput` / `node.workeroutput` | Worker → controller | During orderly worker completion | Return worker-produced statistics, metadata, and aggregated results |

The previous overview described `workerinput` but omitted `workeroutput`, which provides a useful native alternative to introducing custom IPC for relatively small amounts of worker-produced information.

In the 3.8.0 implementation, the worker bootstrap initializes `config.workeroutput` to an empty dictionary. The worker's `pytest_sessionfinish` hook wrapper populates several xdist-owned fields:

- `exitstatus`: the worker's pytest exit status, represented as an integer.
- `shouldfail`: the session's requested failure condition.
- `shouldstop`: the session's requested stop condition.

The wrapper then yields to the other implementations of `pytest_sessionfinish`, allowing plugins to contribute their own values before xdist sends the `workerfinished` event containing the dictionary.

The controller's `WorkerController` receives that event, assigns the returned dictionary to `node.workeroutput`, and notifies the distributed session manager. The latter invokes `pytest_testnodedown(node, error=None)`.

These behaviors are implemented directly in the worker and controller lifecycle code; they are not dependent on pytest-cov or an additional statistics plugin.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### 1.2 Aggregating worker-produced information

A plugin loaded in both controller and worker processes can exploit the complete communication path.

The following is an illustrative pattern:

```
import pytest@pytest.hookimpl(optionalhook=True)def pytest_configure_node(node):    # Controller: populate configuration before worker bootstrap.    node.workerinput["execution_profile"] = "integration"@pytest.fixture(scope="session")def execution_profile(request):    # Worker: consume controller-supplied configuration.    return getattr(request.config, "workerinput", {}).get(        "execution_profile", "default"    )def pytest_sessionfinish(session, exitstatus):    # Worker: add custom summary data to the final message.    output = getattr(session.config, "workeroutput", None)    if output is not None:        output["application_stats"] = {            "resources_created": 4,            "cache_entries": 120,        }@pytest.hookimpl(optionalhook=True)def pytest_testnodedown(node, error):    # Controller: receive the completed worker's output.    output = getattr(node, "workeroutput", None)    if output is not None:        stats = output.get("application_stats", {})        # Incorporate stats into controller-side aggregation.
```

This illustrates the API interactions, not a complete statistics implementation. In particular, the values shown are illustrative and would need to be derived from actual worker-side instrumentation.

The plugin must be loaded in the relevant process contexts. A controller-side hook cannot be assumed to execute simply because its implementation exists in a test `conftest.py` loaded during worker collection. A separately registered pytest plugin, available to both processes, provides a clearer integration boundary.

The mechanism enables several useful patterns, including worker-local counters, custom execution summaries, resource-consumption measurements, cache statistics, and application-specific diagnostics.

### 1.3 Communication semantics and limitations

`workeroutput` is a completion-time data-transfer mechanism, not a live distributed shared-memory interface.

Its guarantees and limitations are important:

Serialization. The dictionary is transferred through execnet. Values must therefore be representable by execnet's serialization protocol. Open files, locks, generators, arbitrary extension objects, and process-local references cannot be treated as transparently transferable state.

Completion dependency. The normal data-transfer path requires the worker to execute its orderly shutdown logic. If the worker crashes or loses its communication channel before emitting `workerfinished`, its final output may be unavailable.

No automatic merging. pytest-xdist transfers each worker's dictionary independently. It does not combine application-defined statistics across workers or resolve conflicts between values.

No live synchronization. A controller cannot use `workeroutput` to read continuously updated worker state while tests are executing. Live coordination requires another protocol or shared-state mechanism.

Failure versus clean termination. A cleanly completed worker can have a nonzero pytest exit status. Thus, receiving `pytest_testnodedown(..., error=None)` and a populated `workeroutput` does not establish that every test passed.

The resulting architectural opportunity is to use xdist's existing transport for per-worker aggregation while reserving external state stores or synchronization facilities for information that genuinely needs to be shared during execution.

Primary sources:

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py?utm_source=chatgpt.com)

## 2. Extensible test-report serialization and distributed reporting

### 2.1 pytest's report serialization hooks

pytest-xdist relies on two hooks defined by pytest itself:

```
pytest_report_to_serializable(config, report)pytest_report_from_serializable(config, data)
```

The first converts a pytest report into a transportable representation; the second reconstructs a report from that representation.

Both use pytest's `firstresult` hook semantics: the first non-`None` result is used. They therefore permit plugins to handle specialized report types or serialization formats, but they do not automatically merge the output of multiple independent serializers.

pytest-xdist invokes the serialization hook inside workers and the deserialization hook in the controller, with execnet transporting the serialized representation.

This creates a meaningful integration point for plugins that attach structured information to test results, implement custom report types, or need plugin-specific information to survive the process boundary.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytest.org\&sz=32)

pytest documentation+2



### 2.2 Worker metadata attached to reports

During report transmission, pytest-xdist adds identifiers that allow the controller to associate results with their originating worker.

| Attribute            | Meaning                                                                          |
| -------------------- | -------------------------------------------------------------------------------- |
| `report.worker_id`   | Worker identifier associated with the report                                     |
| `report.testrun_uid` | Shared identifier of the distributed execution                                   |
| `report.node`        | Controller-side `WorkerController` associated with the report                    |
| `report.item_index`  | Internal index of the corresponding item in the worker's collected test sequence |

The worker serializes `item_index`, `worker_id`, and `testrun_uid`. The controller reconstructs the report, and the distributed session manager attaches `report.node` before forwarding the report through `pytest_runtest_logreport`.

This allows a controller-side reporting plugin to reason about worker-level execution without independently tracking every assignment.

For example, worker identifiers and report durations can support per-worker execution summaries, while worker metadata can distinguish failures associated with different Python interpreters or execution hosts.

The `item_index` attribute is particularly relevant to xdist's scheduling protocol. It identifies the item within a worker's collected sequence and should not be treated as a durable test identifier across independent runs.

Sources:

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 2.3 Collection reports are deliberately filtered

A subtle but consequential distinction is that pytest-xdist does not transmit every successful collection report from every worker.

The worker implementation forwards collection reports only when they have not passed. The controller therefore receives failed or skipped collection reports, while successful collection reports are suppressed to reduce communication overhead.

Consequently, a controller-side plugin consuming `pytest_collectreport` does not necessarily observe the same complete sequence of successful collection events it would receive in an ordinary sequential pytest session.

For identifying what workers collected, the dedicated `pytest_xdist_node_collection_finished` hook is the more appropriate mechanism.

This distinction is important for collection analyzers, test inventories, and plugins that derive information from collection events.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 2.4 Warning serialization and preservation limits

Warnings also cross the worker–controller boundary.

The worker serializes warning-related information, including message text, category metadata, and contextual fields. The controller reconstructs a warning representation and forwards it to pytest's warning-reporting hooks.

Not every detail of an arbitrary warning object is guaranteed to survive unchanged. The worker implementation contains fallback behavior for values that execnet cannot serialize.

This means that warning metadata should not be treated as a transparent transfer of the original Python object.

For structured diagnostics requiring stronger preservation guarantees, an explicit serializable representation is preferable to relying on arbitrary warning arguments.

### 2.5 Reporting extensions must account for process boundaries

A report created inside a worker is not the same in-memory object as the report reconstructed by the controller.

Custom attributes, exception representations, and auxiliary objects may be transformed or lost unless they are included in the supported serialization representation.

This is especially important for plugins that modify `pytest_runtest_makereport`, attach additional diagnostic state, or expect controller-side reporting hooks to access worker-local pytest items.

The compositional advantage is that pytest-xdist supplies the report transport while pytest supplies the extensible serialization protocol. A reporting plugin can integrate with those interfaces instead of building a separate communication channel, provided its data model respects their serialization and lifecycle constraints.

Primary sources:

[https://docs.pytest.org/en/stable/reference/reference.html](https://docs.pytest.org/en/stable/reference/reference.html?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py?utm_source=chatgpt.com)

## 3. Additional scheduling behavior and internal heuristics

### 3.1 Duration-sensitive replenishment in `LoadScheduling`

The default `load` scheduler has a limited form of duration awareness that was not described in the original overview.

Its `check_schedule()` method considers both outstanding queue lengths and the duration of the most recently completed test.

The scheduler calculates a target minimum and maximum number of queued items for each worker using the size of the global pending queue and the number of active workers.

In version 3.8.0, its formulas are:

\\[ q\_{\min}=\max\left(2,\left\lfloor\frac{P}{4W}\right\rfloor\right) \\]

\\[ q\_{\max}=\max\left(2,\left\lfloor\frac{P}{2W}\right\rfloor\right) \\]

where \\(P\\) is the number of globally pending tests and \\(W\\) is the number of registered workers.

When a worker's outstanding queue falls below the minimum, the scheduler considers replenishing it toward the maximum.

However, if the last completed test took at least 0.1 seconds and the worker already has two or more outstanding items, replenishment may be deferred.

This reduces the tendency to accumulate additional outstanding work on a worker that is executing relatively long tests.

The behavior is not a historical test-duration model. It neither predicts individual test runtimes nor optimizes the assignment using previous test-run measurements.

It is a lightweight feedback heuristic based on recently observed execution duration and current queue occupancy.

The distinction matters because `load` is somewhat adaptive to execution speed, even though it does not provide a complete duration-aware scheduling algorithm.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/load.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/load.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 3.2 Queue-aware but not duration-aware work stealing

`WorkStealingScheduling` uses a different scheduling heuristic.

When workers have fewer than two outstanding tests, it first attempts to distribute any globally pending tests to them.

If no globally pending work can satisfy those workers, it considers stealing tests from another worker.

The implementation:

1. Identifies the worker with the longest outstanding test queue.
2. Calculates approximately half that queue as a candidate for stealing.
3. Ensures that at least two queued items remain assigned to the donor.
4. Requests the removal of those candidate items from the donor's queue.
5. Reassigns items returned by the donor as successfully unscheduled.

Only one steal request is outstanding at a time. The worker queue's atomic removal operation ensures that an attempted steal either removes all requested items or none of them.

This provides load balancing using queued item counts, rather than estimated time remaining.

A worker with two extremely expensive tests may have more remaining work than a worker with ten inexpensive tests, but the scheduler does not infer that from historical duration information.

This distinction helps explain both the scheduler's simplicity and its limitations.

A custom implementation that uses historical timings would be architecturally different from xdist's built-in work stealing.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/worksteal.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/worksteal.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 3.3 Automatic reduction of surplus grouped workers

`LoadScopeScheduling` contains an explicit optimization for cases where the requested worker count exceeds the number of scheduling work units.

After constructing its initial work queue, it computes:

```
extra_nodes = len(self.nodes) - len(self.workqueue)
```

When the result is positive, it initiates shutdown of the surplus workers rather than leaving them waiting indefinitely for groups that do not exist.

Because `LoadFileScheduling` and `LoadGroupScheduling` inherit the underlying scope scheduler, this behavior also applies to those modes.

For example, if a configuration launches 12 workers but the test collection forms only four independent groups, no more than four workers can execute those initial groups concurrently.

An important performance qualification is that the optimization occurs after workers have initialized and collected tests. It reduces unused execution capacity but does not avoid the initialization and collection costs already incurred by those workers.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 3.4 Internal construction of `xdist_group` identities

The 3.8.0 worker implementation handles explicit grouping during `pytest_collection_modifyitems`.

For each test, it collects applicable `xdist_group` marks, converts their names into strings, removes duplicates, sorts the names, and joins them using underscores.

It then appends the resulting group identity to the test's node ID using an `@` separator.

Conceptually:

```
tests/test_storage.py::test_insert
```

becomes:

```
tests/test_storage.py::test_insert@database_storage
```

The `LoadGroupScheduling` implementation subsequently extracts the effective group identity from that modified node ID.

This explains how fixture-, module-, and test-level grouping information becomes a scheduling unit without transmitting a separate fixture-dependency graph to the controller.

There are two consequential details.

First, the group's internal representation is based on node ID mutation, not a separate opaque group identifier. Plugins consuming test node IDs under `loadgroup` may therefore observe identifiers with group suffixes.

Second, the composite naming scheme can theoretically produce collisions when constituent names contain underscores. For example, `{a_b, c}` and `{a, b_c}` both produce the string `a_b_c`. This is an inference from the tagged implementation, not a documented collision-avoidance guarantee.

The practical significance is that grouping is deterministic with respect to marker order, but composite group identity should not be confused with a structured, collision-proof set representation.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 3.5 Scope ordering affects inherited schedulers at the implementation level

Version 3.8.0 introduced `--loadscope-reorder` and `--no-loadscope-reorder`, documented specifically for `loadscope`.

However, `loadfile` and `loadgroup` inherit `LoadScopeScheduling.schedule()`, which reads the same `config.option.loadscopereorder` setting when constructing and ordering work units.

Therefore, the tagged implementation suggests that the flag can affect group ordering under those schedulers as well.

This is an implementation-level observation rather than a separately documented public guarantee. The official changelog explicitly scopes the option to `loadscope`.

That discrepancy matters for developers who want consistent ordering across execution modes: behavior inherited through the implementation may be available today without being part of the project's declared compatibility contract.

Sources:

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadfile.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadfile.py?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadgroup.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadgroup.py?utm_source=chatgpt.com)

[https://pytest-xdist.readthedocs.io/en/stable/changelog.html](https://pytest-xdist.readthedocs.io/en/stable/changelog.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+3



## 4. Crash recovery and scheduler-extension compatibility

### 4.1 Not every scheduler supports `mark_test_pending`

The original overview described `pytest_handlecrashitem` as a mechanism for intercepting a test interrupted by a worker crash and using `sched.mark_test_pending()` to request another execution.

That facility is present, but it is not implemented uniformly by all built-in schedulers.

| Distribution strategy | Explicit `mark_test_pending()` support |
| --------------------- | -------------------------------------- |
| `load`                | Implemented                            |
| `worksteal`           | Implemented                            |
| `loadscope`           | Raises `NotImplementedError`           |
| `loadfile`            | Inherits the unimplemented method      |
| `loadgroup`           | Inherits the unimplemented method      |
| `each`                | Raises `NotImplementedError`           |

This distinction is especially important because the scheduler protocol declares the method, but the presence of a protocol member does not establish that every implementation provides functional behavior.

A plugin that unconditionally calls `sched.mark_test_pending(crashitem)` can therefore fail under grouped or full-suite-replication scheduling.

A custom crash-handling extension must account for the particular scheduler implementation rather than assuming all built-in modes provide identical rescheduling capabilities.

Sources:

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/load.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/load.py?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/worksteal.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/worksteal.py?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/each.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/each.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+3



### 4.2 Scheduler recovery versus explicit test requeueing

The missing `mark_test_pending()` implementation should not be interpreted as an absence of crash recovery.

The built-in schedulers distinguish between two operations:

Removing a failed worker. `remove_node()` removes the worker from scheduler state, accounts for work that was assigned to it, and identifies the test interrupted by the crash.

Explicitly requeueing a test. `mark_test_pending()` is used by extensions to insert a particular test back into the scheduling queue.

In the grouped schedulers, `remove_node()` can return unfinished work units to the available work queue while separately identifying the crash item.

This allows outstanding tests to be recovered even though arbitrary test-level requeueing is not implemented.

The distinction reflects the schedulers' data models. A grouped scheduler maintains work-unit affinity and completion state, whereas `load` and `worksteal` maintain queues of individual test indices.

An arbitrary test-level retry is therefore not necessarily compatible with the original group's scheduling semantics.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/scheduler/loadscope.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 4.3 Crash reports are synthetic and contain limited diagnostic information

When a worker crashes, the controller constructs a new `pytest.TestReport` identifying the interrupted test.

The synthetic report includes the test node ID, an outcome of `failed`, a message identifying the crashed worker, and a reference to the corresponding worker controller.

However, the report is not produced by the normal execution of `pytest_runtest_makereport`.

The implementation even uses a placeholder for the execution phase because it cannot reliably determine whether the crash happened during setup, call, or teardown.

Consequently, reporting integrations should distinguish synthetic crash reports from ordinary assertion-failure reports.

The `pytest_handlecrashitem` hook receives this synthetic report before the controller forwards it through `pytest_runtest_logreport`, allowing extensions to modify the representation or request supported rescheduling.

This hook does not provide enough information to reconstruct arbitrary Python state or external side effects that existed immediately before the crash.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 5. Remote worker bootstrapping and lifecycle extension points

### 5.1 Replacing the remote execution module

The `pytest_xdist_getremotemodule` hook provides a lower-level extension point than ordinary worker configuration.

By default, pytest-xdist uses `xdist.remote` as the module executed inside each worker through execnet.

During `WorkerController.setup()`, the controller invokes:

```
remote_module = config.hook.pytest_xdist_getremotemodule()self.channel = self.gateway.remote_exec(remote_module)
```

A plugin implementing `pytest_xdist_getremotemodule` can substitute another executable module.

This is fundamentally different from `pytest_configure_node`, which modifies information sent to the standard remote worker.

Replacing the remote module potentially allows control over worker bootstrap, runtime initialization, communication behavior, and integration with specialized execution environments.

However, the extension is not equivalent to providing a custom Python entry point with arbitrary behavior. The replacement must communicate with the controller according to the protocol expected by `WorkerController` and `DSession`.

That protocol includes startup configuration, readiness notifications, collection results, execution commands, test reports, worker completion, and failure handling.

A modified worker runtime that does not honor those expectations may fail during initialization or cause inconsistencies in scheduling and reporting.

The hook is therefore best understood as a low-level worker-runtime replacement facility, with substantially greater integration obligations than a custom pytest fixture or scheduler.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 5.2 Worker lifecycle phases and corresponding hooks

Several lifecycle hooks were listed in the original overview without explaining their exact relationship to worker initialization and scheduling.

The following sequence shows where they participate.

| Lifecycle phase                 | Relevant hook or interface              | Available information or intervention                        |
| ------------------------------- | --------------------------------------- | ------------------------------------------------------------ |
| Execution environments prepared | `pytest_xdist_setupnodes`               | Inspect execution specifications before workers are created  |
| Gateway created                 | `pytest_xdist_newgateway`               | Observe the newly established execnet gateway                |
| Worker configuration            | `pytest_configure_node`                 | Modify `workerinput` before bootstrap                        |
| Worker module selection         | `pytest_xdist_getremotemodule`          | Supply the remote execution module                           |
| Worker initialized              | `pytest_testnodeready`                  | Inspect the ready worker and its execution environment       |
| Worker collection completed     | `pytest_xdist_node_collection_finished` | Examine the worker's ordered test node IDs                   |
| Worker completes or terminates  | `pytest_testnodedown`                   | Observe completion, termination, and available worker output |

These hooks expose different stages of the controller's orchestration process.

They should not be treated as interchangeable notifications.

For instance, `pytest_configure_node` runs before the remote runtime begins executing, whereas `pytest_testnodeready` is invoked after the worker has initialized and sent its runtime information.

Similarly, `pytest_xdist_node_collection_finished` executes before the distributed session manager submits the collection to its scheduler.

This permits an extension to inspect the submitted collection, but does not make the hook itself a general interface for replacing the scheduler's collection or assignment decisions.

Those decisions belong to the scheduler implementation.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 5.3 Runtime information exposed by workers

During startup, workers send a runtime information dictionary to the controller.

The version 3.8.0 implementation includes information such as:

| Field          | Description                               |
| -------------- | ----------------------------------------- |
| `version`      | Full Python version string                |
| `version_info` | Structured Python version tuple           |
| `sysplatform`  | `sys.platform`                            |
| `platform`     | Operating-system and platform description |
| `executable`   | Python executable path                    |
| `cwd`          | Worker working directory                  |
| `id`           | Controller-assigned worker identity       |
| `spec`         | execnet execution specification           |

The controller stores this information as `node.workerinfo`.

This is particularly relevant for heterogeneous execution environments.

For example, a reporting extension could associate failures with interpreter versions and operating systems. A custom scheduling implementation could potentially consider worker environment characteristics when making assignment decisions.

The built-in schedulers do not automatically use this metadata for generalized capability matching. Using it to create an environment-aware scheduling policy would require additional logic.

Sources:

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/remote.py?utm_source=chatgpt.com)

[https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/dsession.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 5.4 Original command-line arguments

The controller includes `mainargv` in the worker's initialization dictionary.

The field contains the original `sys.argv` captured in the controller process:

```
request.config.workerinput["mainargv"]
```

This can be relevant when a plugin needs to understand the original invocation, rather than the arguments reconstructed or transformed for an individual worker.

Such transformations are especially pertinent to remote execution, where paths and execution specifications may differ between controller and worker environments.

However, `mainargv` is diagnostic input, not a guarantee that every original command-line argument is meaningful or valid inside the worker.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/workermanage.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 6. Additional command-line and execution-state distinctions

### 6.1 Collection-only mode bypasses distributed execution

When pytest is invoked with `--collect-only`, the 3.8.0 plugin deliberately avoids registering its distributed session manager.

Consequently, even when worker-count options are configured, collection-only execution is not transformed into a normal distributed run.

This is meaningful for tooling that analyzes test discovery, collection structure, or generated test inventories.

Such tools should not expect worker readiness events or distributed collection-completion hooks merely because pytest-xdist is installed or parallel execution options appear in the configuration.

The normal pytest collection machinery remains responsible for collection-only operation.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/plugin.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/plugin.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 6.2 PDB compatibility depends on how workers are requested

The original overview correctly identified interactive PDB debugging as incompatible with distributed execution, but the command-line behavior deserves clarification.

In version 3.8.0, specifying `--pdb` with `-n auto` or `-n logical` causes xdist to disable distributed execution.

By contrast, explicitly requesting a nonzero worker count alongside `--pdb` generally produces a pytest usage error.

For example:

```
pytest -n auto --pdb
```

disables distribution, whereas:

```
pytest -n 8 --pdb
```

requests an incompatible combination.

This is an intentional distinction in the option-resolution implementation, rather than a difference in whether PDB can communicate with one type of worker versus another.

Source: [https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/plugin.py](https://github.com/pytest-dev/pytest-xdist/blob/v3.8.0/src/xdist/plugin.py?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 7. Companion libraries extending pytest-xdist's capabilities

Several relevant capabilities are implemented outside pytest-xdist itself. These integrations are worth identifying because they address functional boundaries that otherwise require additional custom tooling.

### 7.1 pytest-forked: per-test process isolation

pytest-forked provides test-level subprocess isolation and originated from functionality previously included in pytest-xdist.

It can be combined with xdist:

```
pytest -n 8 --forked
```

The resulting execution model has two levels of process management.

pytest-xdist coordinates eight independent workers, while pytest-forked creates forked subprocesses for individual test executions.

This is useful for testing native extensions, code capable of crashing the interpreter, and tests that leave undesirable process-local state behind.

pytest-forked also supports selective isolation using the `forked` marker:

```
import pytest@pytest.mark.forkeddef test_native_extension():    ...
```

The distinction from ordinary xdist workers is important. Without pytest-forked, multiple tests can execute sequentially inside the same persistent worker interpreter. With per-test forking, those tests execute in separate child processes.

However, a forked process inherits state from its parent at fork time. It should not be confused with a completely fresh interpreter initialized independently from scratch.

Limitations: pytest-forked does not work on Windows because it requires operating-system fork support. Its maintainers also state that maintenance beyond the minimum is not planned until a new maintainer is found.

Primary source: [https://github.com/pytest-dev/pytest-forked](https://github.com/pytest-dev/pytest-forked?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 7.2 pytest-rerunfailures: interoperability constraints

The original overview described how pytest-rerunfailures can retry ordinary failures and work with xdist's crash-handling infrastructure.

Several compatibility qualifications are important.

Remote crash recovery. The plugin's documentation states that hard-crash recovery with xdist assumes workers and the controller are on the same LAN. It warns that the functionality may not operate correctly when this assumption is violated.

This qualification matters for remotely distributed test execution, where a worker might execute in a different network environment.

Incompatible execution plugins. pytest-rerunfailures explicitly identifies incompatibilities with both pytest-forked and xdist's deprecated `--looponfail`.

The pytest-forked conflict arises because both plugins override `pytest_runtest_protocol`, and their competing implementations prevent the intended rerun behavior.

This illustrates an important general constraint of pytest plugin composition: two extensions can independently support pytest but still conflict when they take ownership of the same execution hook.

Fixture behavior. pytest-rerunfailures can retry failures during fixture setup, including higher-scoped fixtures. Nevertheless, fixture setup already completed successfully remains subject to the normal pytest fixture cache.

Retrying a failed test therefore does not necessarily mean every fixture associated with that test is reconstructed.

This distinction can be consequential when a test's failure may have affected shared fixture state.

Primary source: [https://github.com/pytest-dev/pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



### 7.3 pytest-xdist-worker-stats: worker-level reporting

pytest-xdist-worker-stats extends distributed reporting by producing worker-specific execution statistics.

It provides:

- Per-worker test counts and accumulated runtimes.
- Minimum, maximum, and average test counts across workers.
- Minimum, maximum, and average worker runtimes.
- Optional breakdowns showing which tests executed on each worker.

Its `--xdist-breakdown` option enables the detailed per-worker test inventory, while `--no-xdist-runtimes` suppresses individual worker runtime reporting and retains the summary.

The package is useful for analyzing scheduling imbalance without implementing custom worker-level statistics collection.

Importantly, it supplies reporting rather than changing scheduling decisions. It does not automatically feed its observations into a historical duration-aware scheduler.

Source: [https://pypi.org/project/pytest-xdist-worker-stats/](https://pypi.org/project/pytest-xdist-worker-stats/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



### 7.4 pytest-xdist-rate-limit: shared state and coordinated execution pacing

pytest-xdist-rate-limit is a third-party plugin that adds cross-worker coordination functionality beyond xdist's native `workerinput` and `workeroutput` mechanisms.

Its documented capabilities include controlled execution pacing, callbacks when the target rate cannot be maintained, file-backed JSON state shared between workers, and first-worker/last-worker setup and teardown coordination.

The shared-state facility addresses a different problem from `workeroutput`.

`workeroutput` collects data after a worker completes. File-backed shared state enables coordination and state exchange while multiple workers are still executing.

The plugin also exposes pacing utilities such as `make_pacer` and rate expressions through `Rate`, enabling tests to coordinate their workload against a target execution rate.

An important limitation follows from its file-backed design: workers must have access to an appropriate shared storage location with suitable synchronization behavior. The package should not be interpreted as providing an automatically distributed consensus or storage service across arbitrary remote hosts.

Its first/last-worker facilities are also distinct from xdist's ordinary session-scoped fixtures, which initialize independently inside each worker.

The plugin is third-party and classified as beta, rather than being part of pytest-xdist's core stable API.

Source: [https://pypi.org/project/pytest-xdist-rate-limit/](https://pypi.org/project/pytest-xdist-rate-limit/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



### 7.5 pytest-xdist-load-testing: repeated and weighted execution

pytest-xdist-load-testing extends pytest-xdist with a scheduler intended for continuous load generation rather than the usual one-pass execution of a test suite.

Its documented capabilities include repeated execution until interruption, weighted random selection of tests, and programmatic stopping conditions.

For example:

```
pytest --load-test -n 4 tests/test_api.py
```

The plugin supports a `weight` decorator to control the relative frequency of different test functions.

This makes its scheduling model fundamentally different from `load`, `worksteal`, or `each`.

Standard xdist scheduling is designed to execute the selected tests according to the configured distribution policy. The load-testing extension repeatedly selects tests to generate a workload over time.

Its documentation explicitly restricts load-testing mode to a single test module, partly to preserve the intended fixture-handling semantics.

When combined with pytest-xdist-rate-limit, it can support weighted workload selection and controlled arrival rates as separate capabilities.

This is not a general-purpose performance-testing guarantee: accurately characterizing an external system's load, concurrency, latency, and throughput still requires appropriate instrumentation and experimental design.

Source: [https://pypi.org/project/pytest-xdist-load-testing/](https://pypi.org/project/pytest-xdist-load-testing/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



## 8. Architectural implications of the additional capabilities

The additions establish several further distinctions that complement the original overview.

Data aggregation versus live coordination. `workeroutput` provides a built-in completion-time results channel. Shared resources, live synchronization, and inter-worker communication require additional mechanisms. These are different problems and should not be addressed with identical infrastructure by default.

Scheduler protocols versus scheduler implementations. The custom `Scheduling` interface exposes several operations, but the built-in scheduling strategies do not implement every operation uniformly. Extending scheduling behavior requires attention to each implementation's work-unit model, not merely the protocol's declared members.

Resource affinity versus resource ownership. Group scheduling provides process affinity, while companion coordination tools can provide shared state, pacing, and first/last-worker lifecycle semantics. Those mechanisms can complement one another, but none automatically establishes transactional ownership of arbitrary external resources.

Parallelism versus isolation. pytest-xdist provides persistent parallel worker processes. pytest-forked adds another execution boundary for individual tests. The approaches address different failure and state-isolation requirements.

Execution distribution versus workload generation. Native schedulers aim to distribute a selected suite. Third-party load-testing schedulers can change the execution model into repeated, weighted selection. This is a substantive difference in purpose, not merely another balancing heuristic.

Taken together, the most consequential new capability picture is that pytest-xdist provides an extensible distributed pytest runtime with built-in scheduling, worker metadata exchange, completion-time data aggregation, extensible report serialization, and lifecycle control. Companion plugins can then add isolation, retries, live shared state, coordinated pacing, and specialized worker telemetry.

These capabilities allow more sophisticated test execution and instrumentation without necessarily creating a separate orchestration framework. Their benefits depend on respecting process boundaries, implementation-specific scheduler semantics, and the distinct responsibilities of pytest-xdist, pytest, execnet, and the relevant companion packages.

Evidence note: This addendum is based on Context7, the officially published pytest-xdist 3.8.0 source, pytest's hook documentation, and upstream or PyPI documentation for companion packages. Implementation-derived observations are identified as such. No independent runtime benchmarks or plugin interoperability tests were performed.