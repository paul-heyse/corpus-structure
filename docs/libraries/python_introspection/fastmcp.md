# FastMCP 4.1.3 — Comprehensive Python Library Capability Reference

Research date: October 24, 2026 | Target: FastMCP 4.1.3 (latest stable release, October 20, 2026)

FastMCP is a Python framework for building, composing, securing, deploying, and consuming applications that use the Model Context Protocol (MCP). It provides substantially more than a convenient way to expose Python functions as tools: it includes a server framework, a complete client implementation, dynamic component providers, schema and interface transformations, proxying and federation, authorization, application state, background execution, protocol extensions, and interactive MCP applications.

FastMCP 4 is built on the rewritten official MCP Python SDK v2 and supports the July 28, 2026 MCP protocol revision, while maintaining compatibility with older protocol clients through negotiation. Version 4.1.3 is the current stable PyPI release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+2



Primary sources

- Official documentation: `https://gofastmcp.com/`
- Documentation index: `https://gofastmcp.com/llms.txt`
- GitHub: `https://github.com/PrefectHQ/fastmcp`
- Release 4.1.3: `https://github.com/PrefectHQ/fastmcp/releases/tag/v4.1.3`
- PyPI: `https://pypi.org/project/fastmcp/`
- FastMCP 4 capabilities: `https://gofastmcp.com/getting-started/whats-new`
- Python SDK reference: `https://gofastmcp.com/python-sdk/fastmcp-server-server`

## 1. Architectural orientation

FastMCP operates at several distinct layers. Understanding their separation is fundamental to recognizing its architectural capabilities.

| Layer                    | Responsibilities                                         | Principal mechanisms                                                |
| ------------------------ | -------------------------------------------------------- | ------------------------------------------------------------------- |
| Component definition     | Expose typed operations, data, and reusable instructions | Tools, resources, resource templates, prompts                       |
| Component sourcing       | Discover and resolve capabilities from different origins | Local, filesystem, proxy, skills, and custom providers              |
| Interface adaptation     | Reshape capabilities without rewriting implementations   | Transforms, namespaces, tool schemas, visibility, version filtering |
| Server composition       | Combine multiple capability sources behind one endpoint  | Mounting, providers, MCP proxies                                    |
| Request execution        | Validate, authorize, execute, and observe operations     | Context, dependency injection, middleware, lifespans                |
| Stateful interaction     | Support multi-step exchanges despite stateless transport | Elicitation, request state, session state, background tasks         |
| Protocol/runtime         | Communicate with clients and manage server operation     | STDIO, Streamable HTTP, version negotiation, extensions             |
| Client integration       | Consume one or multiple MCP servers                      | `Client`, `ClientGroup`, transport adapters, OAuth                  |
| Interactive applications | Present user interfaces alongside MCP tools              | FastMCP Apps, Prefab, custom HTML, forms and approval controls      |

These layers can be combined, but they solve different problems. A provider determines where a component comes from; a transform determines how it appears or behaves; middleware governs operations flowing through the server; and the transport determines how messages reach it.

### Why this architecture matters

The most consequential property of FastMCP is that the MCP interface need not be tightly coupled to the Python functions implementing it.

A capability may originate as a local Python function, an OpenAPI operation, a dynamically discovered module, or a remote MCP tool. FastMCP can present it through a standardized interface, change its exposed schema, apply authorization and cross-cutting middleware, and combine it with other capabilities.

This permits several architectural patterns:

- Thin interfaces over existing application logic: MCP exposure without duplicating domain implementations.
- Dynamic capability catalogs: Discover components at runtime rather than hardcoding every tool.
- Composable service boundaries: Present several servers as one logical capability surface.
- Agent-oriented interfaces: Search, filter, reshape, or orchestrate tools to reduce the amount of interface material presented to a model.
- Transport-independent implementations: Reuse much of the same application logic in local and remote MCP deployments.

The framework provides the mechanisms, not the application-specific semantics. Domain correctness, data ownership, transaction handling, operation safety, and the security of downstream systems remain application responsibilities.

## 2. Component model: tools, resources, and prompts

FastMCP implements the three primary MCP component families. They share registration, discovery, metadata, authorization, visibility, versioning, and composition infrastructure, but have different protocol semantics.

### 2.1 Tools: typed executable operations

`@mcp.tool` exposes a Python callable as an MCP operation. FastMCP derives a JSON input schema from its signature and type annotations, incorporates docstring parameter descriptions, validates incoming arguments using Pydantic, and serializes the return value into MCP-compatible content.

It supports synchronous and asynchronous functions, Pydantic models, nested collections, unions, optional and defaulted arguments, `Annotated` metadata, and explicit output schemas. Variadic `*args` and `**kwargs` are unsupported because an MCP tool needs an enumerable input contract.

Illustrative example — not executed:

```
from fastmcp import FastMCPfrom pydantic import BaseModel, Fieldmcp = FastMCP("Data Services")class QueryResult(BaseModel):    rows: list[dict]    row_count: int@mcp.tool(    tags={"query", "read"},    timeout=30.0,)async def query_records(    expression: str = Field(description="Validated query expression"),    limit: int = Field(default=100, ge=1, le=1000),) -> QueryResult:    """Execute a read-only query and return structured records."""    ...
```

Here the function signature establishes both the caller-facing input contract and the output contract. The implementation still needs to enforce its stated read-only semantics: schema validation is not authorization, query safety, or domain validation.

FastMCP also supports:

- Tool annotations: `readOnlyHint`, `destructiveHint`, `idempotentHint`, and `openWorldHint` inform clients of intended behavior. They are hints, not independently enforced guarantees.
- Metadata and organization: names, display titles, descriptions, icons, tags, versions, and arbitrary `_meta`.
- Validation modes: default coercive validation or stricter validation where input-type preservation matters.
- Parameter hiding/injection: internal dependencies can be excluded from the schema visible to the model.
- Custom registration: standalone `@tool` and bound-method registration provide alternatives to immediate server registration.

### Structured output versus MCP content

An important distinction is that the tool's result can have two representations:

| Representation       | Purpose                                | FastMCP behavior                                                         |
| -------------------- | -------------------------------------- | ------------------------------------------------------------------------ |
| MCP `content` blocks | Human/model-readable content and media | Text, images, audio and other supported MCP content                      |
| `structuredContent`  | Machine-readable result                | Typed models and structured returns can generate an output schema        |
| `ToolResult`         | Explicit result control                | Allows content, structured content, and metadata to be supplied directly |

A typed Pydantic model, dataclass, or `TypedDict` can produce an MCP `outputSchema`. Primitive results may be wrapped into a root object for structured output, rather than transmitted as a bare scalar schema. On the client, `result.data` is a convenient decoded Python representation, while `result.content` retains the underlying content blocks.

This enables agents and ordinary programs to share a typed operation contract. It also permits schema-aware downstream processing without relying on parsing prose responses. It does not imply a relational result engine, streaming tabular execution, or automatic persistence.

### Execution and concurrency

Synchronous tools are dispatched to a thread pool by default, so blocking functions do not normally monopolize the event loop. `run_in_thread=False` accommodates thread-affine integrations but executes inline and blocks concurrent event-loop work.

Per-tool `timeout` controls execution duration, with consequential limits: cancellation is cooperative for asynchronous work; a timeout cannot safely terminate an already running synchronous thread or roll back an external side effect. Inline synchronous tools cannot combine thread-affinity mode with FastMCP timeouts. Long-running work requiring durable execution is a separate concern addressed by background tasks.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+1



`https://gofastmcp.com/servers/tools`

`https://gofastmcp.com/clients/tools`

### 2.2 Resources: addressable, lazily evaluated data

Resources are identified by URIs and read through the MCP resource protocol. They can expose configuration, documents, structured data, generated reports, and binary content.

```
@mcp.resource("catalog://records/{record_id}")async def record_resource(record_id: str) -> str:    return await load_record_as_json(record_id)
```

