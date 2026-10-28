# Advanced Python Library Reference: markdown-it-py, mdit-py-plugins, and Jinja2

Research date: October 28, 2026 · Audience: Advanced Python engineers and autonomous programming agents · Scope: Current stable releases

## 1. Library scope and architectural relationships

| Library         | Verified stable version | Primary responsibility                                                                                                 |
| --------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| markdown-it-py  | 4.2.0 (May 7, 2026)     | CommonMark parsing, structural tokens, configurable parsing rules, rendering, and syntax-extension infrastructure      |
| mdit-py-plugins | 0.6.1 (May 13, 2026)    | Additional Markdown dialects, semantic constructs, metadata, mathematical syntax, and specialized parsing rules        |
| Jinja2          | 3.1.6 (March 5, 2025)   | Compiled template evaluation, inheritance, composition, transformation, rendering, and template-language extensibility |

Versions verified against PyPI and upstream releases.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+4



These libraries implement three distinct but complementary forms of document processing:

- markdown-it-py — structural interpretation: Converts Markdown source into a rule-driven token representation, preserving useful syntax, nesting, and positional information. HTML generation is a downstream operation rather than the only output.
- mdit-py-plugins — syntax and semantic specialization: Extends the parser with features such as footnotes, definition lists, attribute annotations, mathematical expressions, directives, and GitHub-flavored constructs. Some extensions create semantically meaningful tokens rather than merely adding HTML formatting.
- Jinja2 — programmable document generation: Compiles templates into Python execution machinery, providing conditional evaluation, iteration, reusable components, inheritance, filters, custom language constructs, asynchronous rendering, and caching.

The consequential architectural distinction is that Markdown parsing, template evaluation, and HTML rendering are separable operations.

A system can generate Markdown with Jinja2, parse it with markdown-it-py, transform the resulting tokens with plugins or custom rules, and render the result using standard or specialized renderers. Alternatively, structured document data can be processed independently and supplied directly to templates.

Neither Markdown parser is a template engine, and Jinja2 does not provide a CommonMark parser. They also do not jointly provide a complete document-object model, reversible Markdown serialization, a general-purpose sanitizer, or a full document-conversion framework.

The sections below concentrate on the native mechanisms and combinations that are most useful to recognize when designing sophisticated document-processing infrastructure.

## 2. markdown-it-py 4.2.0 — parsing, token semantics, and extensibility

### 2.1 Parsing architecture and rule execution

The parser is organized around three cooperating rule engines, each with a separate state object and configurable rule order.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://markdown-it-py.readthedocs.io\&sz=32)

markdown-it-py+2



| Engine             | Principal responsibility                                                                    | Advanced extension mechanisms                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `md.core`          | Document normalization, block/inline orchestration, document-wide postprocessing            | Transform complete token sequences; rewrite references; apply global normalization or annotation                  |
| `md.block`         | Recognize paragraphs, lists, headings, blockquotes, references, HTML blocks, tables, fences | Add or replace block syntaxes, control precedence and paragraph interruption, recursively tokenize nested content |
| `md.inline`        | Recognize links, images, delimiters, escapes, emphasis, inline HTML, entities               | Add tokenizers, register delimiter characters, control parsing priority and silent lookahead                      |
| `md.inline.ruler2` | Secondary processing of inline token sequences                                              | Resolve paired delimiters, perform emphasis processing, normalize intermediate fragments                          |

Consequential mechanisms:

