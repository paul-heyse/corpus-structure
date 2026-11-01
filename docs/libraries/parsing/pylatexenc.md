# pylatexenc — Python Library Capability Reference

Research date: October 28, 2026 | Stable version: 2.11 | Prerelease: 3.0b2

## 1. Overview and architectural role

pylatexenc is a lightweight, extensible Python library for parsing LaTeX markup, converting LaTeX into Unicode text, and encoding Unicode text into LaTeX-compatible representations.

Its distinguishing capability is that it combines a structural LaTeX parser with configurable syntax definitions and semantic text-conversion rules, without requiring a TeX distribution or executing a full LaTeX engine.

It is particularly useful for document ingestion, scientific-text processing, indexing, LaTeX-aware transformations, custom markup analysis, and pipelines that need to understand LaTeX structure without typesetting it.

### Version status

PyPI confirms the following releases:

| Release | Status                | Published     |
| ------- | --------------------- | ------------- |
| 2.11    | Latest stable         | July 25, 2026 |
| 3.0b2   | Latest 3.x prerelease | July 28, 2026 |
| 3.0b1   | Earlier beta          | July 26, 2026 |

Version 3 introduces significant architectural improvements, particularly in parsing extensibility, parsing-state management, node traversal, and Unicode formatting. However, it is still a prerelease, not the default stable version.

Accordingly, this reference distinguishes stable 2.x functionality from additional 3.0 beta capabilities. This distinction is especially important because the latest Read the Docs documentation describes 3.0b2 rather than the stable release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



Primary resources:

- Stable 2.x documentation: [https://pylatexenc.readthedocs.io/en/v2.10/](https://pylatexenc.readthedocs.io/en/v2.10/?utm_source=chatgpt.com)
- Version 3 beta documentation: [https://pylatexenc.readthedocs.io/en/latest/](https://pylatexenc.readthedocs.io/en/latest/?utm_source=chatgpt.com)
- Source repository: [https://github.com/phfaist/pylatexenc](https://github.com/phfaist/pylatexenc?utm_source=chatgpt.com)
- Package releases: [https://pypi.org/project/pylatexenc/#history](https://pypi.org/project/pylatexenc/?utm_source=chatgpt.com#history)

## 2. Capability map

| Functional family                 | Principal interfaces                                       | Architectural role                                              |
| --------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------- |
| LaTeX → Unicode                   | `latex2text`, `LatexNodes2Text`                            | Produce readable, searchable text from LaTeX markup             |
| Unicode → LaTeX                   | `latexencode`, `UnicodeToLatexEncoder`                     | Escape and encode text into LaTeX-compatible syntax             |
| Structural parsing                | `latexwalker`, `LatexWalker`                               | Identify macros, environments, groups, math, comments, and text |
| Syntax customization              | `macrospec`, `LatexContextDb`                              | Define recognized constructs and their argument grammars        |
| Semantic conversion customization | `MacroTextSpec`, `EnvironmentTextSpec`, `SpecialsTextSpec` | Define how parsed constructs appear in plain text               |
| Source-aware analysis             | LaTeX node objects, source positions                       | Inspect original markup and retain structural boundaries        |
| CLI utilities                     | `latex2text`, `latexencode`, `latexwalker`                 | Shell-oriented conversion and parsing                           |
| Extensible parser framework       | `latexnodes` (3.x)                                         | Specialized parsers, token readers, and node collection         |
| Stateful parsing                  | `ParsingStateDelta` (3.x)                                  | Propagate controlled syntax and parsing-state changes           |
| Tree traversal and reconstruction | Visitor/recomposer (3.x)                                   | Structured analysis and LaTeX regeneration                      |

The most consequential conceptual distinction is between three operations:

1. Parsing determines which LaTeX constructs exist and how their arguments are structured.
2. Interpretation determines how those constructs should be represented in plain text.
3. Encoding determines how Unicode characters should be represented in LaTeX syntax.

These responsibilities are separable. Recognizing a custom macro does not automatically establish its meaning, and converting LaTeX to text is not equivalent to compiling or rendering it.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 3.0beta2 documentation+2



## 3. Structural LaTeX parsing — `latexwalker`

### 3.1 Parsing model

`LatexWalker` takes a LaTeX source string and constructs a tree of nodes representing its markup structure.

Unlike regular-expression extraction, this preserves nesting and distinguishes syntactically different constructs. A macro's arguments are parsed according to its registered signature, rather than treating all braces uniformly.

The stable 2.x interface is:

```
from pylatexenc.latexwalker import LatexWalkerwalker = LatexWalker(latex_source)nodes, pos, length = walker.get_latex_nodes()
```

The result is a Python node list plus the starting position and consumed source length.

The parser also supports selective parsing, so an application need not always process an entire source string.

Important entry points include:

| Method                           | Capability                                                              |
| -------------------------------- | ----------------------------------------------------------------------- |
| `get_latex_nodes()`              | Parse a sequence of nodes, optionally stopping at a structural boundary |
| `get_latex_expression()`         | Parse a single LaTeX expression or argument                             |
| `get_latex_braced_group()`       | Parse a delimited group, including nested contents                      |
| `get_latex_environment()`        | Parse a named `\begin` / `\end` environment                             |
| `get_latex_maybe_optional_arg()` | Parse a square-bracketed argument when present                          |
| `get_token()`                    | Read a lower-level LaTeX token                                          |
| `make_parsing_state()`           | Construct an altered parsing context                                    |
| `pos_to_lineno_colno()`          | Translate source offsets into line and column coordinates               |

`get_latex_nodes()` exposes stopping conditions for closing braces, environment endings, math delimiters, and a maximum node count. This allows callers to parse structurally bounded regions without implementing another delimiter-aware scanner.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation+2



Reference: [https://pylatexenc.readthedocs.io/en/v2.10/latexwalker/](https://pylatexenc.readthedocs.io/en/v2.10/latexwalker/?utm_source=chatgpt.com)

### 3.2 Node types and retained structure

The stable parser defines seven principal node types.

| Node                   | Represents                           | Significant retained information                   |
| ---------------------- | ------------------------------------ | -------------------------------------------------- |
| `LatexCharsNode`       | Ordinary character sequences         | Original characters                                |
| `LatexGroupNode`       | Braced or otherwise delimited groups | Nested nodes, opening/closing delimiters           |
| `LatexMacroNode`       | Commands such as `\frac`             | Macro name, parsed arguments, following whitespace |
| `LatexEnvironmentNode` | `\begin{...}` blocks                 | Environment name, arguments, body nodes            |
| `LatexMathNode`        | Delimited inline/display mathematics | Math type, delimiters, nested expression           |
| `LatexCommentNode`     | `%` comments                         | Comment text, following whitespace                 |
| `LatexSpecialsNode`    | Special character sequences          | Recognized sequence, optional parsed arguments     |

An important distinction: mathematical environments such as `equation` are represented as `LatexEnvironmentNode`, while delimiter-based mathematics such as `$...$` are represented as `LatexMathNode`. A processor that needs complete mathematical coverage must account for both.

Nodes also retain the original source span, which makes the parser useful for more than semantic text extraction.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation+1



### 3.3 Source provenance and exact markup recovery

Every node carries:

- `pos`: its starting offset in the original source.
- `len`: the length of its source span in 2.x.
- `parsing_state`: the context in which it was parsed.
- `latex_verbatim()`: the exact original source substring represented by that node.

This gives pylatexenc two complementary representations of a document: interpreted structure and original source text.

That combination supports general operations such as source-aware diagnostics, structural extraction with provenance, targeted rewriting, and preservation of markup that a converter would otherwise discard.

It is especially important that `latex_verbatim()` retrieves original code rather than reconstructing LaTeX from interpreted node attributes.

Consequently, a caller can inspect a macro structurally while retaining its original spelling, whitespace, delimiters, and argument formatting.

Reference: [https://pylatexenc.readthedocs.io/en/v2.10/latexwalker/](https://pylatexenc.readthedocs.io/en/v2.10/latexwalker/?utm_source=chatgpt.com)

### 3.4 Error handling and incomplete inputs

Stable 2.x exposes `tolerant_parsing` and `strict_braces`.

In tolerant mode, the parser generally attempts to continue after syntax errors. In stricter operation, `LatexWalkerParseError` provides error information including source position and line/column coordinates.

This distinction is useful for different workloads:

- Exploratory ingestion can tolerate imperfect documents and recover available structure.
- Structural validation can reject malformed constructs that would otherwise be accepted.
- Source-aware editors and analyzers can use the reported coordinates to identify problematic input.

However, tolerant parsing is not a proof of syntactic correctness. Successful recovery does not establish that the resulting tree represents the author's intended TeX semantics.

The parser's behavior also depends on its registered macro and environment specifications. An unknown construct can produce a plausible tree with incorrectly associated arguments.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation+2



## 4. Declarative LaTeX syntax and grammar customization — `macrospec`

This is one of pylatexenc's most valuable capabilities beyond basic text conversion.

LaTeX macros have heterogeneous argument conventions. Some accept mandatory arguments, optional brackets, starred variants, or special delimiters. Others change parsing behavior within their arguments.

`macrospec` separates these syntactic definitions from the central parser.

### 4.1 Macro, environment, and specials specifications

The three principal classes are:

| Class             | Responsibility                                                      |
| ----------------- | ------------------------------------------------------------------- |
| `MacroSpec`       | Describe a macro's name and argument structure                      |
| `EnvironmentSpec` | Describe an environment's name, arguments, and math-mode behavior   |
| `SpecialsSpec`    | Recognize arbitrary special character sequences and their arguments |

In stable 2.x, the standard argument grammar uses a compact syntax:

| Symbol | Meaning                                            |
| ------ | -------------------------------------------------- |
| `{`    | Mandatory argument, potentially a single TeX token |
| `[`    | Optional bracket-delimited argument                |
| `*`    | Optional starred form                              |

For example:

```
from pylatexenc.macrospec import MacroSpecspec = MacroSpec("customcmd", "*[{{")
```

This declares a macro with an optional star, an optional bracket argument, and two required arguments.

The parser records the resulting argument nodes in `node.nodeargd`, normally a `ParsedMacroArgs` instance. Optional arguments that were not supplied are represented by `None` entries, preserving positional correspondence with the declared signature.

Subtle distinction: The star in `\command*` can be an optional macro argument. But in `\begin{equation*}`, the star is part of the environment name. These require different definitions.

Reference: [https://pylatexenc.readthedocs.io/en/v2.10/macrospec/](https://pylatexenc.readthedocs.io/en/v2.10/macrospec/?utm_source=chatgpt.com)

### 4.2 Custom argument parsers

Not all LaTeX constructs fit the standard argument grammar.

`MacroStandardArgsParser` provides a reusable parser for ordinary signatures and a subclassing point for more complicated ones.

Two less obvious capabilities are particularly useful:

Argument-specific math mode: The `args_math_mode` parameter lets individual arguments be parsed in math mode, text mode, or the current mode. This matters for commands whose arguments have different syntactic conventions.

Whitespace-sensitive optional arguments: `optional_arg_no_space` controls whether whitespace may appear before a bracketed optional argument. This is relevant to commands such as the AMS mathematics line-break command, where a subsequent bracket does not always indicate an optional argument.

For nonstandard syntax, a custom `parse_args()` implementation can inspect the walker, read the appropriate source region, and return a custom `ParsedMacroArgs` subclass.

pylatexenc also provides `VerbatimArgsParser` and `ParsedVerbatimArgs`, covering constructs such as `\verb|...|` and verbatim environments.

These mechanisms allow specialized syntax recognition to remain localized rather than requiring modifications to the general parser.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation+2



### 4.3 `LatexContextDb`: the syntax registry

`LatexContextDb` stores categorized definitions of known macros, environments, and specials.

It supports:

- Ordered category registration through `add_context_category()`.
- Definition overriding with `prepend=True`, `insert_before`, and `insert_after`.
- Lookup using `get_macro_spec()`, `get_environment_spec()`, and `get_specials_spec()`.
- Category filtering using `filter_context()` in 2.x.
- Iteration over registered specifications.
- Configurable fallback specifications for unknown constructs.

Category precedence is significant: the first matching registered definition determines which signature is used.

The database supports a form of declarative grammar composition. Different LaTeX dialects, package conventions, or document families can be represented by different context configurations without duplicating the core parser.

There is also a consequential lifecycle constraint. In 2.x, the database is intended to be pseudo-immutable once supplied to a parser. Mutating it afterward can alter contextual information referenced by existing nodes. The official documentation recommends deriving new contexts rather than modifying contexts already in use.

Version 3 introduces a stronger explicit freezing and extension model, discussed later.

Reference: [https://pylatexenc.readthedocs.io/en/v2.10/macrospec/](https://pylatexenc.readthedocs.io/en/v2.10/macrospec/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation+2



### 4.4 Why the context registry matters

A LaTeX parser cannot reliably infer macro argument structure from braces alone.

Consider a hypothetical macro with two required arguments. Without knowledge of that signature, a generic parser might identify the command and then treat the following groups as unrelated structural nodes.

By registering the signature, the parser can associate those groups with the macro invocation.

This is an architectural distinction:

Generic token recognition → declared argument grammar → structurally meaningful nodes.

The benefit extends to text conversion, custom extraction, tree traversal, and analysis of mathematical notation. All can operate on the same recognized structure rather than independently rediscovering argument boundaries.

The limitation is equally important: a grammar specification declares how a construct is parsed, not what it means or how TeX would execute it.

## 5. LaTeX-to-Unicode conversion — `latex2text`

### 5.1 Text conversion is a structural interpretation

`LatexNodes2Text` consumes the node structure produced by `latexwalker` and emits a readable Unicode approximation.

```
from pylatexenc.latex2text import LatexNodes2Texttext = LatexNodes2Text().latex_to_text(    r"\textbf{Temperature}: $25\,^\circ\mathrm{C}$")
```

This operation recognizes common LaTeX symbols, accents, formatting commands, and mathematical constructs. It can produce text suitable for indexing and downstream linguistic analysis without compiling the document.

The module also exposes lower-level conversion entry points:

- `nodelist_to_text()` converts an existing collection of parsed nodes.
- `node_to_text()` converts an individual node.
- `node_arg_to_text()` converts a specified argument of a macro or environment.
- Specialized methods such as `macro_node_to_text()`, `environment_node_to_text()`, and `math_node_to_text()` provide narrower conversion behavior and customization points.

Because parsing and conversion are separate, the same syntax tree can feed different text representations without reparsing, provided their interpretation rules are compatible with the tree's argument structure.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation+1



Reference: [https://pylatexenc.readthedocs.io/en/v2.10/latex2text/](https://pylatexenc.readthedocs.io/en/v2.10/latex2text/?utm_source=chatgpt.com)

### 5.2 Mathematics and representation choices

Mathematical expressions expose a central tradeoff: readability versus preservation of original notation.

In stable 2.x, `LatexNodes2Text` supports four math modes:

| `math_mode`       | Behavior                                                    | Useful distinction                                     |
| ----------------- | ----------------------------------------------------------- | ------------------------------------------------------ |
| `text`            | Convert mathematics into approximate ordinary text; default | Human-readable extraction                              |
| `with-delimiters` | Convert contents while retaining original math delimiters   | Keep math-region boundaries visible                    |
| `verbatim`        | Preserve original mathematical markup                       | Avoid lossy conversion of equations                    |
| `remove`          | Exclude math regions                                        | Text-only processing that intentionally omits formulas |

The converter recognizes numerous mathematical symbols and operations. It also has basic support for matrices and arrays, rendering them as compact one-line text representations.

However, text conversion does not produce a symbolic mathematical AST suitable for algebraic equivalence, differentiation, or rigorous equation manipulation.

For instance, distinctions involving fraction layout, implicit multiplication, operator precedence, and multidimensional mathematical notation can be weakened or lost in plain text.

For scientific-document processing, this makes the combination of structured node extraction plus selective verbatim preservation more expressive than plain-text conversion alone.

Version 3 adds a materially different `fancy` math renderer; see Section 8.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation+1



### 5.3 Whitespace, comments, groups, and formatting

The converter exposes several controls that can materially change downstream results.

| Option                      | Effect                                                       |
| --------------------------- | ------------------------------------------------------------ |
| `strict_latex_spaces`       | Controls how closely whitespace handling follows LaTeX rules |
| `fill_text`                 | Reflow plain-text character blocks to a target width         |
| `keep_comments`             | Preserve or discard `%` comments                             |
| `keep_braced_groups`        | Preserve grouping braces in output                           |
| `keep_braced_groups_minlen` | Retain braces selectively based on converted group length    |

Whitespace handling is more sophisticated than a Boolean switch. `strict_latex_spaces` accepts presets including `based-on-source`, `macros`, and `except-in-equations`, or a dictionary controlling individual situations such as whitespace after comments and between LaTeX constructs.

This matters because TeX often consumes source whitespace after control words, while readable extracted text may benefit from preserving some of that separation.

The stable 2.x default is `macros`, following a correction made in version 2.6.

These options affect observable output, so a text corpus or comparison pipeline should regard the converter configuration as part of the text's interpretation semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation



### 5.4 Custom semantic replacement rules

The principal extension classes are:

- `MacroTextSpec`
- `EnvironmentTextSpec`
- `SpecialsTextSpec`

Each describes how a recognized LaTeX construct is converted to Unicode.

`MacroTextSpec` supports literal text substitutions, positional placeholders such as `%(1)s`, and Python callables that inspect the parsed macro node. An environment's body can be addressed with `%(body)s`.

For a compact example, suppose `\keyterm{signal}` should be interpreted as the word `signal`:

```
from pylatexenc import latexwalker, latex2text, macrospecparse_db = latexwalker.get_default_latex_context_db()parse_db.add_context_category(    "custom",    prepend=True,    macros=[macrospec.MacroSpec("keyterm", "{")],)text_db = latex2text.get_default_latex_context_db()text_db.add_context_category(    "custom",    prepend=True,    macros=[        latex2text.MacroTextSpec(            "keyterm",            simplify_repl="%(1)s",        )    ],)walker = latexwalker.LatexWalker(    r"\keyterm{signal}",    latex_context=parse_db,)nodes, _, _ = walker.get_latex_nodes()text = latex2text.LatexNodes2Text(    latex_context=text_db).nodelist_to_text(nodes)
```

Illustrative stable-2.x API composition; not executed here.

The important feature is the two independently configurable registries:

1. The parsing registry determines that `\keyterm` takes one argument.
2. The conversion registry determines that its argument becomes the output text.

Callable replacements can implement more complex transformations based on arguments, environment bodies, or nested node conversion.

`SpecialsTextSpec` also permits conversions at recognized syntactic boundaries, rather than applying unrestricted substitutions after text has already been generated. This can avoid inadvertently altering output produced by unrelated macros.

Reference: [https://pylatexenc.readthedocs.io/en/v2.10/latex2text/](https://pylatexenc.readthedocs.io/en/v2.10/latex2text/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation



### 5.5 Resolving `\input` and `\include`

A less obvious capability is controlled processing of files referenced by LaTeX input directives.

By default, `LatexNodes2Text` ignores `\input` and `\include`.

To enable file resolution, it provides:

```
converter.set_tex_input_directory(    tex_input_directory,    strict_input=True,)
```

The default resolver restricts referenced files to the designated directory tree when `strict_input=True`, checking canonical paths and resolved symbolic links.

The `read_input_file(filename)` method can also be overridden to retrieve content from a different source, such as an application-controlled document store.

This is significant because it allows document-level text conversion to operate across multiple input files without requiring an external TeX compilation process.

Two boundaries matter:

- This is input resolution during text conversion, not general TeX macro expansion or full document execution.
- The directory constraint is not a complete security sandbox. Resource consumption, recursive inputs, and custom resolver behavior still require appropriate controls for untrusted content.

Reference: [https://pylatexenc.readthedocs.io/en/v2.10/latex2text/](https://pylatexenc.readthedocs.io/en/v2.10/latex2text/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation



## 6. Unicode-to-LaTeX encoding — `latexencode`

### 6.1 Encoding model

`latexencode` performs the opposite transformation: it maps Unicode strings into LaTeX representations.

```
from pylatexenc.latexencode import unicode_to_latexunicode_to_latex("À votre santé")# r"\`A votre sant\'e"
```

Unlike a generic character-escaping function, this encoder knows mappings for many accents, mathematical symbols, and special LaTeX characters.

It also escapes ASCII characters that have structural significance in LaTeX, such as `#`, `&`, `$`, and `%`, unless explicitly configured otherwise.

The two primary interfaces are:

| Interface               | Use                                                        |
| ----------------------- | ---------------------------------------------------------- |
| `unicode_to_latex()`    | Simple, convenient string conversion                       |
| `UnicodeToLatexEncoder` | Reusable configured encoder with custom rules and policies |

For repeated conversions, `UnicodeToLatexEncoder` prepares its rules during construction and reuses them for subsequent strings. The convenience function also caches encoder instances for supported hashable argument combinations.

The configuration is intentionally established when the encoder is created rather than changed afterward.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation+1



Reference: [https://pylatexenc.readthedocs.io/en/v2.10/latexencode/](https://pylatexenc.readthedocs.io/en/v2.10/latexencode/?utm_source=chatgpt.com)

### 6.2 Extensible Unicode conversion rules

The rule engine supports three types of conversions.

| Rule type       | Mechanism                                            | Distinctive capability                                     |
| --------------- | ---------------------------------------------------- | ---------------------------------------------------------- |
| `RULE_DICT`     | Unicode code-point → LaTeX string dictionary         | Efficient character-specific mappings                      |
| `RULE_REGEX`    | Regular-expression matching and substitution         | Recognize and convert multicharacter patterns              |
| `RULE_CALLABLE` | Python function receiving source string and position | Context-dependent encoding and variable-length consumption |

A callable rule can return `(consumed_length, replacement_string)`, enabling a single rule to replace more than one input character.

Rules are ordered and applied until a matching replacement is found. Custom rules can precede built-in rules to override their behavior, while leaving the defaults available as a fallback.

Built-in conversion collections include:

- `defaults`: pylatexenc's curated Unicode-to-LaTeX mappings.
- `unicode-xml`: mappings derived from the Unicode/XML entity-name resource.

The `get_builtin_conversion_rules()` and `get_builtin_uni2latex_dict()` functions expose these resources for inspection and composition.

This makes the encoder useful as a configurable transformation engine, not merely a fixed character lookup table.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation



### 6.3 LaTeX replacement protection

Replacing a Unicode character with a LaTeX command can create an invalid token boundary.

For example, inserting a control word immediately before ordinary letters may cause TeX to interpret the following letters as part of the command name.

The `replacement_latex_protection` option addresses this problem.

| Policy               | Behavior                                            |
| -------------------- | --------------------------------------------------- |
| `braces`             | Protect potentially ambiguous replacements; default |
| `braces-all`         | Enclose every replacement in braces                 |
| `braces-almost-all`  | Enclose nearly every backslash-based replacement    |
| `braces-after-macro` | Add empty braces after vulnerable control words     |
| `none`               | Disable protection                                  |
| Callable             | Implement custom protection logic                   |

Since 2.10, individual `UnicodeToLatexConversionRule` instances can override the encoder's global protection policy.

The significance is that encoding correctness depends on the interaction between a replacement and its neighboring text, not only on the character being replaced.

Reference: [https://pylatexenc.readthedocs.io/en/v2.10/latexencode/](https://pylatexenc.readthedocs.io/en/v2.10/latexencode/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation+1



### 6.4 Unknown characters and output guarantees

The `unknown_char_policy` parameter determines how to handle characters for which no mapping exists.

Supported policies include:

- `keep`: retain the original character; default.
- `replace`: substitute a conspicuous question-mark representation.
- `ignore`: omit the character.
- `fail`: raise `ValueError`.
- `unihex`: output a textual Unicode code-point representation.
- Callable: provide custom fallback behavior.

`unknown_char_warning` independently controls whether warnings are emitted.

Two choices have particularly important consequences:

`non_ascii_only=True` does not escape ASCII LaTeX metacharacters. It is suitable for some already-structured inputs, but not as a general-purpose escaping policy for arbitrary literal text.

`unknown_char_policy='keep'` does not guarantee compatibility with a particular TeX engine, font, or package set. It retains characters that may require Unicode-aware typesetting support.

The encoder therefore provides configurable conversion behavior, not a universal guarantee of compilable LaTeX output.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 2.10 documentation



### 6.5 Mixed LaTeX and Unicode input

Version 2.10 introduced `PartialLatexToLatexEncoder`, an easily overlooked capability for strings that already contain some LaTeX expressions.

Its purpose is to avoid double-escaping recognized existing LaTeX while encoding the remaining text.

This is distinct from encoding an entirely literal Unicode string. It is useful when a string combines ordinary prose with fragments intended to remain as LaTeX markup.

However, preserving recognized snippets should not be confused with fully parsing, validating, or executing arbitrary LaTeX. Correct handling still depends on the kinds of embedded constructs encountered.

The older `utf8tolatex()` function also remains available for compatibility with pylatexenc 1.x. Official documentation recommends the newer encoding interfaces; it does not formally mark `utf8tolatex()` as deprecated.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 3.0beta2 documentation+1



Additional encoder extension: `latex_string_class` permits a custom appendable output object instead of a single string, making it possible to retain emitted conversion chunks individually.

## 7. Command-line utilities, packaging, and integration

### 7.1 CLI interfaces

pylatexenc distributes three useful commands:

| Command       | Function                              | Representative use                         |
| ------------- | ------------------------------------- | ------------------------------------------ |
| `latex2text`  | Convert LaTeX to Unicode text         | Document ingestion, text inspection        |
| `latexencode` | Encode Unicode into LaTeX             | Preparing literal text for LaTeX documents |
| `latexwalker` | Parse LaTeX and display its node tree | Structural inspection, parser diagnostics  |

The first two support stdin-to-stdout pipelines and file inputs. `latexwalker` additionally supports machine-readable JSON output:

```
latexwalker --output-format=json \
  --code '\textbf{Example} and $x^2$'
```

This exposes parser structure without requiring a Python wrapper.

The JSON format is useful for diagnostics and prototyping external integrations. However, the schema changes between major versions, particularly in version 3, so it should not be treated as a version-independent interchange protocol.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 3.0beta2 documentation+2



### 7.2 Distribution and dependencies

The package is MIT-licensed and designed without runtime third-party Python dependencies. It does not require an installed TeX engine for its core functionality.

The stable 2.11 release provides a platform-independent Python wheel marked for Python 2 and 3 compatibility. The 3.0 beta drops Python 2 and declares Python 3.6 or newer.

The upstream repository also contains a Transcrypt-based JavaScript transcription of some core functionality. That is an associated source-level integration, not evidence that the standard Python package offers a general-purpose JavaScript execution interface.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+2



References:

[https://pypi.org/project/pylatexenc/](https://pypi.org/project/pylatexenc/?utm_source=chatgpt.com)

[https://github.com/phfaist/pylatexenc](https://github.com/phfaist/pylatexenc?utm_source=chatgpt.com)

## 8. Version 3 architecture — currently prerelease

The 3.0 beta substantially expands pylatexenc's role from a configurable LaTeX parser into a composable, state-aware parsing framework.

These features are documented for 3.0b2, not included in stable 2.11.

### 8.1 Parser objects and the generalized parsing interface

The most consequential change is the introduction of `pylatexenc.latexnodes.parsers`.

Rather than embedding most parsing behavior directly into the walker, version 3 delegates interpretation of specific constructs to parser objects.

The new entry point is:

```
from pylatexenc.latexwalker import LatexWalkerfrom pylatexenc.latexnodes.parsers import LatexGeneralNodesParserwalker = LatexWalker(latex_source)nodes, state_delta = walker.parse_content(    LatexGeneralNodesParser())
```

`LatexParserBase` is the extensibility contract. A parser implements `parse(latex_walker, token_reader, parsing_state, ...)` and returns a parsed object plus any resulting parsing-state delta.

The reusable parser family is broader than ordinary groups and macro calls.

| Parser                                   | Capability                                                        |
| ---------------------------------------- | ----------------------------------------------------------------- |
| `LatexGeneralNodesParser`                | Parse general LaTeX content with configurable stopping conditions |
| `LatexSingleNodeParser`                  | Parse one structural node                                         |
| `LatexExpressionParser`                  | Parse an expression, optionally including a macro's arguments     |
| `LatexDelimitedGroupParser`              | Parse groups using configured delimiters                          |
| `LatexDelimitedMultiDelimGroupParser`    | Accept several possible delimiter pairs                           |
| `LatexMathParser`                        | Parse a delimited mathematical expression                         |
| `LatexOptionalSquareBracketsParser`      | Recognize optional bracket arguments                              |
| `LatexOptionalCharsMarkerParser`         | Parse markers such as a star or other designated characters       |
| `LatexOptionalEmbellishmentArgsParser`   | Parse embellishments such as superscript/subscript forms          |
| `LatexDelimitedVerbatimParser`           | Parse literal content without normal LaTeX interpretation         |
| `LatexVerbatimEnvironmentContentsParser` | Parse verbatim environment bodies                                 |
| `LatexCharsGroupParser`                  | Parse group contents as character-oriented input                  |
| `LatexCharsCommaSeparatedListParser`     | Parse protected comma-delimited character lists                   |

The parser framework supports composing recognized syntax from specialized parsers, including cases where ordinary LaTeX tokenization should be temporarily suppressed.

`LatexGeneralNodesParser` uses `LatexNodesCollector`, which delegates identified macros, environments, and other constructs to the appropriate specialized parsers. The collector itself also exposes customization methods.

This can reduce the need for bespoke scanners when building LaTeX-adjacent markup processors with nonstandard argument conventions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 3.0beta2 documentation+2



References:

[https://pylatexenc.readthedocs.io/en/latest/latexnodes.parsers/](https://pylatexenc.readthedocs.io/en/latest/latexnodes.parsers/?utm_source=chatgpt.com)

[https://pylatexenc.readthedocs.io/en/latest/latexwalker/](https://pylatexenc.readthedocs.io/en/latest/latexwalker/?utm_source=chatgpt.com)

### 8.2 Parsing state and configurable tokenization

Version 3 expands `ParsingState` beyond tracking ordinary text and mathematical context.

It can control:

- Which delimiters represent groups, inline math, and display math.
- Whether macros, environments, groups, comments, specials, and mathematics are recognized.
- Which characters are valid in multi-character macro names.
- The macro escape character and comment-start character.
- Whether blank lines are recognized as paragraph breaks.
- Characters that should be explicitly rejected during tokenization.

This supports controlled LaTeX-like dialects. For example, a parser can deliberately prohibit particular constructs, alter how selected characters are tokenized, or interpret an argument as literal characters rather than normal markup.

Token reading is separately represented through `LatexTokenReader` and its base interface. `LatexTokenListTokenReader` can consume an already-tokenized list, separating token production from structural parsing when that distinction is valuable.

The architectural benefit is localized syntax configuration without replacing the entire parsing engine. It does not make arbitrary TeX catcode manipulation or macro execution automatically available.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 3.0beta2 documentation+1



### 8.3 Parsing-state deltas and dynamic grammar extension

The other major change is explicit handling of state transitions.

`ParsingStateDelta` represents changes caused by parsing a construct. Such a delta can alter the subsequent parsing context rather than requiring a preconfigured, globally fixed grammar.

In particular, `ParsingStateDeltaExtendLatexContextDb` supports extending the current macro, environment, and specials definitions.

A specialized parser can therefore interpret a declaration and publish additional syntax definitions to be used when parsing later content.

This is relevant to LaTeX documents that introduce their own commands or environments.

The mechanism has an important limitation: the ability to register state changes does not imply that pylatexenc fully executes `\newcommand`, `\def`, package loading, or other TeX programming constructs. The necessary interpretation of those declarations still depends on the parser and associated specifications.

Version 3 also introduces a more explicit lifecycle for `LatexContextDb`:

1. Assemble definitions through `add_context_category()`.
2. Freeze the context with `freeze()`.
3. Derive modified contexts using `extended_with()` or `filtered_context()`.

`extended_with()` requires a frozen original context. These APIs make contextual definitions easier to share and extend in a controlled manner.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 3.0beta2 documentation+1



Reference: [https://pylatexenc.readthedocs.io/en/latest/macrospec/](https://pylatexenc.readthedocs.io/en/latest/macrospec/?utm_source=chatgpt.com)

### 8.4 More expressive argument grammars

The 2.x grammar is extended in version 3 through `LatexStandardArgumentParser` and `LatexArgumentSpec`.

The grammar is inspired by LaTeX's `xparse`, but should not be assumed to implement every `xparse` feature.

| Specification          | Meaning                                                    |
| ---------------------- | ---------------------------------------------------------- |
| `m` or `{`             | Required argument                                          |
| `o` or `[`             | Optional bracket argument                                  |
| `s` or `*`             | Optional star                                              |
| `t<char>`              | Optional designated-character marker                       |
| `r<char1><char2>`      | Required argument using specified delimiters               |
| `d<char1><char2>`      | Optional argument using specified delimiters               |
| `e{<chars>}`           | Optional embellishments introduced by specified characters |
| `v`                    | Verbatim argument with dynamically chosen delimiters       |
| `v<char1><char2>`      | Verbatim argument with explicit delimiters                 |
| `AnyDelimited`         | Required argument accepting several delimiter-pair types   |
| `AnyDelimitedOptional` | Optional equivalent                                        |

`LatexArgumentSpec` associates each argument with its own parser, optional name, and parsing-state adjustment.

`ParsedArguments` stores parsed values, while `ParsedArgumentsInfo` provides higher-level access, including lookup by argument name.

The ability to name arguments reduces dependence on positional indexes when a macro signature evolves. More importantly, each argument can have its own grammar and parsing context, allowing a macro to combine ordinary LaTeX content, literal strings, metadata, and custom-delimited regions.

The specification objects also expose hooks such as `get_node_parser()`, `make_body_parser()`, `make_arguments_parsing_state_delta()`, `make_body_parsing_state_delta()`, `make_after_parsing_state_delta()`, and `finalize_node()`.

Together, these enable macro- and environment-specific parsing behavior without modifying the generic walker.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 3.0beta2 documentation+2



### 8.5 `LatexNodeList`: structural collection operations

In version 3, parsed node sequences are represented by `LatexNodeList` rather than ordinary Python lists.

Besides retaining source spans and context, the class provides several useful structural operations:

| Method                   | Capability                                                                |
| ------------------------ | ------------------------------------------------------------------------- |
| `filter()`               | Select nodes using a predicate and optional comment/whitespace exclusions |
| `split_at_node()`        | Divide a sequence at selected structural nodes                            |
| `split_at_chars()`       | Divide at characters or regular-expression matches within character nodes |
| `parse_keyval_content()` | Parse LaTeX-style comma-separated key/value arguments                     |
| `get_content_as_chars()` | Extract character-oriented content from suitable nested nodes             |
| `latex_verbatim()`       | Retrieve source markup represented by the nodes                           |

Two methods deserve particular attention.

`split_at_chars()` is structure-aware. Given a citation argument such as `\cite{key1,key2,my{special,key},keyN}`, it can split at commas in character nodes without splitting the comma inside the nested group.

`parse_keyval_content()` recognizes protected delimiters. Commas and equals signs inside nested nodes are not treated as separators at the containing level. The method supports configurable repeated-key behavior, including error, first, last, concatenation, and custom aggregation.

These operations address common needs in LaTeX metadata, package options, citation lists, custom command arguments, and other text-with-embedded-structure formats.

They can replace significant amounts of ad hoc string splitting and brace-depth tracking.

One compatibility caveat: `LatexNodeList` behaves much like a list, but is not itself an instance of the built-in Python `list` class.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 3.0beta2 documentation+2



Reference: [https://pylatexenc.readthedocs.io/en/latest/latexnodes.nodes/](https://pylatexenc.readthedocs.io/en/latest/latexnodes.nodes/?utm_source=chatgpt.com)

### 8.6 Visitor-based traversal and LaTeX recomposition

Version 3 supplies two complementary capabilities.

`LatexNodesVisitor` provides traversal of the parsed tree, with callbacks for different node types. It descends into macro arguments, environment arguments and bodies, groups, and mathematics. Visitor callbacks can also return values for aggregation by enclosing visits.

This supports operations such as extracting citations, collecting references and labels, finding macros, and performing structured analysis without writing a separate recursive traversal framework.

`LatexNodesLatexRecomposer` generates LaTeX code from a node tree's stored structure.

```
from pylatexenc.latexnodes import LatexNodesLatexRecomposerlatex = LatexNodesLatexRecomposer().latex_recompose(nodes)
```

The distinction from `latex_verbatim()` is critical:

| Mechanism                   | Source of output             | Principal use                             |
| --------------------------- | ---------------------------- | ----------------------------------------- |
| `node.latex_verbatim()`     | Original LaTeX source string | Recover exact source fragments            |
| `LatexNodesLatexRecomposer` | Fields of the node tree      | Generate LaTeX from represented structure |
| `LatexNodes2Text`           | Semantic conversion rules    | Produce readable Unicode text             |

The recomposer can operate on transformed or programmatically constructed trees without consulting the original source string.

However, it is not a lossless round-trip guarantee. The official documentation explicitly notes that reparsing recomposed LaTeX need not produce the same tree. Whitespace around paragraph breaks, for example, may be normalized.

The recomposer also provides overridable methods for different node types, allowing customized LaTeX serialization policies.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 3.0beta2 documentation+1



### 8.7 Improved mathematical and text rendering

Version 3 introduces `math_mode='fancy'` as the new default.

Relative to 2.x, it improves spacing and produces more readable one-dimensional representations of formulas.

For example, the documented output of:

```
$\frac{4 \pi c}{2}\sin(x+y)$
```

is rendered approximately as:

```
(4π𝑐)/2 sin(𝑥 + 𝑦)
```

Additional capabilities include Unicode mathematical fonts, available superscript/subscript glyphs, and improved treatment of roots and mathematical operators.

Text formatting may also be reflected through Unicode styled alphabets. For example, a bold LaTeX text command can produce Unicode bold mathematical-style characters.

These changes are visually useful but potentially consequential for search indexing, normalization, equality checks, and compatibility with downstream text-processing libraries.

To approximate the 2.x conversion behavior in version 3:

```
converter = LatexNodes2Text(    math_mode="text",    math_fontstyle=None,    text_fontstyle=False,)
```

These are explicitly documented compatibility settings, not a guarantee that every output difference between releases disappears.

Version 3 also introduces `TextConversionState`, accessible through the converter's `state` attribute, for context-dependent formatting.

This supports improved nested list rendering, including numbering, nesting-dependent markers, and alignment of multiline list items.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 3.0beta2 documentation+1



Reference: [https://pylatexenc.readthedocs.io/en/latest/latex2text/](https://pylatexenc.readthedocs.io/en/latest/latex2text/?utm_source=chatgpt.com)

### 8.8 Error recovery and compatibility changes

The beta expands the error model with `LatexWalkerLocatedError`, `LatexWalkerNodesParseError`, and `LatexWalkerTokenParseError`.

These provide more specific categories and source-location information, together with recovery-related context in the lower-level parser framework.

Additional migration-sensitive changes include:

| Area                                   | Version 2.x                               | Version 3.0 beta                                       |
| -------------------------------------- | ----------------------------------------- | ------------------------------------------------------ |
| Primary parsing entry point            | `get_latex_nodes()`                       | `parse_content()`; legacy API retained                 |
| Node sequences                         | Ordinary lists                            | `LatexNodeList`                                        |
| Node span                              | `pos` and `len`                           | `pos` and `pos_end`; `len` compatibility property      |
| Macro argument representation          | `ParsedMacroArgs`                         | `ParsedArguments` with compatible alias                |
| Context filtering                      | `filter_context()`                        | `filtered_context()`                                   |
| Custom argument parsing                | `MacroStandardArgsParser`                 | Individual parser objects and argument specs           |
| Math-to-text default                   | `text`                                    | `fancy`                                                |
| Paragraph breaks, `^`, `_`             | Typically included within character nodes | Special nodes under the default context                |
| Unknown definitions in custom contexts | More permissive fallback                  | May produce errors unless unknown specs are configured |
| CLI JSON structure                     | 2.x representation                        | Changed node serialization structure                   |

The library preserves many legacy interfaces, but compatibility of method calls does not imply identical node structure or text output.

Reference: [https://pylatexenc.readthedocs.io/en/latest/new-in-pylatexenc-3/](https://pylatexenc.readthedocs.io/en/latest/new-in-pylatexenc-3/?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 3.0beta2 documentation+2



## 9. Architectural combinations and system boundaries

The library's capabilities are most useful when considered as interacting layers rather than unrelated utilities.

LaTeX source

Original markup and source positions

Syntax recognition

LatexWalker + macrospec + LatexContextDb

Structured node representation

Arguments · environments · math · provenance

Unicode text

latex2text

Structure analysis

Traversal and extraction

LaTeX output

Source spans / v3 recomposer

`latexencode` complements this flow as an independent Unicode-to-LaTeX transformation layer; it does not require a previously parsed LaTeX tree.

Three combinations are particularly significant.

### 9.1 Parse once, interpret in multiple ways

A node tree can be used for structural extraction, text normalization, and source-aware reporting.

For example, a document processor could retain exact formula markup, convert prose to Unicode, extract citation arguments, and record source locations.

The substantive benefit is a single recognized syntax structure shared by several operations. This avoids independently parsing macro argument boundaries for each output.

The suitability depends on whether the registered grammar correctly models the constructs encountered.

### 9.2 Extend syntax and meaning independently

A new domain-specific command can be introduced with `MacroSpec` and then interpreted through `MacroTextSpec` or a visitor.

This separation is valuable because the same syntactic construct may need different representations: searchable text, structured metadata, source-aware diagnostics, or a transformed LaTeX expression.

No single converter has to own the definition of the command's syntax.

In version 3, custom parser objects and parsing-state deltas expand this further by allowing individual arguments and environments to employ different grammars.

### 9.3 Preserve source while producing lossy output

Plain-text conversion is useful precisely because it discards many markup details.

That same information loss makes it unsuitable as the sole representation when exact mathematical notation, source provenance, or faithful rewriting matters.

Retaining the node structure and original source alongside the converted text supports both human-readable outputs and higher-fidelity structural operations.

Version 3's recomposer adds an additional regeneration path, but it should be distinguished from exact source recovery.

## 10. Boundaries, tradeoffs, and limitations

| Dimension                   | Capability                                                                      | Important limitation                                              |
| --------------------------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| LaTeX syntax                | Recognizes common commands, groups, environments, comments, and math delimiters | Not a complete TeX interpreter                                    |
| Package-specific constructs | Extendable through syntax specifications                                        | Signatures and semantics may require explicit definitions         |
| Dynamic declarations        | State-aware extensions possible in 3.x                                          | Full macro execution is not supplied automatically                |
| Structural provenance       | Source spans and original markup recovery                                       | Converted text may lose substantial structure                     |
| Mathematical notation       | Recognizes math regions and many symbols                                        | Does not establish algebraic semantics                            |
| Unicode encoding            | Extensive mapping and configurable escaping                                     | Compilability depends on the TeX environment and policies         |
| Unknown constructs          | Configurable handling and tolerant parsing                                      | Recovery may produce incomplete or misleading structure           |
| Source reconstruction       | Node-driven recomposition in 3.x                                                | Not guaranteed to reproduce original code or parse identically    |
| Performance                 | Reusable encoders and lightweight parsing model                                 | No general throughput or memory guarantee for arbitrary documents |
| Interoperability            | Python APIs, CLI, JSON, extensible node objects                                 | No standardized stable cross-version AST interchange contract     |

### Where pylatexenc is especially distinctive

Its strongest functionality is the combination of LaTeX-aware structure, declarative grammar registration, configurable interpretation, and original-source retention.

For many extraction and transformation problems, that combination can avoid implementing a custom lexer, nested-brace parser, macro-argument recognizer, and text-conversion layer.

The 3.0 beta further reduces bespoke parsing requirements through individual parser objects, configurable tokenization, named arguments, structural collection utilities, and explicit parsing-state transitions.

### Where another class of engine is required

pylatexenc is not the appropriate final authority when an operation requires:

- Full TeX expansion, package execution, or exact typesetting behavior.
- A visual layout model of rendered equations and pages.
- Formal symbolic mathematics or guaranteed expression equivalence.
- Complete interpretation of arbitrary LaTeX programs.
- A security guarantee for executing untrusted TeX content.

These requirements belong to TeX engines, rendering systems, symbolic mathematics libraries, or other specialized processors. A pylatexenc-based syntactic front end may still be useful, but it cannot by itself supply those guarantees.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pylatexenc.readthedocs.io\&sz=32)

pylatexenc 3.0beta2 documentation+2



## 11. Primary-source reference map

| Subject                                        | Direct source                                                                                                                                               |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Stable release and distribution                | [https://pypi.org/project/pylatexenc/](https://pypi.org/project/pylatexenc/?utm_source=chatgpt.com)                                                         |
| Stable parsing API                             | [https://pylatexenc.readthedocs.io/en/v2.10/latexwalker/](https://pylatexenc.readthedocs.io/en/v2.10/latexwalker/?utm_source=chatgpt.com)                   |
| Stable grammar specifications                  | [https://pylatexenc.readthedocs.io/en/v2.10/macrospec/](https://pylatexenc.readthedocs.io/en/v2.10/macrospec/?utm_source=chatgpt.com)                       |
| Stable LaTeX-to-text conversion                | [https://pylatexenc.readthedocs.io/en/v2.10/latex2text/](https://pylatexenc.readthedocs.io/en/v2.10/latex2text/?utm_source=chatgpt.com)                     |
| Stable Unicode-to-LaTeX encoding               | [https://pylatexenc.readthedocs.io/en/v2.10/latexencode/](https://pylatexenc.readthedocs.io/en/v2.10/latexencode/?utm_source=chatgpt.com)                   |
| Version-specific release changes               | [https://pylatexenc.readthedocs.io/en/latest/changes/](https://pylatexenc.readthedocs.io/en/latest/changes/?utm_source=chatgpt.com)                         |
| Version 3 feature and compatibility guide      | [https://pylatexenc.readthedocs.io/en/latest/new-in-pylatexenc-3/](https://pylatexenc.readthedocs.io/en/latest/new-in-pylatexenc-3/?utm_source=chatgpt.com) |
| Version 3 parsing-state and token model        | [https://pylatexenc.readthedocs.io/en/latest/latexnodes/](https://pylatexenc.readthedocs.io/en/latest/latexnodes/?utm_source=chatgpt.com)                   |
| Version 3 specialized parsers                  | [https://pylatexenc.readthedocs.io/en/latest/latexnodes.parsers/](https://pylatexenc.readthedocs.io/en/latest/latexnodes.parsers/?utm_source=chatgpt.com)   |
| Version 3 node lists and visitors              | [https://pylatexenc.readthedocs.io/en/latest/latexnodes.nodes/](https://pylatexenc.readthedocs.io/en/latest/latexnodes.nodes/?utm_source=chatgpt.com)       |
| Version 3 macro and environment specifications | [https://pylatexenc.readthedocs.io/en/latest/macrospec/](https://pylatexenc.readthedocs.io/en/latest/macrospec/?utm_source=chatgpt.com)                     |
| Upstream implementation                        | [https://github.com/phfaist/pylatexenc](https://github.com/phfaist/pylatexenc?utm_source=chatgpt.com)                                                       |

Overall assessment: pylatexenc 2.11 is a capable, lightweight foundation for Unicode/LaTeX conversion and syntax-aware document processing. Its more powerful architectural opportunity is the configurable structural parser beneath those utilities. Version 3.0b2 extends that foundation substantially toward a modular LaTeX-like parsing framework, but those capabilities remain prerelease and should be evaluated separately from the stable 2.x contract.