A resource handler is evaluated when the client requests it, not necessarily at registration time.

Resource templates expand this model beyond a fixed collection of URIs. FastMCP supports RFC 6570-style URI templates, path variables, wildcard path expansions, and query parameters. Version 4 includes default path-parameter protections against traversal patterns such as `..`, absolute paths, and null bytes. Such protections do not replace application-specific authorization of the resolved resource.

Two further distinctions matter:

1. Resource access is read-oriented at the MCP protocol layer; the Python function is still arbitrary application code and must not be assumed side-effect-free.
2. Resource discovery and resource reading are distinct operations. Large or dynamically generated resource spaces should not be confused with a requirement to enumerate every possible resource instance.

Resources may return text, JSON-compatible content, or binary data, with MIME metadata and explicit `ResourceResult` control where needed.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP



`https://gofastmcp.com/servers/resources`

### 2.3 Prompts: reusable, parameterized message definitions

`@mcp.prompt` exposes a callable that builds a prompt or sequence of messages. FastMCP validates parameters and converts strings, `Message` objects, or `PromptResult` instances into MCP prompt results.

Unlike a tool, a prompt primarily defines what messages a client should use, rather than performing an external operation. A prompt handler can dynamically obtain domain context, but retrieving a prompt does not itself imply that an LLM inference has been executed.

Prompt definitions support argument documentation, required and optional parameters, dynamic rendering, and multiple user/assistant messages. FastMCP also exposes argument-completion handlers to help clients populate prompt or resource-template parameters.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+1



`https://gofastmcp.com/servers/prompts`

`https://gofastmcp.com/servers/completions`

### 2.4 Request context and dependencies

A handler can access MCP runtime capabilities without exposing internal infrastructure objects as client arguments.

`CurrentContext()` injects the current `Context`; `get_context()` offers access from code that cannot receive an explicit parameter. Context exposes server logging, progress, request metadata, request-local state, resource and prompt operations, component visibility, and supported client-interaction mechanisms.

FastMCP's dependency-injection system also supports `Depends`, nested dependencies, asynchronous dependency resolution, scoped cleanup through generator/yield dependencies, and cached dependency values. This allows infrastructure services, request identities, and contextual services to be supplied independently of an operation's JSON input schema.

The distinction is consequential: a database handle, access token, or execution context belongs to the server's trusted execution environment, not to the arguments an LLM is expected to construct.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+1



`https://gofastmcp.com/servers/context`

`https://gofastmcp.com/servers/dependency-injection`

## 3. Providers: dynamic capability sourcing and server federation

Introduced in FastMCP 3 and retained in version 4, providers are one of the framework's most important extension points.

A provider answers two questions: which MCP components are available, and how should requests for those components be resolved?

The server combines components from its providers rather than requiring every tool to be registered directly onto one monolithic instance.

| Provider mechanism           | Component source                         | Architectural significance                                           |
| ---------------------------- | ---------------------------------------- | -------------------------------------------------------------------- |
| `LocalProvider`              | Python-defined tools, resources, prompts | Default local registration; reusable component container             |
| `FastMCPProvider` / mounting | Another FastMCP instance                 | Modular composition and delegation                                   |
| `ProxyProvider`              | Another MCP server                       | Remote federation and transport bridging                             |
| `FileSystemProvider`         | Discoverable Python source files         | File-based organization and optional dynamic reload                  |
| `OpenAPIProvider`            | OpenAPI-described HTTP operations        | Existing API reuse without hand-defining every MCP operation         |
| Skills providers             | Agent skill directories and files        | Distribution of reusable agent instructions and supporting resources |
| Custom `Provider`            | Arbitrary application-defined source     | Dynamic catalogs, external registries, policy-aware discovery        |

### 3.1 Local composition and mounting

`mcp.mount(child, namespace=...)` makes a child server's components available through a parent. Calls are delegated to the child, instead of copying Python functions into the parent as unrelated definitions.

Namespacing resolves collisions across component families: tools and prompts acquire namespace-derived names, while resource URIs and templates receive corresponding namespace treatment.

A mounted server retains its own middleware and lifespan, while the parent's middleware participates in operations exposed through it. This allows independent component ownership while retaining a consolidated MCP surface.

```
from fastmcp import FastMCPcatalog = FastMCP("Catalog")analytics = FastMCP("Analytics")gateway = FastMCP("Combined")gateway.mount(catalog, namespace="catalog")gateway.mount(analytics, namespace="analytics")
```

The example is structural. The individual servers would register their capabilities separately.

Mounting is particularly useful when component ownership, internal dependencies, or lifecycle management differ across functional areas. It is not inherently a distributed deployment; for that, remote proxies are relevant.

### 3.2 Proxies and remote MCP federation

`create_proxy()` constructs a FastMCP proxy backed by another MCP server. A proxy can expose a remote HTTP server to a local STDIO client, or combine independent remote servers behind one externally visible endpoint.

Beyond forwarding tool calls, the documented proxy supports MCP protocol features including roots, sampling, elicitation, logging, and progress, subject to the relevant protocol capabilities and client support.

The architectural distinction is between composition of implementations and composition of endpoints:

- Mounting a local child shares a Python runtime but preserves component boundaries.
- Proxying delegates operations across an MCP connection.
- A server can mount a proxy, combining local and remote components.

Remote federation introduces network latency, downstream availability requirements, authentication and credential boundaries, and potentially different protocol versions. The proxy does not automatically make remote operations local, transactional, or mutually atomic.

### 3.3 Filesystem and custom providers

`FileSystemProvider` discovers annotated components in Python files. It can supply an organization mechanism for larger tool collections and supports reload behavior that reexamines source files.

This loads and executes Python code; it is not a sandbox for untrusted component definitions.

Custom providers allow the source of truth for components to reside somewhere other than Python decorators. An implementation can supply dynamic discovery and retrieval logic for tools, resources, and prompts. This is the native extension point for capability catalogs whose contents change or are derived from external metadata.

Provider ordering and name collisions matter because FastMCP must resolve which source owns a requested component. Explicit namespacing is generally easier to reason about than depending on collision resolution.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+4



`https://gofastmcp.com/servers/providers/overview`

`https://gofastmcp.com/servers/composition`

`https://gofastmcp.com/servers/providers/proxy`

`https://gofastmcp.com/servers/providers/filesystem`

`https://gofastmcp.com/servers/providers/custom`

## 4. Transforms: adapting agent-facing interfaces independently of implementations

Transforms operate between component providers and clients, allowing a server to modify how its available capabilities are represented or accessed.

They can run at the provider level, affecting a particular source, or at the server level, affecting the combined result. On discovery, components flow outward through the transform chain; on resolution by name, transforms map client-visible requests back toward their underlying component.

Ordering is significant, particularly when combining renaming, search, filtering, and authorization-dependent behavior.

### 4.1 Tool transformation and schema adaptation

`ToolTransform` can change exposed names, descriptions, and parameter interfaces while delegating execution to an underlying tool. `Tool.from_tool()` provides an alternative immediate transformation mechanism.

This permits a single implementation to support multiple presentation contracts, for example a detailed programmatic interface and a narrower agent-facing interface.

It can also avoid writing simple wrapper functions solely to rename or simplify arguments. However, removing or hiding a parameter creates an obligation to supply its value through a trustworthy mechanism; a transformed schema must remain consistent with the underlying callable's requirements.

### 4.2 On-demand tool discovery

FastMCP offers specialized transformations for large tool catalogs.

| Mechanism              | How it works                                                            | Important tradeoff                                                             |
| ---------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `RegexSearchTransform` | Searches names, descriptions, and parameter text using Rust-style regex | Predictable lexical matching, but no semantic understanding                    |
| `BM25SearchTransform`  | Ranks tools using lexical information retrieval                         | Better relevance ranking than literal matching in some catalogs; still lexical |
| `JevSearchTransform`   | Experimental alternative ranking using the optional Jev integration     | Additional dependency and experimental behavior                                |
| `CodeMode`             | Exposes discovery plus sandboxed Python execution to compose tool calls | Fewer model round-trips, but a larger execution/security boundary              |