- `Ruler.before()`, `.after()`, `.push()`, and `.at()` provide explicit rule ordering, insertion, and replacement. This is substantially more capable than a post-render regex substitution because a new rule participates in the Markdown grammar itself.
- Rule options support `alt` chains. For block extensions, correct registration determines whether syntax may interrupt an existing paragraph or be recognized in nested block contexts.
- Block rules receive `(state, startLine, endLine, silent)`; inline rules receive `(state, silent)`. The `silent` contract allows recognition/lookahead without emitting tokens or otherwise performing normal parsing mutations.
- Core rules run over the complete document state, making them suitable for cross-token behavior such as resolving references, altering document structure, and generating metadata. Their placement relative to inline parsing and text joining determines which intermediate token representations remain available.
- `ParserInline.add_terminator_char()` (introduced in 4.1) registers characters that must interrupt the fast plain-text rule, allowing new inline syntax to be recognized without replacing the text scanner. This is particularly valuable for uncommon delimiters in custom Markdown dialects.
- `make_fence_rule()` (introduced in 4.2) parameterizes block-fence recognition with `markers`, `token_type`, `exact_match`, `disallow_marker_in_info`, and `min_markers`. Exact-match closing fences can support nested constructs differentiated by fence length; the resulting token still contains literal fenced content unless other processing is added.&#x20;

  [image](https://www.google.com/s2/favicons?domain=https://markdown-it-py.readthedocs.io\&sz=32)

  markdown-it-py+3



Parsing is composable but rule order is semantically significant. Two individually valid plugins can conflict over the same delimiter, block-opening marker, or token transformation phase. Changing registration order may affect not only HTML output but also which tokens exist for later analysis.

### 2.2 Configurable Markdown dialects

| Preset / configuration | Behavior and architectural significance                                                                                                                                              |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `commonmark`           | Default; CommonMark baseline including raw HTML. Suitable for trusted content but not safe by default for user-generated HTML output.                                                |
| `js-default`           | Closely follows the JavaScript markdown-it default, disabling raw HTML while enabling useful extensions such as tables and strikethrough.                                            |
| `zero`                 | Minimal paragraph/text parsing; useful when constructing tightly controlled custom dialects without inheriting most built-in syntax.                                                 |
| `gfm-like`             | Enables GitHub-style features such as tables, strikethrough, and URL autolinking; requires `linkify-it-py`.                                                                          |
| `gfm-like2`            | Adds task lists, GitHub-style alerts, and single-tilde strikethrough to the preceding preset; released in 4.1. It is not a claim of complete GitHub Flavored Markdown compatibility. |
| Custom rule set        | Construct a constrained or domain-specific grammar through `.enable()`, `.disable()`, `.use()`, ruler modifications, and parser options.                                             |

Additional configuration includes `html`, `linkify`, `typographer`, `quotes`, `breaks`, `xhtmlOut`, `langPrefix`, `highlight`, and `maxNesting`. The typographic replacement and smart-quote rules can alter text semantics; they are therefore not appropriate for every source-preservation workload. `maxNesting` is a parser-depth protection, not a complete resource-consumption limit.

`get_active_rules()` and `get_all_rules()` expose the actual grammar configuration for introspection. `reset_rules()` temporarily restores the enabled rule set after a scoped modification. Distinct persistent parser configurations are generally preferable to repeatedly reconfiguring one shared instance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://markdown-it-py.readthedocs.io\&sz=32)

markdown-it-py+2



### 2.3 Token representation, structural analysis, and metadata

`MarkdownIt.parse()` produces a flat block-token sequence, with inline content represented by child token arrays. `parseInline()` bypasses block parsing. `render()` and `renderInline()` combine parsing and rendering.

The `Token` data structure exposes:

| Field / operation                            | Importance                                                                                                         |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `type`, `tag`, `nesting`                     | Structural identity and open/close boundaries (`1`, `0`, `-1`)                                                     |
| `level`, `children`                          | Nesting context and subordinate inline tokens                                                                      |
| `map`                                        | Source line range, generally a zero-based, end-exclusive pair; not a comprehensive character-level source map      |
| `content`, `markup`, `info`                  | Text content, original syntax marker, and additional syntax data such as fence language information                |
| `attrs`                                      | Ordered HTML attribute mapping; used for attributes, links, anchors, and output annotations                        |
| `meta`                                       | Arbitrary plugin/application metadata without forcing it into rendered HTML                                        |
| `block`, `hidden`                            | Block/inline distinction and suppressed output structures, including tight-list paragraph wrappers                 |
| `attrGet`, `attrSet`, `attrJoin`, `attrPush` | Token-level attribute manipulation                                                                                 |
| `as_dict()`, `from_dict()`                   | Token serialization and reconstruction, including compatibility with upstream markdown-it attribute representation |

[image](https://www.google.com/s2/favicons?domain=https://markdown-it-py.readthedocs.io\&sz=32)

markdown-it-py+1

Several advanced uses follow from this structure:

- Semantic extraction: Detect headings, hierarchical lists, links, images, tables, code fences, blockquotes, and extension-specific constructs without interpreting HTML.
- Document transformation: Apply structural rewrites before rendering—for example, annotate links, alter heading attributes, collect references, or attach domain metadata.
- Source-oriented diagnostics: Associate many block constructs with originating line ranges. However, reliable exact character spans, source-preserving edits, and lossless formatting reconstruction require supplementary machinery.
- Interchange: Serialize tokens for separate processing stages. Plugin-defined `meta` values may require custom serialization; a serialized token stream is not a complete document schema by itself.
- Reference preservation: The `inline_definitions` and `store_labels` options can retain additional information about reference definitions useful for source-oriented analysis. They improve preservation but do not make all Markdown transformations fully reversible.

`markdown_it.tree.SyntaxTreeNode` supplies a Python-specific higher-level structural view, collapsing matching opening/closing tokens into nodes. It supports hierarchical access, children and sibling traversal, and inspection without requiring every consumer to maintain its own token-stack algorithm.

This creates a useful distinction between flat tokens for transformation and rendering and tree nodes for structural queries. The tree is a representation of parsed Markdown, not a replacement for a fully lossless concrete syntax tree.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://markdown-it-py.readthedocs.io\&sz=32)

markdown-it-py+1



### 2.4 Renderer extensibility and non-HTML outputs

The HTML renderer dispatches on token type, separating syntax recognition from output generation.

- `md.add_render_rule(token_type, callback, fmt="html")` registers rendering behavior. The callback operates on the token sequence, index, options, and environment, and is bound to the renderer instance.
- `RendererHTML` can be subclassed to change handling of individual token families such as links, fences, images, or emphasis.
- `renderer_cls` allows an entirely different renderer implementation. `RendererProtocol` provides the integration contract, while the renderer's `__output__` setting permits output-format-specific rule registration.
- `renderToken()` provides generic opening/closing-tag behavior, including attributes; `renderAttrs()` handles HTML attribute serialization.
- The `highlight` option supplies a code-fence highlighting hook. Its returned HTML has an explicit escaping contract; it must not be assumed safe merely because it is produced by a callback.

A custom renderer can target structured representations, specialized markup, plain-text extraction, or a different presentation format. However, creating a renderer does not automatically solve semantic issues such as cross-reference resolution or lossless Markdown regeneration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://markdown-it-py.readthedocs.io\&sz=32)

markdown-it-py+3



### 2.5 Parser state, integration, and correctness boundaries

The `env` mapping is a first-class cross-rule communication mechanism. It carries reference definitions, plugin state, accumulated metadata, and caller-supplied values through parsing and rendering. Unlike Jinja2's `Environment`, it is essentially a per-document mutable mapping rather than a compiled template configuration.

This supports document-level indexes and cross-token coordination without introducing separate global registries. It also means reuse of an `env` between unrelated documents can accidentally mix metadata unless that behavior is intentional.

URL processing includes `normalizeLink()`, `normalizeLinkText()`, and `validateLink()`. Link destination handling and dangerous-protocol restrictions are part of the parser, but they do not constitute general HTML sanitization. The default `commonmark` configuration permits raw HTML. For untrusted web content, disabling raw HTML or using an appropriate sanitizer remains essential; custom renderers and attribute plugins can create additional output hazards.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://markdown-it-py.readthedocs.io\&sz=32)

markdown-it-py+1



Performance characteristics: The architecture minimizes unnecessary processing through rule-specific recognition and a fast inline text path; recent releases have also fixed specific quadratic-complexity cases involving reference parsing and token joining. These improvements should not be interpreted as a blanket linear-time or denial-of-service guarantee for arbitrary plugins, nesting, or adversarial inputs.

Native boundaries: No built-in general-purpose Markdown formatter, complete CSS/HTML sanitizer, citation manager, schema validator, or automatic incremental parsing model is implied by the parser architecture. Those are separate concerns even when token-level hooks make them possible to implement.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Primary sources: versioned usage and architecture [https://markdown-it-py.readthedocs.io/en/v4.2.0/using.html](https://markdown-it-py.readthedocs.io/en/v4.2.0/using.html?utm_source=chatgpt.com) · [https://markdown-it-py.readthedocs.io/en/v4.2.0/architecture.html](https://markdown-it-py.readthedocs.io/en/v4.2.0/architecture.html?utm_source=chatgpt.com) · API [https://markdown-it-py.readthedocs.io/en/v4.2.0/api/markdown_it.html](https://markdown-it-py.readthedocs.io/en/v4.2.0/api/markdown_it.html?utm_source=chatgpt.com) · token and tree APIs [https://markdown-it-py.readthedocs.io/en/v4.2.0/api/markdown_it.token.html](https://markdown-it-py.readthedocs.io/en/v4.2.0/api/markdown_it.token.html?utm_source=chatgpt.com) · [https://markdown-it-py.readthedocs.io/en/v4.2.0/api/markdown_it.tree.html](https://markdown-it-py.readthedocs.io/en/v4.2.0/api/markdown_it.tree.html?utm_source=chatgpt.com) · released changes [https://github.com/executablebooks/markdown-it-py/blob/v4.2.0/CHANGELOG.md](https://github.com/executablebooks/markdown-it-py/blob/v4.2.0/CHANGELOG.md?utm_source=chatgpt.com)

## 3. mdit-py-plugins 0.6.1 — dialect extensions and semantic constructs

The package supplies independently composable plugins for `MarkdownIt.use()`. It does not introduce a separate parser: its block, inline, core, and rendering rules participate in the same execution machinery described above.

### 3.1 Capability inventory

| Capability              | Plugin entry point                                       | Advanced behavior and distinctions                                                                                                                                                                                |
| ----------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GitHub-style dialect    | `gfm.gfm_plugin`                                         | Composite configuration enabling tables, single/double-tilde strikethrough, autolinks, task lists, alerts, and footnote references; optionally math and front matter. Modifies the existing parser configuration. |
| GFM autolinks           | `gfm_autolink.gfm_autolink_plugin`                       | Recognizes bare `www.`, HTTP(S), `mailto:`, `xmpp:`, and email patterns. Distinct from the core's optional `linkify-it-py` integration; requires markdown-it-py 4.1+.                                             |
| Front matter            | `front_matter.front_matter_plugin`                       | Recognizes leading `---` metadata blocks; preserves the body for downstream interpretation. Does not itself provide a validated YAML object model.                                                                |
| Footnotes               | `footnote.footnote_plugin`                               | Reference definitions, inline footnotes, numbering, document-tail relocation, backlinks, and shared state through `env`.                                                                                          |
| Definition lists        | `deflist.deflist_plugin`                                 | Pandoc-style term/definition syntax, multiple definitions per term, and multiline/nested block bodies.                                                                                                            |
| Field lists             | `field_list.fieldlist_plugin`                            | reStructuredText-style named fields with inline markup in field names and multiline or nested bodies.                                                                                                             |
| Task lists              | `tasklists.tasklists_plugin`                             | Converts Markdown list-item checkboxes into HTML controls; controls editability and label placement.                                                                                                              |
| Heading anchors         | `anchors.anchors_plugin`                                 | Generates heading IDs, configurable slugs and heading ranges, optional permalinks and their placement.                                                                                                            |
| Word counts             | `wordcount.wordcount_plugin`                             | Collects text statistics into `env`; supports custom counting functions, reading-time assumptions, and optional retained text.                                                                                    |
| Custom containers       | `container.container_plugin`                             | Named, recursively parsed block containers with custom marker, validation, and rendering behavior.                                                                                                                |
| Admonitions             | `admon.admon_plugin`                                     | Python-Markdown/MkDocs-style callouts, including collapsible variants.                                                                                                                                            |
| Inline attributes       | `attrs.attrs_plugin`                                     | Inline attribute declarations attached to recognized elements; optional spans; attribute allowlists.                                                                                                              |
| Block attributes        | `attrs.attrs_block_plugin`                               | Standalone attribute blocks applied to subsequent blocks, including stacked/merged attributes.                                                                                                                    |
| Dollar mathematics      | `dollarmath.dollarmath_plugin`                           | Inline/display mathematics, configurable delimiter ambiguity, equation labels, and custom math rendering.                                                                                                         |
| TeX mathematics         | `texmath.texmath_plugin`                                 | Alternative configurable mathematics delimiters and TeX-style wrappers.                                                                                                                                           |
| AMS math environments   | `amsmath.amsmath_plugin`                                 | Recognizes top-level LaTeX AMS environments without requiring an additional Markdown math fence.                                                                                                                  |
| Subscript / superscript | `subscript.sub_plugin`, `superscript.superscript_plugin` | Compact inline scientific typography using tilde and caret delimiters.                                                                                                                                            |
| MyST roles              | `myst_role.myst_role_plugin`                             | Recognizes inline semantic-role syntax for downstream MyST/Sphinx interpretation.                                                                                                                                 |
| MyST blocks             | `myst_blocks.myst_block_plugin`                          | Recognizes additional MyST block constructs, including explicit targets and comments.                                                                                                                             |
| Colon fences            | `colon_fence.colon_fence_plugin`                         | Colon-delimited fenced blocks with literal contents, analogous to code fences rather than recursively parsed containers.                                                                                          |
| Substitutions           | `substitution.substitution_plugin`                       | Recognizes substitution placeholders as inline or block tokens; leaves their resolution to subsequent processing.                                                                                                 |

The last two capabilities are present in the released 0.6.1 source tree even though they receive less attention in the published reference documentation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mdit-py-plugins.readthedocs.io\&sz=32)

mdit-py-plugins+6



### 3.2 Footnotes: cross-document semantics and structural rewriting

`footnote_plugin(inline=True, move_to_end=True, always_match_refs=False)` is among the most architecturally significant plugins because it is not just a local syntax recognizer.

Its rules cooperate across phases:

1. Block rules recognize labeled definitions and their nested content.
2. Inline rules recognize references and optional inline footnotes.
3. `env["footnotes"]` stores reference mappings and data associated with numbered footnotes.
4. A core tail rule can relocate referenced definitions to the end of the token stream.
5. Render rules create references, numbered footnote sections, and backlinks.

`move_to_end=False` changes the token-processing model by retaining definitions near their source positions instead of appending the rendered footnote section. `always_match_refs=True` changes handling of references without recognized definitions, which can matter when another layer resolves them later.

Footnote tokens include reference, definition, opening/closing, and anchor constructs; metadata associates references with IDs and repeated occurrences. The renderer also supports a document identifier from `env["docId"]` to help distinguish anchors when rendered fragments are combined.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



Important implication: A rendered document's footnote ordering and location may no longer reflect the original Markdown source ordering. Systems doing source diagnostics, structural diffing, or exact-location transformations should account for the transformation phase rather than treating final token order as source order.

### 3.3 Attribute systems: structural annotations rather than mere styling

`attrs_plugin` supports annotations such as `{#identifier .class key=value}` on specified inline constructs. Significant controls include `after`, `spans`, `span_after`, and `allowed`.

- `after` determines which inline token types may receive attributes; by default images, inline code, closing links, and closing spans are supported.
- `spans=True` introduces explicitly attributed text spans. Markdown reference links have parsing precedence over span syntax.
- Multiple attribute groups can be merged; classes accumulate, and repeated IDs have replacement behavior.
- The plugin does not generically attach attributes to arbitrary emphasis, strikethrough, or plain-text tokens, because those constructs require different postparse handling.

`attrs_block_plugin` applies standalone attribute declarations to the next block element. Stacked declarations accumulate classes while later assignments override earlier values for other keys. It combines block recognition with a core rule that resolves and removes the temporary attribute tokens.

The `allowed` option is particularly important: attributes outside the allowlist are omitted from rendered attributes and retained under token metadata such as `insecure_attrs`. This makes it possible to inspect rejected source annotations without treating them as permitted HTML. It is not equivalent to a complete security policy covering URL schemes, IDs, classes, and downstream renderers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mdit-py-plugins.readthedocs.io\&sz=32)

mdit-py-plugins+1



### 3.4 Mathematical syntax: recognition versus actual typesetting

The three math plugins support different input grammars rather than forming one interchangeable implementation.

| Feature             | `dollarmath_plugin`                                                                 | `texmath_plugin`                                       | `amsmath_plugin`                        |
| ------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------ | --------------------------------------- |
| Input orientation   | Dollar-delimited inline/display math                                                | Selectable delimiter conventions                       | Top-level AMS math environments         |
| Key controls        | `allow_space`, `allow_digits`, `allow_blank_lines`, `double_inline`, `allow_labels` | Delimiter mode and macros                              | Custom renderer                         |
| Equation labeling   | Optional labeled block expressions and label normalization                          | Depends on syntax/renderer                             | Not a general label resolver            |
| Output model        | Math tokens plus HTML wrappers and configurable renderer                            | Syntax-specific math rendering                         | Environment-aware math content          |
| Principal advantage | Fine-grained ambiguity control and flexible rendering integration                   | Supports alternative mathematical Markdown conventions | Accepts existing TeX environment syntax |

`dollarmath_plugin` additionally exposes `renderer(content, {"display_mode": bool})` and `label_renderer(label)`, allowing a separate typesetting layer to receive mathematical content and display-mode information. Its default behavior HTML-escapes the mathematical source; it does not itself implement TeX-to-MathML conversion or browser-side mathematical layout.

`allow_digits` and `allow_space` are consequential when Markdown contains currency amounts or `$` characters that should not start equations. `allow_blank_lines` changes compatibility with other Markdown/LaTeX conventions. `double_inline` enables a different treatment of double-dollar delimiters within inline contexts.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mdit-py-plugins.readthedocs.io\&sz=32)