The search transforms normally expose synthetic `search_tools` and `call_tool` tools instead of returning the entire underlying catalog.

A critical detail is that search transforms control discovery, not authorization. Their documentation explicitly states that original tools remain callable even when omitted from the advertised listing. A caller that already knows a tool's name may still invoke it unless an independent authorization or visibility mechanism prevents that operation.

BM25 and regex search can reduce tool-schema context usage without requiring an embedding service. Whether they improve overall execution depends on the catalog, query phrasing, additional discovery calls, and retrieval precision.

### 4.3 Code Mode — experimental

`CodeMode`, installed with the `code-mode` extra, lets a model discover tool interfaces and write Python that orchestrates multiple underlying tool calls.

The default interface exposes `search`, `get_schema`, and `execute` meta-tools. Discovery can be customized, including more or fewer stages; execution uses a sandbox provider with configurable resource and tool-call limits.

Rather than returning every intermediate result to the LLM, code can pass one result directly into another tool call and return a consolidated answer. This offers a potentially significant reduction in model context transfer and repeated model interactions.

It also changes the trust boundary: model-authored code now participates in tool orchestration. The sandbox's supported operations and configured restrictions determine what is permissible, while all invoked tools still need their own authorization and safety enforcement. FastMCP labels the feature experimental; its discovery interface may change.

### 4.4 Resources and prompts as tools

`ResourcesAsTools` creates `list_resources` and `read_resource`. `PromptsAsTools` creates `list_prompts` and `get_prompt`.

These are useful when the consuming MCP client supports tool calls but not native resources or prompts. The generated tools route operations through the FastMCP server's middleware chain, preserving applicable authorization, rate limiting, and visibility behavior.

This is a protocol-interface compatibility mechanism, not a conversion of all resource or prompt semantics into ordinary computational tools.

### 4.5 Visibility, versioning, and schema fingerprints

FastMCP supports component enable/disable operations by identifier, tag, and related filtering criteria, including session-scoped visibility.

Component versioning is separate from both the FastMCP package version and the negotiated MCP protocol revision. Multiple versions of a component can coexist; `VersionFilter` can expose a selected range to different clients or servers while retaining shared definitions.

For downstream schema drift detection, each component has a canonical identity such as `tool:name@version`, and tools expose their protocol-facing representation through `to_mcp_tool()`. Stable fingerprints can be assembled from identity, input/output schemas, annotations, descriptions, and metadata. The framework exposes the necessary representation; the fingerprint inclusion policy and hashing are application-defined, not a universal built-in contract hash.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+7



`https://gofastmcp.com/servers/transforms/transforms`

`https://gofastmcp.com/servers/transforms/tool-transformation`

`https://gofastmcp.com/servers/transforms/tool-search`

`https://gofastmcp.com/servers/transforms/code-mode`

`https://gofastmcp.com/servers/transforms/resources-as-tools`

`https://gofastmcp.com/servers/transforms/prompts-as-tools`

`https://gofastmcp.com/servers/versioning`

`https://gofastmcp.com/servers/tool-fingerprinting`

## 5. Execution architecture: middleware, lifespans, and state

### 5.1 Middleware and cross-cutting behavior

FastMCP middleware intercepts MCP operations rather than merely intercepting HTTP requests. It therefore applies across the server's transports and the corresponding protocol operations.

Hooks cover discovery and execution: tool calls, resource reads, prompt rendering, component listing, initialization/discovery, messages, and notifications. Middleware can inspect a request, execute logic before or after it, modify results, or reject execution.

Built-in middleware includes facilities for logging, response caching, timing, rate limiting, error handling, and response-size limiting.

This enables cross-cutting behavior without inserting equivalent code into every tool. For example, a caching policy can be applied at the MCP operation boundary rather than separately inside each function.

However, cache correctness depends on whether responses are sensitive to identity, permissions, arguments, underlying state, or time. Neither caching nor rate limiting should be treated as semantically safe merely because middleware supports it.

Middleware ordering is explicit and consequential. Mounted servers can have their own middleware in addition to the parent's chain.

### 5.2 Lifespan management and dependency cleanup

FastMCP supports asynchronous server lifespans for initializing and tearing down long-lived resources: HTTP connection pools, database pools, model clients, registries, and similar infrastructure.

Lifespans compose through mounted servers, and context/dependency mechanisms allow handlers to access resources initialized at startup.

This avoids the two common alternatives of constructing expensive infrastructure on every call or maintaining unmanaged module-global state.

Lifecycle distinctions:

| Scope                | Appropriate state                                        | Expected lifetime           |
| -------------------- | -------------------------------------------------------- | --------------------------- |
| Server lifespan      | Connection pools, service clients, shared registries     | Server instance lifetime    |
| Request context      | Request metadata, transient objects, intermediate values | One operation               |
| Dependency scope     | Injected resources with setup/cleanup                    | Defined dependency lifetime |
| User/session storage | Cross-request application state                          | Storage-controlled          |
| Background task      | Long-running execution and task progress                 | Scheduler-controlled        |

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+2



`https://gofastmcp.com/servers/middleware`

`https://gofastmcp.com/servers/lifespan`

`https://gofastmcp.com/servers/dependency-injection`

### 5.3 Sessionless transport does not imply stateless applications

This is one of FastMCP 4's defining architectural advances.

The MCP `2026-07-28` protocol uses independent requests rather than requiring a persistent session or initialization handshake. This simplifies load balancing because consecutive requests need not reach the same worker.

FastMCP provides separate application-level state mechanisms:

| Mechanism                       | State identity                        | Intended use                                                     |
| ------------------------------- | ------------------------------------- | ---------------------------------------------------------------- |
| Request context state           | Individual request                    | Middleware-to-handler data, intermediate request values          |
| `UserSession`                   | Authenticated user                    | One persistent state namespace per user                          |
| `SessionId` + `SessionProvider` | User plus explicit session identifier | Several carts, conversations, or workflows belonging to one user |
| Generic storage                 | Application-defined keys              | Caches, credentials, arbitrary persistent/shared state           |

`UserSession` is injected into handlers and does not appear in their input schema. It requires an authenticated user identity.

`SessionId` appears as a string argument in the tool schema. `SessionProvider` supplies lifecycle operations such as `create_session`, and `get_session()` resolves and validates the identifier. State exposes asynchronous `get`, `set`, `delete`, and `clear` operations; it stores JSON-serializable values.

The isolation model keys state by authenticated user and then by session identifier. Without authentication, a session identifier cannot provide equivalent tenant isolation: it effectively becomes a bearer handle, so leakage matters.

Retention and expiry are controlled by the configured storage backend rather than by a universal FastMCP session TTL.

### 5.4 Storage backends

FastMCP uses the `py-key-value-aio` ecosystem for general key-value storage. Relevant implementations include memory, filesystem, Redis/Valkey, and further integrations exposed through that companion library.

Shared storage is important when server replicas need consistent session state, OAuth state, or response caches. In-memory storage remains useful for ephemeral or single-process applications.

Different concerns can use different stores. A shared session store does not automatically provide a distributed task queue or atomic domain transactions.

Sensitive OAuth state requires additional attention to encryption at rest and durable key management. FastMCP provides encryption wrappers and production configuration mechanisms, but supplying an arbitrary custom store without equivalent protections can weaken the security boundary.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+1



`https://gofastmcp.com/servers/sessions`

`https://gofastmcp.com/servers/storage-backends`

## 6. Background tasks and multi-request interaction

FastMCP 4 makes a consequential distinction between a Python function running asynchronously and a protocol-visible background task.

### 6.1 MCP background tasks

Background tasks use the `io.modelcontextprotocol/tasks` extension and the separately distributed `fastmcp-tasks` package, powered by Docket.

Installation of `fastmcp[tasks]` supplies the companion package, but server task capability also requires registering `TasksExtension`.

```
from fastmcp import FastMCPfrom fastmcp_tasks import TasksExtensionmcp = FastMCP("Workers")mcp.add_extension(TasksExtension())@mcp.tool(task=True)async def long_operation(job_id: str) -> dict:    ...
```

A compatible client can initiate a task, receive a task identifier, poll for status, obtain progress, cancel supported work, and retrieve the eventual result.

`TaskConfig` distinguishes three execution policies:

- `forbidden`: execute in the foreground.
- `optional`: use background execution when the client opts in; otherwise execute in the foreground.
- `required`: reject calls that do not request task execution.

Only asynchronous tools can be task-enabled; resources and prompts do not accept `task=True`.

An easily overlooked limitation is that an internal tool call made through a search transform or Code Mode's execution layer runs in the foreground. Consequently, an inner tool configured with `task=required` cannot simply be invoked as a background task by those wrappers. Only the external client can initiate the protocol task.

### Distributed execution

The in-memory backend is process-local and ephemeral. Redis/Valkey-backed execution supports external workers and distributed scheduling through Docket. Worker management, task persistence, retry behavior, expiration, and operational durability depend on scheduler configuration, not just the MCP protocol.

For Redis-backed tasks, FastMCP provides optional encryption for stored caller-identity snapshots using `FASTMCP_TASKS_ENCRYPTION_KEY`. The documented protection does not encrypt every persisted task argument or result. Storage-level security must therefore be considered separately.

On the client, the `fastmcp-tasks` companion integration permits transparent task handling through ordinary `call_tool()`, or explicit status and result operations through `call_tool_task()`. Task execution requires negotiation of the modern protocol and the extension capability.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+1



`https://gofastmcp.com/servers/tasks`

`https://gofastmcp.com/clients/tasks`

### 6.2 Elicitation: two different protocol-era models

Elicitation allows an operation to request additional structured information from its user, such as a choice, confirmation, or missing parameter.

Legacy MCP connections (through `2025-11-25`) support `await ctx.elicit(...)`: the tool pauses and awaits a client response over the session backchannel.

Modern connections (`2026-07-28`) removed server-initiated requests. A tool instead returns an `InputRequiredResult` containing one or more `ElicitRequest` objects. The client collects the response and reissues the tool call, with answers in `ctx.input_responses`.

The two models are not interchangeable.

Modern multi-request elicitation has important consequences:

1. The original Python invocation ends when input is requested; the continuation is a fresh invocation.
2. Every round passes through the middleware and authorization pipeline again.
3. Small continuation data can travel in `request_state`; larger or durable data belongs in server-side state.
4. The request sequence can cross replicas, provided its continuation state and storage are configured appropriately.
5. Repeated execution requires particular care around non-idempotent side effects, since a tool's code runs again from the beginning.

Supported elicitation schemas include scalar answers, enumerated choices, confirmations, multi-selects, and structured responses.

### 6.3 Sampling: a major FastMCP 4 breaking change

FastMCP 4 removed `Context.sample()` and `Context.sample_step()`. It also removed the former server-side `sampling_handler` constructor parameters. These methods are not usable by forcing a legacy connection in FastMCP 4.

There are two documented alternatives:

- Call an LLM provider SDK directly from the tool, making generation an ordinary application dependency.
- Return `InputRequiredResult` containing a `CreateMessageRequest` so a modern client can use its own model and return the generated message in the next request.

The second mechanism is appropriate when using the caller's model, identity, or associated billing is genuinely necessary. It introduces an additional request/response cycle and requires compatible clients.

This distinction also explains why older FastMCP sampling examples may be misleading when copied into a FastMCP 4 server.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+1



`https://gofastmcp.com/servers/elicitation`

`https://gofastmcp.com/servers/sampling`

## 7. Authentication, authorization, and identity delegation

FastMCP separates transport-level identity verification from component-level permission checks.

### 7.1 Authentication mechanisms

| Mechanism            | Role                                                             | Relevant constraints                                                           |
| -------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `TokenVerifier`      | Validate externally issued bearer credentials                    | Does not independently provide interactive OAuth issuance                      |
| `JWTVerifier`        | Verify signed JWTs using JWKS or configured keys                 | Issuer, audience, signature, expiry, and key management matter                 |
| Token introspection  | Validate opaque tokens with an upstream service                  | Adds upstream availability and request latency                                 |
| `RemoteAuthProvider` | Integrate MCP discovery with a remote OAuth authorization server | Suited to providers supporting relevant OAuth client-registration capabilities |
| `OAuthProxy`         | Bridge MCP clients to an existing upstream OAuth provider        | Handles registration, callbacks, token exchanges, proxy security and storage   |
| `OIDCProxy`          | OIDC-oriented variation of the proxy pattern                     | Identity-provider-specific discovery and validation                            |
| `OAuthProvider`      | Implement a fuller authorization-server role                     | Greater control and substantially greater security responsibility              |
| `MultiAuth`          | Accept credentials from multiple trusted sources                 | Must resolve identity and claims consistently across issuers                   |

FastMCP includes documented integrations with GitHub, Google, Microsoft Entra ID, Auth0, WorkOS, Keycloak, AWS Cognito, and other identity providers.

Its OAuth integrations cover more than parsing a bearer header: protected-resource metadata, authorization-server discovery, token validation, registered client identities, scopes, callback handling, and relevant OAuth 2.1 mechanisms are part of the supported design space.

These server authentication mechanisms apply to HTTP transports. STDIO normally relies on local process access and environment security rather than the framework's HTTP OAuth system.

### 7.2 Authorization and policy checks

Component authorization uses callable checks that receive an `AuthContext`. Built-in helpers include `require_scopes`, `require_roles`, and `restrict_tag`, alongside custom synchronous or asynchronous checks.

Checks can be attached directly to components or applied globally with `AuthMiddleware`. Unauthorized components can be filtered from discovery responses, and direct invocation is separately checked.

Component visibility, search filtering, and authorization have distinct responsibilities:

- Visibility controls what components a particular caller can encounter or invoke through the applicable visibility layer.
- Search transforms reduce what is advertised during discovery.
- Authorization determines whether an identity is permitted to access a component.

Do not rely on a smaller discovered catalog as a permission boundary.

A consequential transport limitation is documented: component authorization checks relying on HTTP access tokens are skipped for STDIO operations. A deployment mixing HTTP and STDIO must account for this difference at the process and access-control boundary.

### 7.3 OAuth proxies and advanced identity

`OAuthProxy` supports bridging OAuth identity systems whose client-registration behavior does not directly satisfy MCP client expectations. This introduces challenges around redirect URI validation, PKCE, token issuance, forwarded credentials, and confused-deputy risks. FastMCP documents these specifically rather than treating an OAuth proxy as transparent authentication forwarding.

FastMCP 4 also supports identity assertions under SEP-990, a beta on-behalf-of mechanism involving signed ID-JAG assertions. It is intended to permit trusted identity providers to assert an end user's identity to an MCP authorization server, with audience, issuer, client binding, resource binding, expiration, and replay checks.

Because it is explicitly beta, this should be treated as a version-sensitive integration capability, not an immutable stable contract.

On the client side, FastMCP supports browser-based OAuth with PKCE, client ID metadata documents (CIMD), pre-registered clients, client-credentials grants, and `private_key_jwt` authentication. For machine credentials, the documented guidance strongly emphasizes explicitly pinning the expected issuer so credentials are not inadvertently disclosed to a server-advertised malicious authorization endpoint.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+8



`https://gofastmcp.com/servers/auth/authentication`

`https://gofastmcp.com/servers/auth/token-verification`

`https://gofastmcp.com/servers/auth/remote-oauth`