mdit-py-plugins+1



The main separation is mathematical syntax parsing → semantic math tokens → mathematical renderer/typesetter → final presentation. That permits different output backends without requiring the Markdown parser to understand or evaluate the mathematics itself.

### 3.5 Containers, callouts, and literal fences

Three mechanisms that look similar in Markdown source have importantly different semantics:

| Mechanism            | Interior content                    | Principal use                                                         |
| -------------------- | ----------------------------------- | --------------------------------------------------------------------- |
| `container_plugin`   | Recursively parsed as Markdown      | Structured nested blocks, extensions, and specialized block semantics |
| `admon_plugin`       | Parsed callout body                 | Notes, warnings, examples, and collapsible information panels         |
| `colon_fence_plugin` | Preserved as literal fenced content | Named literal blocks and fenced payloads                              |

`container_plugin` accepts a container name, marker character, validation callback, and renderer callback. The default renderer annotates the opening container with a CSS class; the interior is parsed through the normal block engine. Nested containers can therefore contain lists, mathematics, other containers, and additional Markdown extensions where the grammar permits.

`admon_plugin` recognizes the `!!!` family and `???` collapsible form, exposing a customizable rendering path. It provides Markdown syntax and output scaffolding, rather than a complete component UI implementation.

`colon_fence_plugin` creates a `colon_fence` token with its literal `content`, `info`, `markup`, and source map. Its default renderer emits escaped code content with a class derived from the fence info. It should not be confused with a container that recursively interprets Markdown. Nor should its generated HTML be treated as sanitized merely because the fenced body is escaped.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mdit-py-plugins.readthedocs.io\&sz=32)

mdit-py-plugins+1



### 3.6 Metadata, document structure, and specialized semantics

Heading anchors: `anchors_plugin(min_level, max_level, slug_func, permalink, permalinkSymbol, permalinkBefore, permalinkSpace)` generates IDs and optional navigable permalinks. The custom slug function is an important integration point when identifiers must agree with an external document index, link generator, or publishing platform. Stable cross-document identifiers require deliberate normalization and collision handling beyond merely enabling this plugin.

Word counting: `wordcount_plugin(per_minute=200, count_func=..., store_text=False)` updates `env["wordcount"]` with word counts and estimated reading time. A custom counting function can account for domain terminology or languages that are poorly represented by simple whitespace segmentation. `store_text` additionally retains collected text segments; counting semantics should not be confused with rendered-visible text in every custom dialect.

Definition versus field lists: `deflist_plugin` constructs term–definition relationships. `fieldlist_plugin` constructs named-field structures and supports rich field bodies. Both can be used for structurally meaningful documentation, but neither automatically creates validated Python dictionaries, schemas, or structured records. The 0.6.1 release specifically addresses field-list nesting behavior inside parent containers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mdit-py-plugins.readthedocs.io\&sz=32)

mdit-py-plugins+2



MyST integrations: `myst_role_plugin` recognizes role syntax; `myst_block_plugin` recognizes constructs such as explicit targets and MyST block syntax. The crucial boundary is that token recognition is not the same as resolving Sphinx roles, directives, citations, cross-references, or complete documentation build semantics. Those require the appropriate MyST/Sphinx interpretation and document-resolution layers.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://mdit-py-plugins.readthedocs.io\&sz=32)

mdit-py-plugins



Substitutions: `substitution_plugin(start_delimiter="{", end_delimiter="}")` recognizes double-delimited placeholders and emits `substitution_inline` or `substitution_block` tokens. Its source explicitly delegates handling to the renderer; it does not constitute a variable-evaluation engine. Its default delimiters overlap Jinja2's `{{ ... }}` expression syntax, a consequential conflict discussed later.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



### 3.7 Composability and version-sensitive distinctions

Three recurring integration constraints deserve particular attention:

- Syntax ownership: `~...~` can represent subscript, while a GFM configuration may enable single-tilde strikethrough. Similarly, `$` can introduce mathematical syntax or appear in ordinary text. The appropriate behavior depends on enabled rules and their precedence, not just on installing the plugin packages.
- Rendering completeness: Some plugins register both recognition and default HTML rendering; others principally produce semantic tokens that a downstream renderer must interpret. Recognition is not proof that a complete semantic document feature exists.
- Dialect completeness: The released `gfm_plugin` approximates GitHub's rendering with a composite of native and plugin features. Its tagged source explicitly states that GFM disallowed-HTML-tag filtering is not implemented; it should not be treated as a complete GFM conformance or sanitization layer.&#x20;

  [image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

  raw\.githubusercontent.com+2



Release boundary: The development-branch changelog mentions a `section_ref` capability, but the verified latest published version is 0.6.1. That development entry is not included as a released capability here.

Primary sources: released plugin documentation [https://mdit-py-plugins.readthedocs.io/en/stable/](https://mdit-py-plugins.readthedocs.io/en/stable/?utm_source=chatgpt.com) · tagged implementation [https://github.com/executablebooks/mdit-py-plugins/tree/v0.6.1/mdit_py_plugins](https://github.com/executablebooks/mdit-py-plugins/tree/v0.6.1/mdit_py_plugins?utm_source=chatgpt.com) · GFM implementation [https://raw.githubusercontent.com/executablebooks/mdit-py-plugins/v0.6.1/mdit_py_plugins/gfm/\_\_init\_\_.py](https://raw.githubusercontent.com/executablebooks/mdit-py-plugins/v0.6.1/mdit_py_plugins/gfm/__init__.py?utm_source=chatgpt.com) · footnotes [https://raw.githubusercontent.com/executablebooks/mdit-py-plugins/v0.6.1/mdit_py_plugins/footnote/index.py](https://raw.githubusercontent.com/executablebooks/mdit-py-plugins/v0.6.1/mdit_py_plugins/footnote/index.py?utm_source=chatgpt.com) · math [https://raw.githubusercontent.com/executablebooks/mdit-py-plugins/v0.6.1/mdit_py_plugins/dollarmath/index.py](https://raw.githubusercontent.com/executablebooks/mdit-py-plugins/v0.6.1/mdit_py_plugins/dollarmath/index.py?utm_source=chatgpt.com) · attributes [https://raw.githubusercontent.com/executablebooks/mdit-py-plugins/v0.6.1/mdit_py_plugins/attrs/index.py](https://raw.githubusercontent.com/executablebooks/mdit-py-plugins/v0.6.1/mdit_py_plugins/attrs/index.py?utm_source=chatgpt.com) · substitutions [https://raw.githubusercontent.com/executablebooks/mdit-py-plugins/v0.6.1/mdit_py_plugins/substitution.py](https://raw.githubusercontent.com/executablebooks/mdit-py-plugins/v0.6.1/mdit_py_plugins/substitution.py?utm_source=chatgpt.com)

## 4. Jinja2 3.1.6 — compiled templates, compositional programming, and document generation

Jinja2 provides a programmable template language with its own parser, AST, compiler, runtime context, and extension system. Templates are compiled into Python execution code; rendering evaluates that code against an environment and supplied data.

Its advanced value extends beyond replacing placeholders. It can express reusable document structures, dynamically compose templates, inspect dependencies, produce native Python objects, integrate asynchronous data sources, and execute restricted template programs under a configurable sandbox.

### 4.1 Environment configuration, compilation, and execution lifecycle

`jinja2.Environment` defines the template language configuration, compilation behavior, loading system, and runtime policy.

| Mechanism              | Advanced capability and implications                                                                                                                                                                                                                                    |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Configurable syntax    | `block_start_string`, `block_end_string`, `variable_start_string`, `variable_end_string`, `comment_start_string`, `comment_end_string` permit alternative delimiters. Important for generating Markdown, LaTeX, JavaScript, or other languages that already use braces. |
| Line-oriented syntax   | `line_statement_prefix` and `line_comment_prefix` permit statement/comment directives without normal block delimiters.                                                                                                                                                  |
| Whitespace controls    | `trim_blocks`, `lstrip_blocks`, `newline_sequence`, `keep_trailing_newline` control output structure and line endings.                                                                                                                                                  |
| Compiler optimization  | `optimized` enables compiler optimizations, including applicable constant-expression evaluation; it does not automatically cache rendered documents.                                                                                                                    |
| Undefined-value policy | `undefined` selects how missing variables behave during lookup, output, arithmetic, comparisons, and iteration.                                                                                                                                                         |
| Output finalization    | `finalize` applies a caller-supplied transformation to expression results before output, providing centralized representation policy for values such as `None`.                                                                                                         |
| Autoescaping           | `autoescape` accepts a boolean or callable based on template name. Escaping is a rendering policy and depends on the target output context.                                                                                                                             |
| Runtime policies       | `policies` configures selected filter, formatting, JSON, and internationalization behavior independently of template syntax.                                                                                                                                            |
| Cache and reloading    | `cache_size`, `auto_reload`, and `bytecode_cache` control distinct template-loading and compilation costs.                                                                                                                                                              |
| Extensions             | `extensions` loads language extensions; the extension registry and its state form part of the compiled template environment.                                                                                                                                            |
| Asynchronous execution | `enable_async` generates async-capable template execution machinery, including support for asynchronous callables and iteration.                                                                                                                                        |

A compiled template is bound to the environment's parsing and execution assumptions. Environment-level filters, tests, globals, and configuration should therefore be established before templates are loaded. Mutating the environment after loading can produce inconsistent or undefined behavior for cached templates.

`Environment.overlay()` creates an associated environment with its own template cache while sharing selected resources with the original. Extensions are inherited and may be added but cannot simply be removed. Not all attributes are live-linked; some are copied. The 3.1.5 release fixed propagation of `enable_async` into overlay environments.

This supports related template configurations without duplicating every loader and extension definition, but overlays are not full isolated snapshots.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+4



### 4.2 Template loading, lookup namespaces, and override composition

Jinja's loading abstraction is more capable than reading template files from one directory.

| Loader              | Primary capability                                    | Less-obvious implications                                                                                                     |
| ------------------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `FileSystemLoader`  | Search ordered directories for template files         | Search-path ordering supports overrides; `followlinks` affects traversal of symlinked directories                             |
| `PackageLoader`     | Load templates from installed Python packages         | Suitable for distributing templates as package resources; namespace-package support has documented limitations                |
| `DictLoader`        | Resolve templates from an in-memory mapping           | Useful for generated or centrally registered template sources; changes are not governed by ordinary file-watching assumptions |
| `FunctionLoader`    | Delegate lookup to a callable                         | May return source, filename, and an `uptodate` callback; enables custom registries and nonfilesystem storage                  |
| `PrefixLoader`      | Dispatch prefixed template names to different loaders | Provides namespaces for multiple template families or independently maintained packages                                       |
| `ChoiceLoader`      | Search multiple loaders in priority order             | Supports application or user overrides of default packaged templates without copying all template resources                   |
| `ModuleLoader`      | Load previously compiled templates                    | Avoids runtime template-source compilation when used with `compile_templates()`                                               |
| Custom `BaseLoader` | Define an application-specific loading backend        | Must provide appropriate source/loading behavior and, where relevant, freshness checks                                        |

Key APIs include `get_template()`, `select_template()`, `get_or_select_template()`, `list_templates()`, and `join_path()`.

- `select_template()` supports fallback candidates rather than requiring a caller to implement repeated missing-template exception handling.
- `join_path()` controls how a template name is resolved relative to its parent; Jinja does not automatically implement ordinary filesystem-relative include semantics.
- `list_templates()` depends on loader support for listing. A loader that can resolve known names does not necessarily support discovery or bulk precompilation.
- `get_template(..., globals=...)` can update globals on a cached template. Passing request-specific mutable values as template globals is therefore different from supplying a render context and has potential cross-render implications.

This loader model enables priority-based template overlays, package-distributed template components, virtual template namespaces, and precompiled template bundles without requiring a custom template registry or include-resolution language.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+3



### 4.3 Three distinct caching and compilation layers

| Layer                     | Mechanism                                                            | Avoided work                                                 | Important limitation                                                                                 |
| ------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| In-memory template cache  | `Environment.cache`, `cache_size`, `auto_reload`                     | Repeated loader lookup and compilation within an environment | Cache lifetime is tied to the environment; freshness checks can still incur work                     |
| Bytecode cache            | `BytecodeCache`, `FileSystemBytecodeCache`, `MemcachedBytecodeCache` | Recompilation of a previously parsed template source         | Still requires template loading, execution, and output generation                                    |
| Ahead-of-time compilation | `Environment.compile_templates()` and `ModuleLoader`                 | Runtime source parsing and compilation                       | Template behavior remains dependent on execution context, data, and compatible runtime configuration |

The memory cache uses an LRU policy. `cache_size=0` disables template caching; `cache_size=-1` removes the normal cache-size limit. `auto_reload` and loader freshness callbacks determine when loaded templates need updating.

`BytecodeCache` exposes `load_bytecode(bucket)` and `dump_bytecode(bucket)` for custom backends. Its `Bucket` machinery supports source-based validation of cached compiled code. The filesystem and Memcached implementations are alternative storage backends, not mandatory components.

`compile_templates()` supports compilation to a directory or ZIP-based module bundle, template selection, filtering, and logging. `ModuleLoader` consumes the resulting precompiled modules.

A consequential distinction is that bytecode caching is not fragment caching or result caching. It avoids compiler work but does not memoize data retrieval, loop evaluation, calls to filters, or the rendered output. Fragment caching requires separate machinery or a custom extension. The advanced extension documentation includes a fragment-cache example based on a call block, illustrating how caching can be introduced at template-language level.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+3



### 4.4 Inheritance, block contracts, and dynamic template composition

Jinja distinguishes inheritance, inclusion, and module-like imports. They serve different structural purposes and have different execution semantics.

| Construct         | Main semantics                         | Important advanced distinctions                                                                                   |
| ----------------- | -------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `extends`         | Parent/child template inheritance      | Child blocks override named parent blocks; inheritance may span multiple levels                                   |
| `block`           | Named overridable region               | Supports `scoped`, `required`, repeated invocation, and inheritance-specific execution behavior                   |
| `super()`         | Invoke an overridden parent block      | `super.super()` can reach further ancestors                                                                       |
| `include`         | Render another template at a location  | Normally receives the current context; supports `without context`, fallback candidate names, and `ignore missing` |
| `import`          | Import exported macros and assignments | Normally context-independent and cached, functioning more like a template module                                  |
| `from ... import` | Import selected names                  | Same context and caching distinctions as module imports                                                           |

Advanced inheritance behavior:

- `required` blocks express an explicit template inheritance contract. A rendering hierarchy must supply an implementation rather than silently accepting an empty structural region.
- `scoped` blocks receive access to variables in the surrounding scope. This matters when defining blocks inside loops, where inherited templates may otherwise not have access to the expected loop-local variables.
- Block definitions participate in inheritance independently of ordinary surrounding conditional logic. A block in a conditional branch is not simply a Python-like conditional function definition.
- `self.block_name()` allows a block to be evaluated more than once in the same template.
- The parent used by `extends` may be selected dynamically, and template objects can be used in supported composition operations rather than relying only on literal names.

Import and include are not interchangeable. Imported macros ordinarily do not inherit the complete caller context, enabling caching of imported template modules. `with context` changes that behavior and disables the usual import caching. An include ordinarily receives the current context and renders the included template directly. A child template's macro definition does not automatically override a macro imported or defined in its parent through the block-inheritance mechanism.

These features provide a native means of expressing document layouts, layout contracts, reusable partials, theme overrides, and hierarchical specialization.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+4



### 4.5 Macros, caller blocks, and reusable document components

Macros are the template-language equivalent of reusable parameterized functions, but their semantics are specialized for producing template output.

- `macro` supports positional/default parameters, references to caller context where permitted, and reusable rendering fragments.
- Macro objects expose introspection attributes including `name`, `arguments`, `catch_kwargs`, `catch_varargs`, and `caller`.
- A `call` block supplies a callable rendering body to a macro. The macro can invoke `caller()` one or several times, optionally supplying arguments to the caller block.
- This mechanism supports higher-order template components: a template component can own structure while the caller provides content regions, or the component can repeatedly invoke supplied content against different values.
- Template macros can be imported from independent component libraries. Combined with `PrefixLoader`, they can be distributed and namespaced without conflating them with application-level Python functions.

Macros are most relevant when reuse involves presentation logic and output structure. For substantial data manipulation, business rules, database access, or expensive computations, exposing well-defined Python functions or precomputed data is generally a clearer architectural boundary.

The distinction is not that templates must remain devoid of computation; it is that macro composition is an output-structure mechanism, not a general replacement for domain services.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+1



### 4.6 Control flow, scoping, and stateful template evaluation

Jinja's control flow is expressive, but its scope and loop behavior should not be assumed identical to Python's.

Loop capabilities

- `loop.index`, `loop.index0`, `loop.revindex`, `loop.length`, `loop.first`, and `loop.last` provide position-aware rendering.
- `loop.previtem` and `loop.nextitem` support adjacent-element comparisons without requiring a caller to construct explicit neighbor pairs.
- `loop.changed()` detects whether one or more tracked values differ from the previous loop iteration; useful for change boundaries, grouped output, and section transitions.
- `loop.cycle()` alternates values by iteration.
- Recursive loops, declared with `recursive`, can traverse hierarchical trees while exposing `loop.depth` and `loop.depth0`.
- Loop-level filtering permits rendering only matching elements and affects the iteration metadata and empty-loop behavior.
- Standard Jinja loops do not enable Python's `break` and `continue` statements by default. The `loopcontrols` extension adds them.
- The loop `else` branch represents the empty-iteration case, rather than ordinary Python's no-break condition.

Scope and mutable state

- Assignments made inside a loop do not normally escape into the surrounding scope.
- `namespace()` supplies an explicit shared object whose attributes can be updated across scoped template constructs.
- `with` creates a temporary local scope.
- `if` does not establish the same separate scope as a loop or `with` block.
- Block-form `set` captures rendered content into a variable; block-form `filter` applies a filter to an entire captured region.
- Built-in helpers such as `cycler`, `joiner`, and `namespace` support repeated formatting, separator emission, and controlled state respectively.

This is enough to express sophisticated formatting behavior, including hierarchical tables of contents, change-sensitive headings, alternating sections, and recursive trees. The relevant limit is not lack of expressive power but the increasing cost of reasoning about complex stateful templates compared with typed, precomputed data structures.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+3



### 4.7 Native transformation capabilities: filters, tests, and data selection

Jinja contains a substantial collection of data-transformation operators. For document generation, their importance is that they can eliminate many simple preprocessing loops.

| Family                 | Important operations                                                        | Subtle behavior                                                                                                                      |
| ---------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Mapping and projection | `map`, attribute access, `join(attribute=...)`, `sum(attribute=...)`        | Operate over supplied objects and mappings without requiring explicit Python-side projection for simple cases                        |
| Predicate selection    | `select`, `reject`, `selectattr`, `rejectattr`                              | Compose with registered tests and attribute names                                                                                    |
| Ordering               | `sort`, `dictsort`, `reverse`                                               | `sort` is stable, enabling staged ordering; `dictsort` addresses mapping keys/values                                                 |
| Deduplication          | `unique`                                                                    | Preserves first-encounter ordering and exposes case-sensitivity options; operates as an iterator                                     |
| Grouping               | `groupby`                                                                   | Sorts before grouping, unlike raw adjacency grouping with `itertools.groupby`; ordering and case behavior can affect semantic output |
| Layout partitioning    | `batch`, `slice`                                                            | Different partitioning orientations, important for rows versus columns                                                               |
| Structural conversion  | `list`, `items`, `dictsort`, `first`, `last`, `default`                     | Handles iterable and mapping representations; materialization has cost for large iterators                                           |
| Text formatting        | `indent`, `wordwrap`, `truncate`, `replace`, `format`, `center`             | Output whitespace is semantically important when generating Markdown or other indentation-sensitive formats                          |
| HTML/URL formatting    | `escape`, `forceescape`, `safe`, `tojson`, `xmlattr`, `urlencode`, `urlize` | Each has different output-context guarantees; none is an all-purpose sanitizer                                                       |

`groupby` deserves special attention: it groups on a sorted key rather than preserving the original adjacency sequence. Its default case-insensitive behavior and missing-attribute handling can produce results different from a direct Python `itertools.groupby` operation.

`sort` is stable, which makes successive sorts on secondary and primary keys a valid ordering strategy in suitable contexts. `unique` preserves encounter order, which is useful for controlled lists or indexes but does not establish a deterministic ordering when the source iterable is itself unordered.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+1



### 4.8 Custom filters, tests, globals, and runtime-aware callables

The extension surface includes more than registering Python functions under short names.

Custom filters transform template values; tests return predicates for expressions such as `is defined` or `is my_test`; globals provide functions and data available without explicit per-render injection.

Jinja can also inject execution context into registered functions through dedicated decorators:

| Decorator           | Supplied context           | Architectural use                                                                                             |
| ------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `pass_context`      | Active template context    | Context-dependent operations that need access to variables or names available at a particular rendering point |
| `pass_eval_context` | Current evaluation context | Output-sensitive behavior, especially autoescape-aware filters and rendering                                  |
| `pass_environment`  | Environment object         | Configuration-aware operations, environment-specific policies, and registered services                        |

Filters and tests can use dotted naming schemes, enabling more organized namespaces than a flat registry.

A custom filter that generates markup should respect the active evaluation context and use MarkupSafe appropriately. A function that returns HTML marked safe while incorporating unescaped untrusted content bypasses protections even when automatic escaping is enabled.

`Environment.finalize` is distinct from a filter: it centralizes conversion of expression results before output. Its behavior should not be mistaken for a complete deep transformation of every nested object.

Relevant configurable policies include JSON serialization (`json.dumps_function`, `json.dumps_kwargs`), URL linkification (`urlize.rel`, `urlize.target`, `urlize.extra_schemes`), truncation behavior (`truncate.leeway`), and selected internationalization behavior.

A custom filter is a convenient integration boundary for functionality that deserves implementation in Python while retaining declarative presentation in the template. It is generally preferable to building a custom Jinja language extension solely to expose a specialized computation.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+2



### 4.9 Undefined values, attribute lookup, and strict data contracts

Jinja's handling of missing values is configurable and consequential for correctness.

| Undefined type             | Behavior                                                                                                          | Appropriate interpretation                                        |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `Undefined`                | Can render as an empty string, evaluate false, and iterate as empty; many other operations raise errors           | Permissive rendering, but potentially hides missing template data |
| `StrictUndefined`          | Raises on almost every use, including printing and boolean evaluation; explicit definedness tests remain possible | Stronger detection of missing data contracts                      |
| `ChainableUndefined`       | Supports chained attribute/item access while remaining undefined                                                  | Useful with `default` for deeply nested optional data             |
| `DebugUndefined`           | Displays a source-like placeholder when printed                                                                   | Helps expose unresolved variables during template inspection      |
| `make_logging_undefined()` | Wraps undefined behavior with logging                                                                             | Adds runtime diagnostics for selected missing-value operations    |
| Custom subclass            | Defines domain-specific missing-value semantics                                                                   | Specialized diagnostics and policies                              |

Missing, false, and null are different states. The `default` filter ordinarily replaces undefined values, not every falsy value. Its optional boolean parameter broadens replacement to falsy results, potentially collapsing meaningful values such as `0`, `False`, and empty collections.

Dot and bracket lookup have different precedence:

- `object.name`: attempts attribute lookup before item lookup.
- `object["name"]`: attempts item lookup before attribute lookup.

For mappings, this can be consequential when a key conflicts with a method such as `items` or `keys`.

`StrictUndefined` helps surface accidental omissions, but only when an undefined value is evaluated. It is not a compile-time schema checker. Up-front validation of the supplied context remains a separate capability.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+2



### 4.10 NativeEnvironment: structured evaluation without mandatory string rendering

`jinja2.nativetypes.NativeEnvironment` modifies the output model so that template evaluation can return native Python values rather than always producing a string.

Consequential capabilities include:

- Preserving objects returned by a single expression, where applicable, instead of immediately converting them to their textual representations.
- Returning values such as numbers, lists, mappings, and other Python objects from suitable template expressions.
- Using the Jinja expression language for calculated configuration values, structured parameter selection, or other non-HTML results.
- Combining native rendering with sandboxing through appropriate environment subclass composition.

The difference from ordinary `Environment` is semantic rather than cosmetic: the result may be an object that subsequent Python code can process directly.

However, `NativeEnvironment` does not guarantee a specific type for every template. Multiple rendered fragments and literal-compatible output affect type reconstruction. It is not a general serializer, typed schema compiler, or validation system. If downstream consumers require a fixed structure, that contract still needs explicit enforcement.

This mechanism is particularly valuable when the intended output is structured data rather than a textual document, and it avoids unnecessary render-to-string-and-parse-again cycles when its result semantics fit the workload.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+1



### 4.11 Streaming, generators, and asynchronous rendering

Jinja exposes three meaningfully different output execution patterns.

| Execution mode          | Key APIs                                   | Semantics                                                                                            |
| ----------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| Eager synchronous       | `Template.render()`                        | Executes the template and returns a complete string                                                  |
| Incremental synchronous | `Template.generate()`, `Template.stream()` | Produces output fragments; `TemplateStream` supports buffering and direct dumping                    |
| Asynchronous            | `render_async()`, `generate_async()`       | Awaits asynchronous values and functions where supported; can generate asynchronous output fragments |

`TemplateStream.enable_buffering(size)` groups output fragments to reduce overly frequent writes or flushes. Buffering affects emission granularity and overhead; it does not necessarily reduce total computation or provide a bounded-memory guarantee for every template.

`TemplateStream.dump()` can write generated content directly to a target stream or file, optionally with an encoding.

With `enable_async=True`, the compiler supports async-aware evaluation and iteration. Async rendering can use asynchronous callables and asynchronous iterables provided to the template, and `generate_async()` can be consumed incrementally.

Important restrictions and implications:

- `render_async()` still returns the complete rendered result; it is not a streaming interface.
- `generate_async()` exposes asynchronous iteration, but downstream consumers may still require complete-document buffering.
- Async execution is principally useful when template evaluation invokes asynchronous operations. It is not automatically a faster way to perform CPU-bound formatting.
- The ordinary synchronous `render()` path on an async-configured environment is not a substitute for using the async API inside an already running event loop.
- Certain module-oriented template APIs differ under async execution, including restrictions on synchronous access to template modules.

This separation permits low-memory incremental emission or asynchronous source integration where the surrounding processing pipeline can actually exploit it.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+2



### 4.12 Template AST, static analysis, and dependency discovery

Jinja's parser and compiler infrastructure is directly accessible. This makes it possible to analyze templates before rendering, rather than treating them as opaque strings.

| Mechanism                                    | Capability                                                                           | Important boundary                                                                               |
| -------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `Environment.lex()`                          | Produces lexical tokens with source line information                                 | Does not apply the full extension preprocessing pipeline                                         |
| `Environment.preprocess()`                   | Applies extension preprocessing to template source                                   | Source may be transformed before later parsing                                                   |
| `Environment.parse()`                        | Produces a Jinja AST                                                                 | AST represents template syntax, not a fully evaluated program                                    |
| `jinja2.meta.find_undeclared_variables(ast)` | Identifies possible externally supplied variable names                               | Conservative across branches; may raise `TemplateAssertionError`                                 |
| `jinja2.meta.find_referenced_templates(ast)` | Finds statically identifiable `extends`, `include`, and `import` dependencies        | Dynamic template names cannot always be resolved; `None` denotes an unresolved dynamic reference |
| `Environment.compile_expression()`           | Compiles an isolated Jinja expression to a callable evaluator                        | Useful for controlled expression evaluation; not a safe expression sandbox by itself             |
| `Environment.compile()`                      | Compiles a template source into a code object or Python source, depending on options | Lower-level compiler API; output depends on compiler configuration                               |

The particularly valuable combination is AST inspection plus dependency discovery.

It enables general-purpose analysis of which context variables a template might consume, which other templates it references, and what dependency relationships can be identified before execution. This can reduce custom string scanning and establish the basis for template validation, selective rebuild logic, and static diagnostics.

Two qualifications are essential:

1. `find_undeclared_variables()` is a conservative syntactic/compiler analysis. It does not establish which names will actually be accessed on a specific runtime path.
2. `find_referenced_templates()` does not resolve arbitrary dynamically computed template names, so its graph is not guaranteed complete.

Neither API supplies complete dataflow analysis or schema validation. Their value is structured access to the template compiler's understanding, which is materially more reliable than parsing template directives with regexes.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+1



### 4.13 Language extensions: from token filtering to AST generation

`jinja2.ext.Extension` supports adding or transforming template-language constructs.

There are three principal levels of intervention:

| Level                  | Extension mechanism                         | Nature of customization                                                   |
| ---------------------- | ------------------------------------------- | ------------------------------------------------------------------------- |
| Preprocessing          | `Extension.preprocess()`                    | Transform source text before the main parser consumes it                  |
| Lexical transformation | `Extension.filter_stream()`                 | Transform the lexer token stream before parsing                           |
| Grammar and AST        | `Extension.tags`, `Extension.parse(parser)` | Add new template tags and construct AST nodes representing their behavior |

Advanced AST integration:

- An extension can construct nodes using `jinja2.nodes`, including `CallBlock` and expression nodes.
- `Extension.call_method()` produces a call expression targeting a method on the extension instance; this allows AST constructs to invoke Python-side extension logic.
- `Extension.attr()` provides access to extension attributes through generated expressions.
- `Environment.extend()` can register extension-owned environment configuration.
- Custom AST nodes need correct structure, field types, and source-line metadata. The compiler does not automatically repair invalid AST construction.

Extensions permit new control structures, instrumentation hooks, cached regions, specialized document directives, and domain-oriented template constructs. They are meaningfully different from ordinary filters because they can change grammar and evaluation structure.

The design choice is between exposing computation through filters/tests, encapsulating output structure in macros, and changing the language itself through extensions. The last offers the broadest control but also the highest compatibility and maintenance burden.

The documented built-in extensions include:

- `jinja2.ext.i18n` — translation tags, pluralization, contextual translation support, and translation extraction integration.
- `jinja2.ext.do` — expression statements, including execution of expressions for side effects without emitting output.
- `jinja2.ext.loopcontrols` — `break` and `continue` inside loops.
- `jinja2.ext.debug` — debugging helpers exposing available context and environment information.

Some capabilities previously supplied by extensions, such as `with` and autoescape controls, are integrated into the core language in modern Jinja.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+2



### 4.14 Internationalization and translation extraction

Jinja's internationalization support is more extensive than applying a translation function to arbitrary strings.

- The `i18n` extension introduces translation blocks and gettext-style runtime integration.
- Singular and plural translation forms can be represented in template source.
- Contextual translation variants permit the same source text to have different meanings in different domains.
- Translation calls can be installed through the environment and integrated with external gettext/Babel workflows.
- Extraction infrastructure identifies translation messages from template source for catalog management.
- The `ext.i18n.trimmed` policy controls whitespace normalization in translation blocks.

Translation blocks deliberately constrain the supported expression structure. Complex transformations should normally be assigned to variables before entering translation constructs.

This separation makes translation messages discoverable and manageable by catalog tooling while retaining normal Jinja template composition. It is particularly relevant for document generators that need multiple languages without duplicating all template layouts.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+2



### 4.15 Sandboxed evaluation and operator interception

`SandboxedEnvironment` changes the compiler and runtime's treatment of potentially unsafe operations. It should be understood as a configurable restriction layer, not an unconditional security guarantee.

| Sandbox surface     | Mechanism                             | Capability / limitation                                                     |
| ------------------- | ------------------------------------- | --------------------------------------------------------------------------- |
| Attribute access    | `is_safe_attribute(obj, attr, value)` | Restricts attributes, including private/internal names under default policy |
| Callable access     | `is_safe_callable(obj)`               | Controls which exposed callables a template may invoke                      |
| Binary operators    | `intercepted_binops`, `call_binop()`  | Can intercept `+`, `-`, `*`, `/`, `//`, `%`, and `**`                       |
| Unary operators     | `intercepted_unops`, `call_unop()`    | Can intercept unary plus and minus                                          |
| Mutable objects     | `ImmutableSandboxedEnvironment`       | Restricts known mutation operations on built-in mutable collection types    |
| Exception reporting | `SecurityError`                       | Exposes rejected operations as sandbox violations                           |

Less-obvious consequences:

- Under the default callable policy, ordinary callables are generally considered safe unless marked otherwise or recognized as mutating data. Exposing a powerful Python object or function can therefore undermine the intended restriction.
- Operator interception can prohibit or redefine expensive operations such as exponentiation, but intercepted operators use additional runtime dispatch. It is configurable rather than universally active.
- `ImmutableSandboxedEnvironment` limits identified mutations of known collection types; it is not proof that every exposed object is immutable or side-effect free.
- Sandboxing alone does not prevent excessive CPU, memory, recursion, or output generation. Resource constraints and termination policies are separate.
- Template loading, exposed globals, filters, tests, custom extensions, and user-provided objects remain part of the attack surface.

Version-sensitive security: Jinja2 3.1.6 includes a sandbox fix for attribute access through the `attr` filter. Earlier 3.1.x releases also contained fixes related to string formatting and HTML attribute rendering. When sandboxed execution is part of a security boundary, the exact patch release matters.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+4



### 4.16 Escaping, MarkupSafe, and multi-format output safety

Jinja's automatic escaping is centered on HTML/XML-style markup, using MarkupSafe to distinguish ordinary strings from markup already designated safe.

- `select_autoescape()` configures escaping by template filename extension and whether a template was created from a string.
- A bare `Environment()` does not automatically enable HTML escaping.
- `Markup` marks content as already safe for the relevant HTML rendering path; it does not sanitize that content.
- `safe`, `escape`, and `forceescape` have different purposes and should not be treated as interchangeable.
- `tojson` emits HTML-safe JSON output suitable for common HTML contexts, including script elements. Direct insertion into double-quoted HTML attributes has an additional quoting/escaping consideration.
- `xmlattr` builds HTML/XML attributes but still depends on correct key and value handling and the current security fixes.
- Escaping HTML text does not automatically make text safe as a URL, CSS declaration, JavaScript expression, Markdown fragment, or SQL statement.

For structured output generation, it is useful to distinguish escaping for the target representation, sanitization of permitted content, and validation of semantic values. Jinja provides mechanisms relevant to escaping, but not comprehensive policy enforcement for arbitrary output languages.

This is especially important when Jinja generates Markdown rather than HTML: HTML-escaping a value may not prevent that value from introducing new Markdown syntax. Markdown-sensitive data requires its own handling or structural generation strategy.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+2



### 4.17 Diagnostic behavior and advanced execution boundaries

Jinja exposes typed failure modes such as `TemplateSyntaxError`, `TemplateAssertionError`, `TemplateNotFound`, `TemplatesNotFound`, `UndefinedError`, `SecurityError`, and `TemplateRuntimeError`. Its generated execution system also rewrites tracebacks to refer to template source locations, making it more diagnosable than ad hoc string substitution.

Relevant implementation boundaries:

- Compile-time and runtime validation differ. A template may parse successfully and still fail when executed with particular data.
- Strict missing-value policies do not establish total input validity. They reveal undefined access when that execution path is taken.
- Precompilation is not a complete validation campaign. `compile_templates()` has an `ignore_errors` option whose behavior matters when compiling a large template collection.
- Dynamic includes and expressions limit static guarantees. AST-based dependency checks cannot determine every dynamic runtime selection.
- Template expressions can execute Python callables supplied in context. Complexity, I/O, state changes, and security therefore depend on the objects made available.
- Template output can be structurally significant. Generated Markdown, YAML, SQL, or configuration may require separate parsing and semantic validation after generation.

The most useful architectural perspective is that Jinja supplies an established language runtime and compilation infrastructure for controlled output programs. It can replace custom macro systems, include resolvers, presentation-condition interpreters, template caches, and some dependency-analysis machinery, but it does not replace specialized parsers or validators for the languages it generates.

Primary sources: API and execution model [https://jinja.palletsprojects.com/en/stable/api/](https://jinja.palletsprojects.com/en/stable/api/?utm_source=chatgpt.com) · template-language reference [https://jinja.palletsprojects.com/en/stable/templates/](https://jinja.palletsprojects.com/en/stable/templates/?utm_source=chatgpt.com) · language extensions [https://jinja.palletsprojects.com/en/stable/extensions/](https://jinja.palletsprojects.com/en/stable/extensions/?utm_source=chatgpt.com) · AST and dependency metadata [https://jinja.palletsprojects.com/en/stable/api/#module-jinja2.meta](https://jinja.palletsprojects.com/en/stable/api/?utm_source=chatgpt.com#module-jinja2.meta) · native types [https://jinja.palletsprojects.com/en/stable/nativetypes/](https://jinja.palletsprojects.com/en/stable/nativetypes/?utm_source=chatgpt.com) · sandbox [https://jinja.palletsprojects.com/en/stable/sandbox/](https://jinja.palletsprojects.com/en/stable/sandbox/?utm_source=chatgpt.com) · release and security changes [https://jinja.palletsprojects.com/en/stable/changes/](https://jinja.palletsprojects.com/en/stable/changes/?utm_source=chatgpt.com) · tagged source [https://github.com/pallets/jinja/tree/3.1.6](https://github.com/pallets/jinja/tree/3.1.6?utm_source=chatgpt.com)

## 5. Cross-library composition and architectural implications

The three libraries become substantially more powerful when their responsibilities remain distinct. Their most consequential combinations are not merely alternative ways to produce HTML; they support different document-processing architectures.

### 5.1 Principal composition patterns

| Architecture                        | Native capabilities combined                                                | Benefits and important conditions                                                                                                                      |
| ----------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Template → Markdown → HTML          | Jinja compilation and macros → Markdown parsing and plugins → HTML renderer | Dynamic document generation with headings, tables, notes, mathematics, and other syntax; requires attention to whitespace and injected Markdown syntax |
| Markdown → tokens → custom renderer | Markdown parser, plugin tokens, core transformations, renderer interface    | Semantic extraction and multiple output formats without first converting everything to HTML                                                            |
| Markdown → structured data → Jinja  | Token/tree interpretation → Python data model → template rendering          | Separates content semantics from presentation and permits multiple layouts from the same interpreted source                                            |
| Jinja → structured Python objects   | `NativeEnvironment`, registered filters/tests, strict undefined behavior    | Avoids unnecessary string serialization for compatible data-generation workloads; requires downstream type validation                                  |
| Document-analysis pipeline          | Token metadata, source maps, word counting, Jinja AST/meta analysis         | Structural checks and dependency extraction across source documents and templates                                                                      |
| Extensible documentation dialect    | Configurable Markdown rule engines, mdit plugins, Jinja macros/extensions   | Domain-specific documentation syntax without building an entire parser and template language from scratch                                              |

The third architecture—Markdown into structured data before Jinja rendering—is particularly valuable when source content needs to be reused across multiple output formats. It keeps parsing and document semantics separate from presentation.

Conversely, direct Jinja-to-Markdown generation is simpler when Markdown is the actual desired output and no intermediate semantic model is required.

### 5.2 Semantic boundaries and ordering

A. Template evaluation versus Markdown parsing

Rendering Jinja first means that the Markdown parser sees the expanded source. Template variables and macro output can therefore introduce headings, lists, tables, fenced blocks, footnotes, or other constructs.

Parsing Markdown first instead preserves the original Markdown structure, but Jinja expressions embedded in Markdown become ordinary text or tokens unless an explicit subsequent evaluation stage is added.

This difference matters for both correctness and source provenance. Markdown line maps produced after Jinja expansion refer to the generated document, not automatically to locations in the originating template.

B. Delimiter collisions

The default mdit substitution syntax `{{name}}` overlaps Jinja's `{{ ... }}` expression delimiters. Possible resolution strategies include assigning distinct delimiters, protecting literal source regions using Jinja raw blocks, or deciding explicitly which language owns substitutions.

Other interactions include dollar-delimited math versus ordinary dollar signs, tilde-based subscript versus strikethrough, and Jinja whitespace controls versus indentation-sensitive Markdown constructs.

A Jinja renderer has no intrinsic understanding of whether an expression occurs within a Markdown code fence. Treating source as a nested language therefore requires deliberate ordering or syntax protection.

C. Cross-document state

`MarkdownIt` parser configuration and Jinja `Environment` configuration are reusable, but their mutable data have different lifetimes:

- Markdown `env` is the document-specific context through which plugins coordinate.
- Jinja's environment owns compiler configuration, registries, loaders, and caches.
- Jinja render context supplies values for a particular evaluation.

These should remain conceptually separate. In particular, Jinja globals or mutable Markdown plugin metadata should not accidentally become shared storage for unrelated document renderings.

### 5.3 Security boundaries across the pipeline

| Input or execution boundary                        | Relevant protection                                                           | What it does not guarantee                                                   |
| -------------------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Untrusted Jinja template code                      | `SandboxedEnvironment`, controlled globals/callables, resource constraints    | Arbitrary safe execution or bounded resource usage                           |
| Untrusted values rendered into HTML                | Autoescape, MarkupSafe, context-appropriate escaping                          | Safe URLs, JavaScript, CSS, or arbitrary HTML sanitization                   |
| Untrusted Markdown containing raw HTML             | Parser HTML configuration and dedicated sanitization                          | Safety of all plugin-generated HTML or custom render rules                   |
| Untrusted Markdown attributes                      | `attrs_plugin(allowed=...)`                                                   | Complete sanitization of links, CSS class policies, URLs, or output HTML     |
| Untrusted strings inserted into generated Markdown | Markdown-aware escaping or structural validation                              | Preservation of the original document structure merely through HTML escaping |
| Semantic content assertions                        | Token inspection, strict template missing-value policies, external validation | Complete schema correctness, source integrity, or authorized references      |

One especially important distinction: Jinja autoescaping is not sufficient protection when its output is subsequently interpreted as Markdown. A string inserted into Markdown can create new structural syntax without containing unsafe HTML characters.

Similarly, using MarkupSafe's `Markup` for already generated HTML is appropriate only when the markup is trusted or has been suitably sanitized for the target context.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+3



### 5.4 Streaming and performance interactions

Jinja provides incremental rendering, but markdown-it-py's document-wide parsing model introduces a practical boundary.

Footnote numbering, reference definitions, heading-anchor collision handling, and core token transformations can depend on information from elsewhere in the document. A chunk of Markdown output from `Template.generate()` is therefore not necessarily a self-contained Markdown parsing unit.

A pipeline that renders Jinja incrementally and then requires a complete Markdown token representation may still need to buffer the entire generated Markdown document.

Other consequential performance distinctions:

- Compiled template caching avoids parsing/compilation work, not repeated document content generation.
- Markdown parser reuse avoids repeatedly configuring rules and plugins; it does not imply that document parsing results are cached.
- Token transformations avoid reparsing rendered HTML when the desired information is already represented structurally.
- Async Jinja can overlap asynchronous work invoked during rendering but does not accelerate CPU-bound Markdown tokenization merely through async execution.
- A specialized renderer can eliminate unnecessary intermediate output conversion when the desired target is not HTML.

These are mechanism-based opportunities rather than universal performance guarantees.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://jinja.palletsprojects.com\&sz=32)

Jinja Documentation (3.1.x)+3



### 5.5 Choosing the correct extension level

| Requirement                                            | Most natural extension point                          |
| ------------------------------------------------------ | ----------------------------------------------------- |
| Recognize new inline or block Markdown syntax          | markdown-it-py inline/block ruler                     |
| Change document-wide Markdown semantics                | markdown-it-py core rule and `env`                    |
| Attach annotations without changing syntax             | Token attributes, `meta`, core transformation         |
| Add an established Markdown dialect feature            | mdit-py-plugins                                       |
| Change HTML emitted for an existing Markdown construct | `add_render_rule()` or renderer subclass              |
| Produce output other than HTML from Markdown           | Custom renderer consuming tokens                      |
| Reuse complex document presentation                    | Jinja macros, call blocks, inheritance                |
| Change template-language control flow or grammar       | Jinja `Extension` and AST generation                  |
| Expose specialized Python computation                  | Jinja filter, test, global, or context-aware callable |
| Inspect variables and template dependencies            | Jinja AST and `jinja2.meta`                           |
| Detect missing template inputs during evaluation       | `StrictUndefined`                                     |
| Produce native structured values from expressions      | `NativeEnvironment`, followed by explicit validation  |

The general principle is to extend at the lowest level that owns the required semantics. For instance, a new Markdown block syntax belongs in the Markdown parser, not a Jinja regex filter; a reusable document layout belongs in Jinja, not a custom Markdown rule.

## 6. Additional ecosystem boundaries worth preserving

These are relevant adjacent capabilities, but they should not be confused with functionality directly provided by the three libraries.

| Adjacent system                     | Relationship                                                                                                               |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| MarkupSafe                          | Supplies Jinja's HTML-safe-string and escaping foundation; not a universal content sanitizer                               |
| Babel / gettext                     | Supports translation catalogs and extraction workflows with Jinja's internationalization extension                         |
| linkify-it-py                       | Provides URL autolinking for markdown-it-py's relevant presets; distinct from mdit's dedicated GFM autolink implementation |
| Pygments                            | Can implement syntax highlighting through Markdown renderer callbacks; not built into the Markdown grammar                 |
| KaTeX / MathJax / MathML generators | Typeset or represent mathematics recognized by mdit's math plugins                                                         |
| MyST-Parser / Sphinx                | Supply broader documentation semantics and build integration beyond standalone MyST token recognition                      |
| HTML sanitizers                     | Enforce output HTML policies after parsing and rendering where untrusted markup is permitted                               |
| Typed validation libraries          | Validate contexts, semantic document models, or generated structured data; not replaced by `StrictUndefined` or tokens     |

The important architectural opportunity is not necessarily adding all these dependencies. It is recognizing when a native parser, plugin, renderer, or template mechanism already covers the underlying operation, and when the operation crosses into another library's responsibility.

## 7. Consolidated assessment

The most significant capabilities to recognize across these libraries are:

1\. markdown-it-py is a programmable parsing infrastructure, not merely a Markdown-to-HTML converter. Its ordered rule engines, token metadata, core transforms, tree representation, and configurable renderers enable semantic processing that would otherwise require custom parsing and reconstruction logic.

2\. mdit-py-plugins supplies semantic document constructs as well as presentational syntax. Footnote resolution, structured containers, attribute propagation, mathematical tokens, MyST constructs, and document statistics participate in parser phases and can support downstream transformations independently of their default HTML rendering.

3\. Jinja2 is a compiled document-programming runtime. Template inheritance, macros and caller blocks, loader composition, dependency introspection, bytecode caching, native types, language extensions, sandbox controls, and async streaming are architectural mechanisms rather than just syntax conveniences.

4\. Their greatest combined value comes from separating data, document semantics, and presentation. Keeping these stages explicit makes it possible to reuse grammar extensions, semantic analysis, templates, and output backends while preserving meaningful correctness and security boundaries.

5\. Neither completeness nor safety follows automatically from extensibility. Lossless source rewriting, complete GFM/MyST interpretation, HTML sanitization, arbitrary-template security, schema validation, and end-to-end incremental Markdown processing remain separate capabilities.

The release distinctions used throughout this reference are deliberate: markdown-it-py 4.2.0, mdit-py-plugins 0.6.1, and Jinja2 3.1.6. Features present only on unreleased branches, in adjacent frameworks, or in hypothetical integrations are not treated as native released capabilities.

For continued API-level investigation, the most useful starting points are the version-specific sources supplied under each library section, particularly the Markdown parser architecture, the tagged mdit plugin implementations, and Jinja's API, extension, sandbox, and AST references.