`https://gofastmcp.com/servers/auth/oauth-proxy`

`https://gofastmcp.com/servers/auth/oidc-proxy`

`https://gofastmcp.com/servers/auth/multi-auth`

`https://gofastmcp.com/servers/authorization`

`https://gofastmcp.com/clients/auth/oauth`

`https://gofastmcp.com/clients/auth/client-credentials`

## 8. Client architecture: connecting, discovering, and consuming MCP capabilities

FastMCP includes a substantial client implementation. It is not limited to building servers and is useful both for ordinary Python applications and for frameworks implementing their own agent loops.

`Client` handles transport selection, connection lifecycle, protocol negotiation, authentication, discovery, request execution, result decoding, and selected server-initiated interactions.

### 8.1 Client transports and connection lifecycle

| Transport         | Mechanism                             | Distinguishing properties                                                           |
| ----------------- | ------------------------------------- | ----------------------------------------------------------------------------------- |
| In-memory         | `Client(fastmcp_server)`              | Direct in-process execution; useful for integration tests and embedded applications |
| STDIO             | `StdioTransport` or a Python `Path`   | Launches a subprocess and communicates over pipes                                   |
| Streamable HTTP   | `StreamableHttpTransport` or HTTP URL | Independently deployed services, TLS, OAuth and HTTP infrastructure                 |
| SSE               | `SSETransport`                        | Compatibility with older MCP servers                                                |
| MCP configuration | `Client(config)`                      | Combines declared MCP servers behind an aggregate endpoint                          |

For STDIO, FastMCP forwards a restricted platform-specific environment-variable allowlist rather than implicitly passing every secret from the parent process. Additional environment variables must be supplied explicitly. The transport also supports controlling the subprocess working directory and whether the subprocess is reused through `keep_alive`.

A path should be passed as a `Path`, rather than a bare string: inferring local subprocess execution from a string is deprecated in FastMCP 4 and slated to disappear in FastMCP 5.

Transport inference has a security implication: a caller-supplied configuration dictionary can instruct the client to execute arbitrary local commands. Untrusted server descriptions should therefore be validated and converted into explicit, constrained transports instead of being passed directly to `Client`.

HTTP connections verify certificates through HTTPX2's operating-system trust-store behavior. Updating FastMCP or `certifi` does not necessarily update the CA material used by the actual transport.

### 8.2 Protocol negotiation

By default, FastMCP 4 uses automatic protocol selection.

For modern MCP servers, it uses the discovery-oriented `2026-07-28` protocol. For legacy endpoints, it can fall back to the initialization-handshake model. Explicit `mode="legacy"` is available where older behavior is required.

The two eras have different semantics, not merely different version labels:

| Concern                   | Legacy connection                     | Modern connection                                   |
| ------------------------- | ------------------------------------- | --------------------------------------------------- |
| Connection initialization | Explicit `initialize` handshake       | Discovery-oriented, independent requests            |
| Session lifecycle         | Connection/session state is material  | Sessionless transport                               |
| Elicitation/sampling      | May involve server-initiated requests | Input-required response rounds                      |
| Background tasks          | Older behavior may differ             | Tasks extension, negotiated explicitly              |
| Connection scaling        | Stateful session considerations       | Better suited to independently routed HTTP requests |

The client normalizes much of the application interface across these protocols, but it cannot make removed server-side capabilities behave identically.

### 8.3 `ClientGroup` versus a multi-server `Client`

Introduced in FastMCP 4, `ClientGroup` addresses a subtle limitation of simple client-side aggregation.

`Client(config)` constructs one logical aggregated endpoint. Although its backend servers have individually configured transports, the outer client selects a shared protocol era and shares its handler infrastructure across the aggregation chain.

`ClientGroup`, by contrast, coordinates independent `Client` instances. Each retains its own negotiated protocol version, authentication, transport, handlers, and lifecycle.

```
from fastmcp import Client, ClientGroupgroup = ClientGroup({    "legacy": Client("https://legacy.example.com/sse", mode="legacy"),    "modern": Client("https://modern.example.com/mcp"),})async with group:    tools = await group.list_tools()    result = await group.call_tool("modern_get_status", {})
```

The example illustrates independent client aggregation; the endpoints are placeholders.

Tool names are namespaced by group member. Discovery builds a routing table, and `resolve_tool()` can return the actual owning client and upstream tool name. This is particularly useful for agent framework adapters, which must route follow-up interactions, elicitation, or task polling through the same client that owns a tool.

An explicit `list_tools()` refreshes routes after dynamically changing server catalogs. Connections are reference-counted/reentrant, but `ClientGroup` does not create an additional shared session layer.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP



`https://gofastmcp.com/clients/client-groups`

### 8.4 Results, handlers, and multi-step interactions

Client operations include tool discovery and calls, resource listing and reads, prompt discovery and retrieval, and the corresponding completion and notification capabilities supported by a connected server.

`call_tool()` returns a decoded result whose `data` property is useful for Python consumption; `content` preserves protocol content blocks. For applications needing lower-level MCP details, the client also exposes protocol-level result operations.

Configurable callbacks support:

- Progress notifications, including per-call overrides.
- Server logging messages and notifications.
- User elicitation through an application-supplied handler.
- Client-mediated sampling using the application's model provider.
- Filesystem roots and related client capabilities.

For modern input-required workflows, the client can transparently process intermediate rounds using its configured handlers. `input_required_max_rounds`, defaulting to 10, bounds the number of continuation rounds to avoid an endlessly requesting server.

The client also supports response caching for discovery operations and modern-protocol cache metadata. Caching a component catalog is distinct from caching the results of arbitrary tools, and dynamic provider catalogs need a refresh strategy.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+2



`https://gofastmcp.com/clients/client`

`https://gofastmcp.com/clients/elicitation`

`https://gofastmcp.com/clients/progress`

### 8.5 Lightweight client-only distribution

The `fastmcp-slim[client]` installation exposes the same `fastmcp` import namespace for client use without bringing in the full server framework.

```
pip install "fastmcp-slim[client]"
```

It supports HTTP and STDIO clients, basic protocol operations, and single-server configurations. In-memory `FastMCP` servers, multi-server configurations, and server-side composition features require the full package.

This is a meaningful dependency boundary for SDK authors who need MCP consumption but not MCP server construction.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP



`https://gofastmcp.com/clients/client-only-package`

## 9. MCP Apps: interactive interfaces alongside tools

FastMCP Apps extends the framework beyond tool-call-and-text-response interactions. It implements the MCP Apps extension and uses Prefab to represent reactive interfaces through Python.

An app is still associated with MCP capabilities, but a compatible host renders an interactive interface — a table, chart, form, dashboard, or custom application — rather than presenting only serialized tool output.

```
pip install "fastmcp[apps]"
```

### 9.1 Four application modes

| Mode             | Mechanism                                         | Suitable interaction                                |
| ---------------- | ------------------------------------------------- | --------------------------------------------------- |
| Interactive tool | `@mcp.tool(app=True)` returning Prefab components | Charts, data tables, filters, dashboards            |
| Managed app      | `FastMCPApp`, `@app.ui()`, `@app.tool()`          | Stateful interfaces calling backend tools           |
| Generative UI    | `GenerativeUI()` provider                         | Model-produced UI compositions                      |
| Custom HTML      | MCP Apps resource and app configuration           | Custom browser interfaces and JavaScript frameworks |

The distinction between the first two modes is significant.

An interactive tool can present client-side state and controls without performing a new MCP request for each interaction. A managed app supports `CallTool` actions that invoke backend tools and update reactive UI state with their results.

### 9.2 `FastMCPApp` and composition-safe backend calls

`FastMCPApp` is itself a provider. Its `@app.ui()` functions are user-facing app entry points, while `@app.tool()` functions implement backend operations.

These can carry different visibility metadata: for example, a model discovers a dashboard-opening tool, while the dashboard's own UI can invoke several backend tools without all of them being separately advertised to the model.

Function-reference-based `CallTool` operations resolve through stable identities, protecting UI-to-tool wiring when a server is mounted under a namespace or combined into a gateway.

A critical limitation: app visibility metadata is not an authorization boundary. A client that knows a backend tool name may still attempt to call it directly. Independent server-side authorization and validation must govern any sensitive operation.

### 9.3 Prefab, forms, and ready-made interaction providers

Prefab offers Python-defined components, declarative reactive state, and actions such as state updates, conditional presentation, and backend calls.

FastMCP's app-related providers add capabilities including approval prompts, structured choices, file uploads, and form input. Pydantic models can supply typed form fields and validation constraints.

File-upload workflows are especially useful when the user needs to supply substantial data without sending the entire file through an LLM's textual context. The file's storage, retention, access rights, and downstream validation still require explicit controls.

An approval UI provides a confirmation interaction; it should not be confused with a non-bypassable authorization or transaction-approval policy unless that policy is independently enforced.

### 9.4 Generative UI and custom HTML

`GenerativeUI()` exposes tools that allow a model to discover supported Prefab components and generate an application programmatically. The implementation uses restricted Python execution infrastructure built around Pyodide and related rendering services.

This differs fundamentally from requesting the model to output a JSON table. The generated program defines component composition and interactive behavior, with additional execution and host-compatibility constraints.

Custom HTML apps provide a lower-level option. They involve UI resources, sandboxed rendering, client–app messaging, and browser permissions governed by the MCP Apps extension and the host's implementation.

Compatibility is conditional: an MCP client supporting ordinary tools does not necessarily support interactive MCP Apps. Prefab and host integration are separate dependencies from FastMCP's underlying server protocol.

The `prefab-ui` companion library also evolves rapidly. FastMCP declares a minimum version but not a tight upper bound, so its documentation recommends pinning a known compatible Prefab version for deployed applications.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+4



`https://gofastmcp.com/apps/overview`

`https://gofastmcp.com/apps/fastmcp-app`

`https://gofastmcp.com/apps/prefab`

`https://gofastmcp.com/apps/generative`

`https://gofastmcp.com/apps/low-level`

## 10. Integration with existing APIs, web applications, and agent skills

### 10.1 OpenAPI as a component provider

`FastMCP.from_openapi()` and `OpenAPIProvider` convert OpenAPI-described operations into MCP components. FastMCP delegates the actual HTTP requests to a configured `httpx2.AsyncClient`.

Unlike a one-time code generator, the provider architecture permits OpenAPI-derived capabilities to participate in the same composition and transformation system as local Python tools.

The default is to expose every OpenAPI operation as an MCP tool. This maximizes tool-only client compatibility, but it is not necessarily the best semantic mapping.

`RouteMap` provides ordered rules that match HTTP methods, path patterns, and OpenAPI tags, then classify operations as `MCPType.TOOL`, `RESOURCE`, `RESOURCE_TEMPLATE`, or `EXCLUDE`. Custom mappings take precedence over the default; the first matching rule wins. A `route_map_fn` permits more detailed inspection of operation metadata and can override even an exclusion, so its behavior must be considered part of the exposure policy.

FastMCP also supports customized generated names and tags, plus HTTP request-body mappings including JSON, multipart, and composed request bodies.

Consequential distinction: converting an API into MCP reduces adapter code, but it does not automatically make the API well-suited to agent reasoning. Raw REST APIs may expose excessive implementation detail, numerous parameters, and operations whose side effects are difficult to infer. FastMCP's own documentation recommends curating the agent-facing interface rather than mirroring complex APIs indiscriminately.

Authentication to the upstream API belongs to the configured HTTP client. Authentication to the MCP endpoint is separately governed by FastMCP. The two identities should not be conflated.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP



`https://gofastmcp.com/integrations/openapi`

### 10.2 FastAPI: generating from versus mounting into

FastMCP supports two substantially different FastAPI integrations.

Generate from FastAPI: `FastMCP.from_fastapi(app=...)` derives an MCP server from the application's OpenAPI specification. Existing HTTP endpoint behavior is invoked through the integration's HTTP client.

Mount into FastAPI: `mcp.http_app()` creates an ASGI application that can be mounted alongside ordinary FastAPI routes.

The second approach does not require conversion of any existing HTTP operation into an MCP tool. It is useful when one ASGI process must expose separate application and MCP interfaces.

Lifespan composition matters here. Mounted MCP applications may own resources that must be initialized and closed with the parent ASGI application's lifespan. The documentation includes explicit examples of combining lifespans and using an in-process `StreamingASGITransport` to test mounted endpoints.

FastAPI is not an automatically installed FastMCP dependency.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP



`https://gofastmcp.com/integrations/fastapi`

### 10.3 Agent skills as resources

`SkillProvider` and `SkillsDirectoryProvider` expose instruction packages containing `SKILL.md` and supporting files.

Each skill can expose its main instruction file, a synthetic `_manifest`, and supporting resources under the `skill://` URI scheme.

The manifest includes file sizes and SHA-256 hashes. This allows consumers to inspect a skill's content and check the integrity of downloaded supporting files rather than treating a skill directory as an opaque block.

FastMCP client utilities include `list_skills()`, `get_skill_manifest()`, `download_skill()`, and `sync_skills()`.

This is a different capability from tool execution. A skill packages instructions and supporting knowledge; a tool exposes an operation the client may invoke. The two can coexist, but delivering a skill does not automatically install, trust, approve, or execute its contents.

### Experimental MCP Skills extension

FastMCP 4 also includes an experimental, opt-in extension exposing `skills/list` and `skills/get`.

Its guarantees and limitations are considerably narrower than ordinary resource-based skill serving. The experimental mode introduces stricter frontmatter validation, content hashing, duplicate-name checks, and limits on eligible skill packages. It requires compatible clients and does not currently support transformed, namespaced, mounted, or proxied skill sources.

In particular, the documentation states that it does not implement host-side activation, approval, installation, or execution. The client or host remains responsible for those operations and for verifying content against manifests.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+1



`https://gofastmcp.com/servers/providers/skills`

`https://gofastmcp.com/servers/providers/experimental-skills`

## 11. Deployment, observability, testing, and developer tooling

### 11.1 Serving over STDIO or HTTP

`mcp.run()` defaults to STDIO, while `mcp.run_async()` is available within an existing asynchronous application. Streamable HTTP is the primary network transport; legacy SSE remains supported for compatibility.

An HTTP deployment can be started directly:

```
mcp.run(transport="http", host="127.0.0.1", port=8000)
```

Alternatively, `mcp.http_app()` exposes an ASGI application for Uvicorn, Starlette, FastAPI, or infrastructure controlling its own worker processes.

For the modern protocol, independent requests reduce affinity requirements between clients and HTTP workers. However, that does not make process-local storage shared. Distributed application state, OAuth data, and background tasks still need appropriate external storage or scheduling when their lifecycles cross worker boundaries.

FastMCP includes configurable HTTP paths, custom HTTP routes, health-check integration, HTTP middleware, and reverse-proxy guidance.

### 11.2 Gateway-oriented HTTP features

A less obvious FastMCP 4 capability is protocol-aware HTTP routing metadata.

Modern Streamable HTTP clients can supply:

- `Mcp-Method`, identifying the MCP operation.
- `Mcp-Name`, identifying a requested tool, resource, or prompt.
- `Mcp-Param-*`, exposing explicitly annotated tool arguments as routing headers.

These can help a gateway route requests without first decoding the JSON-RPC body. Parameter-header exposure is opt-in through the `x-mcp-header` JSON Schema extension.

There are two important constraints. Earlier protocol clients do not send these headers, and tool arguments promoted into HTTP headers acquire the security and logging exposure of those headers. Sensitive values should not be casually promoted into intermediary-visible routing data.

FastMCP also provides configurable `Host` and `Origin` validation to mitigate DNS rebinding. It is opt-in, not an unconditional protection enabled by every deployment. This request guard is separate from CORS, and neither substitutes for authentication.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+2



`https://gofastmcp.com/deployment/http`

`https://gofastmcp.com/deployment/running-server`

### 11.3 Declarative configuration with `fastmcp.json`

FastMCP's deployment configuration separates three concerns:

| Configuration section | Responsibility                                       |
| --------------------- | ---------------------------------------------------- |
| `source`              | Where the server implementation is loaded from       |
| `environment`         | Which Python environment and dependencies to prepare |
| `deployment`          | How the server runs                                  |

The currently supported source type is `filesystem`; Git and hosted/cloud source types appear in the documentation as planned, not released configuration backends.

The environment subsystem currently supports `uv`, including Python version and dependency configuration. CLI arguments can override corresponding values in `fastmcp.json`.

A versioned JSON Schema allows IDE validation:

`https://gofastmcp.com/public/schemas/fastmcp.json/v1.json`

This provides a portable deployment definition without making the server's capabilities dependent on a particular shell command.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP



`https://gofastmcp.com/deployment/server-configuration`

### 11.4 OpenTelemetry tracing

FastMCP includes native OpenTelemetry instrumentation covering tool calls, resource reads, prompt operations, task management, and provider delegation.

It depends on the OpenTelemetry API, not an automatically configured telemetry backend. Without an SDK/exporter, instrumentation does not produce externally collected traces.

`FASTMCP_TELEMETRY_MODE` controls three modes:

| Mode               | FastMCP spans | Trace context  |
| ------------------ | ------------- | -------------- |
| `native`           | Enabled       | Propagated     |
| `propagation_only` | Suppressed    | Propagated     |
| `off`              | Suppressed    | Left untouched |

`propagation_only` is useful when another instrumentation layer already owns the MCP spans and duplicate spans would make traces misleading.

The combination of FastMCP, HTTP transports, proxies, and OpenTelemetry provides a route to observing a call across a composed capability surface. But it does not automatically instrument arbitrary external computations or downstream libraries. Those require their own instrumentation or custom spans.

For performance analysis, the native spans are especially useful for distinguishing orchestration, provider delegation, and tool execution boundaries. They should be interpreted as telemetry evidence, not as proof that the underlying tool's computation has been fully profiled.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP



`https://gofastmcp.com/servers/telemetry`

### 11.5 CLI and generated tool interfaces

The `fastmcp` CLI extends beyond launching a server. Its operations include `run`, `list`, `call`, `inspect`, `discover`, developer inspection, application preview, authentication utilities, and editor/assistant installation commands.

Two capabilities are particularly useful for reducing auxiliary tooling:

Server discovery and introspection. `fastmcp list`, `inspect`, and `call` work against supported local or remote server specifications and existing MCP configurations. The CLI can discover named servers configured in environments such as Claude Code, Cursor, and other supported clients.

Generated typed CLIs. `fastmcp generate-cli` reads an MCP server's tool schemas and produces a Python CLI using Cyclopts. Tool names become subcommands; JSON Schema metadata becomes argument types, descriptions, defaults, and required flags. Complex values can be accepted as JSON arguments.

It also generates a `SKILL.md` describing the CLI commands, allowing coding agents to use the generated command-line interface without reconstructing invocation syntax.

The output is a client script, not a replacement server implementation. It still connects to the MCP server when invoked. This is a noteworthy example of reusing MCP schemas to avoid maintaining a second, manually defined operational interface.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+1



`https://gofastmcp.com/cli/overview`

`https://gofastmcp.com/cli/generate-cli`

### 11.6 Testing

`Client(mcp)` supports in-process integration tests without opening network ports. Through this client, tests exercise MCP discovery, argument validation, result serialization, middleware, and the registered handlers.

`pytest-asyncio` provides the async test infrastructure. The documentation also discusses snapshot-based assertions for component metadata and structured results.

For transport-specific behavior, an in-process client is not a complete substitute for HTTP/ASGI or subprocess tests. Authentication, origins, TLS, routing headers, worker state, and process isolation are properties of those boundaries.

A layered test approach can therefore use the same client API against several transports rather than maintaining entirely separate test utilities.

Sources:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP

+1



`https://gofastmcp.com/servers/testing`

### 11.7 The `fastmcp-remote` companion utility

`fastmcp-remote` is a separately distributed STDIO-to-remote-MCP bridge.

It allows a host that can launch local STDIO servers to communicate with a remote HTTP MCP endpoint. The utility handles upstream connection, optional OAuth authentication, TLS configuration, request forwarding, and associated credentials.

A typical invocation is:

```
uvx fastmcp-remote https://example.com/mcp
```

This is a compatibility tool, rather than a replacement for FastMCP's native HTTP client or in-process server proxy.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP



`https://gofastmcp.com/clients/fastmcp-remote`

## 12. Protocol extensions and custom framework behavior

FastMCP 4's `ServerExtension` API deserves separate attention from ordinary middleware and providers.

A provider introduces or resolves components. Middleware intercepts existing operations. A server extension can introduce an additional negotiated protocol capability.

Extensions declare reverse-DNS-style identifiers, advertise capability settings, register custom JSON-RPC request methods, and intercept tool calls.

An extension is registered using `mcp.add_extension(...)`. Its capabilities are advertised to clients, which can opt in through the modern protocol's request metadata.

Extensions cannot silently assume that registration implies client consent. A custom extension changing request behavior must inspect the caller's negotiated/advertised capabilities and enforce its own opt-in semantics.

### 12.1 Tool-call interception

Extensions can intercept `tools/call` at a stage after the normal middleware chain and before execution.

This permits protocol-level behavior that is not naturally modeled as a conventional wrapper function: background execution, protocol-level result negotiation, or specialized operation dispatch.

Unlike a component transform, this interception need not alter the public tool's declaration.

### 12.2 Provider-bundled extensions

New in FastMCP 4.1, providers may declare required extensions through `required_extensions()`.

Extensions opting into `auto_register` can accompany providers through composition, mounting, and transformations. Explicitly configured extensions take precedence when an identifier conflicts.

This is a significant architectural mechanism: a provider can supply not only a family of components but also the protocol-level features required to consume them.

It does not mean every extension is safe to register automatically. The tasks extension, for example, starts execution infrastructure and remains explicitly registered by default.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP



`https://gofastmcp.com/servers/extensions`

## 13. Version, packaging, and compatibility boundaries

| Concern                    | FastMCP 4.1.3 status                                                 |
| -------------------------- | -------------------------------------------------------------------- |
| Release                    | Stable, published October 20, 2026                                   |
| Python                     | Requires Python 3.10 or newer                                        |
| License                    | Apache 2.0                                                           |
| Core package               | `fastmcp`, backed by the version-matched `fastmcp-slim` distribution |
| Protocol dependency        | MCP Python SDK v2                                                    |
| Modern protocol            | MCP `2026-07-28`, with legacy compatibility                          |
| Schema validation          | Pydantic 2, with minimum 2.12 for FastMCP 4                          |
| HTTP stack                 | Includes HTTPX2 and modern Starlette integration                     |
| Background task support    | Separate `fastmcp-tasks` companion via the `tasks` extra             |
| Apps                       | Optional `apps` extra; Prefab is a separate evolving dependency      |
| Tool Code Mode             | Optional `code-mode` extra; experimental                             |
| Jev search                 | Optional `jev` extra; experimental                                   |
| Client-only distribution   | `fastmcp-slim[client]`                                               |
| TypeScript support         | Separate `@prefecthq/fastmcp-ts` package                             |
| Managed enterprise gateway | Prefect Horizon, a separate service/product                          |

The PyPI distribution also advertises optional extras for Anthropic, OpenAI, Gemini, and Azure integrations. Their presence does not imply that FastMCP itself provides those model inference services.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI



### Important FastMCP 3 → 4 distinctions

The current major release introduces more than ordinary renamed APIs.

Official SDK boundary: importing `FastMCP` from `mcp.server.fastmcp` refers to the older SDK-integrated FastMCP lineage, not the modern standalone package's `from fastmcp import FastMCP`.

Type/model changes: SDK v2 places protocol models in `mcp_types`, re-exported via `mcp.types`, and uses Pythonic `snake_case` attributes. A compatibility layer supports older camelCase access with deprecation warnings; the JSON wire format continues to use its defined protocol field names.

HTTP dependency changes: the stack uses `httpx2`, and code directly interacting with underlying HTTP clients may need adjustments.

Framework dependency floors: Pydantic 2.12 or newer is required. The server extra raises Starlette's minimum to 1.0.1. FastAPI integrations must use a sufficiently recent FastAPI release to permit Starlette 1.x; the upgrading guide identifies FastAPI 0.133.0 as the first compatible release in that respect.

Protocol-era changes: old server-side sampling methods were removed, elicitation must account for independent request rounds, and background execution is supplied through the tasks extension.

These distinctions are especially important because examples indexed from FastMCP 2 and 3 can remain superficially plausible while no longer matching a version 4 runtime.

Source:&#x20;

[image](https://www.google.com/s2/favicons?domain=https://gofastmcp.com\&sz=32)

FastMCP



`https://gofastmcp.com/getting-started/upgrading/from-fastmcp-3`

`https://gofastmcp.com/getting-started/whats-new`

### FastMCP 4.1.3 release-specific changes

Version 4.1.3 includes fixes for public-client OAuth behavior, empty session visibility selections, generator-based tool transformations, ordinary request timeouts in multi-server configurations, and tool-raised `TimeoutError` classification.

It also tightens `certifi` requirements for affected dependencies following the October 2026 eMudhra CA incident. The upstream release explicitly warns that updating the Python package alone does not update all operating-system, container, installer, or custom trust stores.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



`https://github.com/PrefectHQ/fastmcp/releases/tag/v4.1.3`

## 14. Architectural implications and capability combinations

FastMCP's greatest architectural value comes from combining its mechanisms rather than adopting them independently.

| Problem shape                                       | Relevant native combination                                        | What can become simpler                                              | Remaining boundary                                                 |
| --------------------------------------------------- | ------------------------------------------------------------------ | -------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Large, changing tool catalog                        | Dynamic providers + transforms + BM25/regex search + authorization | Tool discovery and interface management                              | Search is not access control; catalog freshness still matters      |
| Several independent capability services             | Local mounts + proxy providers + namespaces + middleware           | A unified MCP surface without combining implementations              | Availability, identity propagation, latency and failure isolation  |
| Typed programmatic agent access                     | Pydantic tool contracts + structured results + `ClientGroup`       | Custom protocol adapters and manual argument/result processing       | Domain schemas and agent orchestration logic                       |
| Existing HTTP applications                          | OpenAPI/FastAPI providers + route maps + tool transforms           | Duplicated HTTP-to-MCP wrappers                                      | Well-designed agent semantics and upstream API security            |
| Multi-step user workflows                           | User/session state + elicitation + input-required continuations    | Custom session protocol and callback plumbing                        | Idempotency, durable state, authorization across rounds            |
| Long-running distributed operations                 | Tasks extension + Docket + Redis/Valkey + telemetry                | Protocol-visible jobs, status, cancellation, and worker coordination | Scheduler operations, task durability policies and domain rollback |
| Human-in-the-loop interfaces                        | `FastMCPApp` + Prefab forms + backend tools                        | Separate dashboard/tool wiring and duplicate form definitions        | Host support, application security and UI dependency stability     |
| Tooling shared with coding agents                   | Tool schemas + `generate-cli` + generated `SKILL.md`               | Hand-authored CLI argument schemas and tool documentation            | Schema fidelity, generated artifact maintenance, credentials       |
| Capability bundles needing custom protocol features | Providers + `required_extensions()` + `ServerExtension`            | Ad hoc protocol forks and manual extension wiring                    | Explicit protocol negotiation and interoperability                 |

Several conclusions follow.

### 14.1 A capability can have several interfaces without several implementations

A function can be registered once, exposed through an MCP tool schema, accessed through a Python client, made available through a composed server, and represented in a generated CLI.

Transforms and app providers can create additional presentation contracts.

That can reduce duplicated validation and interface code, provided the underlying function remains the authoritative implementation and its exposed contracts are kept consistent.

### 14.2 Discovery efficiency and execution efficiency are different objectives

Search transforms, version filters, and selective component exposure primarily reduce discovery complexity and model-facing schema volume.

Code Mode can additionally reduce model round-trips by composing tool calls inside one sandboxed execution.

Pagination reduces the size of each component-list response but does not, by itself, reduce the total catalog consumed by the high-level FastMCP client, which fetches all pages automatically.

These mechanisms address different costs. They should not be assumed interchangeable, nor should their benefits be expressed as universal latency improvements without workload measurements.

### 14.3 Stateful workflows can remain compatible with stateless transport

User/session storage provides application continuity. Input-required rounds provide protocol-level continuity without holding a server request open. Background tasks provide durable-operation semantics when supported by an external scheduler.

The combination makes multi-stage workflows feasible across independently routed HTTP requests. It does not eliminate application obligations around state transitions, retries, duplicate effects, authorization, or transactional consistency.

### 14.4 FastMCP is a protocol and application framework, not a replacement for application infrastructure

FastMCP provides MCP component abstractions, protocol handling, discovery, authorization hooks, interface transformations, clients, and orchestration integration.

It does not itself replace a database, distributed transaction coordinator, numerical execution engine, scheduler backend, identity provider, or model inference system. Its integrations reduce the work of exposing and coordinating those capabilities through MCP.

That separation is what makes FastMCP suitable for thin and composable interfaces, but it is also why its built-in guarantees must not be extended beyond their documented boundaries.

## Primary documentation for continued investigation

The following are especially useful entry points for advanced research without relying on introductory examples:

| Topic                                 | Direct URL                                                 |
| ------------------------------------- | ---------------------------------------------------------- |
| Complete official documentation index | `https://gofastmcp.com/llms.txt`                           |
| Full concatenated documentation       | `https://gofastmcp.com/llms-full.txt`                      |
| Server SDK API reference              | `https://gofastmcp.com/python-sdk/fastmcp-server-server`   |
| Provider abstraction                  | `https://gofastmcp.com/servers/providers/overview`         |
| Component transformation              | `https://gofastmcp.com/servers/transforms/transforms`      |
| Tool discovery and search             | `https://gofastmcp.com/servers/transforms/tool-search`     |
| Authorization model                   | `https://gofastmcp.com/servers/authorization`              |
| Server extension API                  | `https://gofastmcp.com/servers/extensions`                 |
| Background tasks                      | `https://gofastmcp.com/servers/tasks`                      |
| Session management                    | `https://gofastmcp.com/servers/sessions`                   |
| Client groups                         | `https://gofastmcp.com/clients/client-groups`              |
| OpenTelemetry                         | `https://gofastmcp.com/servers/telemetry`                  |
| Tagged 4.1.3 source                   | `https://github.com/PrefectHQ/fastmcp/tree/v4.1.3`         |
| 4.1.3 release notes                   | `https://github.com/PrefectHQ/fastmcp/releases/tag/v4.1.3` |

Overall characterization: FastMCP 4.1.3 is best understood as a composable MCP application framework with a unified component, client, and extension model. Its advanced differentiators are dynamic providers, protocol-aware composition, adaptable tool interfaces, independent client aggregation, identity-aware authorization, multi-request stateful interaction, extension-based background execution, and interactive apps. These capabilities allow MCP to function as a structured application interface rather than merely a collection of Python functions exposed to an LLM.