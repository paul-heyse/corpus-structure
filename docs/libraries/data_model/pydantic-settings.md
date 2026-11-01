# pydantic-settings — Comprehensive Python Library Overview

Target version: 2.16.0 (latest stable release, October 14, 2026) Research date: October 20, 2026 Python: 3.11+ | Pydantic: 2.x | License: MIT

pydantic-settings is a typed application configuration framework built around Pydantic's validation and modeling capabilities. Its distinguishing feature is a composable configuration-source system that collects settings from environment variables, configuration files, command-line arguments, local or cloud secrets, and arbitrary custom sources, then resolves them into validated Python objects.

Version 2.16.0 adds several important capabilities, including native settings-instance caching, AWS Systems Manager Parameter Store integration, parent-directory dotenv discovery, and variadic named CLI arguments. It also changes Python compatibility and several source-resolution and alias-handling behaviors.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+1



Official resources:

- [Settings management documentation](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com)
- [API reference](https://pydantic.dev/docs/validation/latest/api/pydantic_settings/?utm_source=chatgpt.com)
- [Version 2.16.0 release notes](https://github.com/pydantic/pydantic-settings/releases/tag/v2.16.0?utm_source=chatgpt.com)
- [Upstream repository](https://github.com/pydantic/pydantic-settings?utm_source=chatgpt.com)

## 1. Architectural model and capability landscape

The most useful way to understand pydantic-settings is as a typed configuration resolution engine, not simply a convenience wrapper around `os.environ`.

It separates three concerns:

1. Configuration schema: A `BaseSettings` subclass defines fields, types, defaults, constraints, nested models, and cross-field invariants.
2. Configuration acquisition and resolution: An ordered collection of settings sources identifies configuration values, translates external representations into Python-compatible inputs, and combines contributions according to precedence.
3. Validation and consumption: Pydantic validates the resolved values and constructs a settings object that can be used as an ordinary typed model.

Conceptual execution pipeline

Configuration sources

Constructor · Environment · Dotenv · Files · CLI · Secrets · Custom providers

Source adapters and precedence resolution

Name and alias matching · Parsing · Nested merging · Priorities

Pydantic validation

Types · Constraints · Validators · Defaults · Model invariants

Validated settings model

Typed attributes · Nested objects · Serialization · Optional caching

The following capability families define the library's scope.

| Capability family          | Principal mechanisms                                                      |
| -------------------------- | ------------------------------------------------------------------------- |
| Typed configuration models | `BaseSettings`, `SettingsConfigDict`, Pydantic fields and validators      |
| Configuration resolution   | Ordered sources, `settings_customise_sources`, layered merging            |
| Environment configuration  | Prefixes, aliases, case matching, nested variables, JSON parsing          |
| Configuration files        | Dotenv, JSON, YAML, TOML, `pyproject.toml`                                |
| Secrets management         | Filesystem secrets, nested secrets, AWS, Azure, GCP                       |
| Command-line interfaces    | `CliSettingsSource`, `CliApp`, arguments, subcommands, parser integration |
| Extensibility              | Custom sources, source-state access, custom parsing                       |
| Lifecycle and diagnostics  | Instance caching, reloads, source debugging, validation errors            |

A central architectural advantage is that these are not independent parsing systems that must each recreate configuration semantics. They can contribute to a shared Pydantic model, reducing bespoke configuration loading, validation, conversion, and precedence logic.

Important boundary: pydantic-settings resolves and validates configuration. It is not a general distributed configuration service, synchronization system, secret-encryption engine, or automatic live-reconfiguration framework. Its cloud integrations retrieve provider-managed values but do not replace the providers' security, authorization, auditing, or lifecycle services.

## 2. Typed settings schemas and Pydantic integration

### 2.1 `BaseSettings` as a validated configuration model

`BaseSettings` inherits from Pydantic's `BaseModel`. Consequently, the settings schema can use the full Pydantic modeling system rather than implementing configuration-specific validation separately.

This includes constrained fields, enumerations, literal types, nested models, discriminated unions, custom scalar types, field validators, model validators, computed fields, and serialization.

A compact illustration:

```
from pydantic import BaseModel, Field, SecretStrfrom pydantic_settings import BaseSettings, SettingsConfigDictclass DatabaseConfig(BaseModel):    host: str = "localhost"    port: int = Field(default=5432, ge=1, le=65535)    pool_size: int = Field(default=10, ge=1)class Settings(BaseSettings):    model_config = SettingsConfigDict(        env_prefix="APP_",        env_nested_delimiter="__",        env_file=(".env", ".env.local"),    )    database: DatabaseConfig = DatabaseConfig()    worker_count: int = Field(default=4, ge=1)    api_token: SecretStr
```

This model can accept inputs such as:

```
APP_DATABASE__HOST=db.internal
APP_DATABASE__POOL_SIZE=20
APP_WORKER_COUNT=8
APP_API_TOKEN=example-secret
```

The resulting object has typed attributes (`settings.database.port`, `settings.worker_count`), and the same validation rules apply whether values originate from environment variables, files, or another configured source.

This makes Pydantic's larger type ecosystem relevant to application configuration. For example:

- `PostgresDsn`, `RedisDsn`, `AnyUrl`, and other Pydantic network types provide structured validation of connection addresses.
- `SecretStr` and `SecretBytes` protect values from accidental disclosure in ordinary string representations.
- `ImportString` resolves Python objects from import paths, enabling configuration of callables or classes.
- `Field` constraints and `model_validator` support cross-field configuration invariants.

A distinctive default: Unlike an ordinary Pydantic `BaseModel`, `BaseSettings` validates field defaults by default. `validate_default=False` can disable this globally or for a particular field. This matters because malformed default configuration is otherwise discoverable at construction time, even when no external override is supplied.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 2.2 Nested models and validation boundaries

Nested configuration is best expressed through ordinary `BaseModel` subclasses inside a top-level `BaseSettings` model. The official documentation specifically distinguishes this from nesting further `BaseSettings` classes, which can independently collect settings values and produce unexpected results.

This creates a useful separation:

- The top-level settings object owns the source-resolution boundary.
- Nested Pydantic models describe configuration subdomains.
- Pydantic validators enforce constraints at either level.
- Source configuration and precedence remain coordinated at the settings root.

Submodels can be reused across different settings classes and, because they are ordinary Pydantic models, across non-configuration inputs as well.

There is an important limitation: Pydantic's runtime validation entry points do not bypass settings acquisition. On `BaseSettings`, `model_validate()`, `model_validate_json()`, and `model_validate_strings()` still construct the model through its settings-aware initializer. Runtime arguments such as `strict`, `extra`, and `context` are not applied as they would be for an ordinary `BaseModel`; the model's configured validation behavior governs instead.

That distinction is consequential when a settings model is also being used as a general data-transfer schema.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Sources: [Pydantic settings usage and default validation](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#validation-of-default-values), [runtime validation arguments](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#runtime-validation-arguments).

## 3. Settings sources, precedence, and layered merging

### 3.1 Default source priority

With command-line parsing enabled, the built-in precedence order is:

| Priority    | Source                | Typical role                                |
| ----------- | --------------------- | ------------------------------------------- |
| 1 — highest | CLI arguments         | Per-invocation overrides                    |
| 2           | Constructor arguments | Explicit programmatic overrides             |
| 3           | Process environment   | Deployment and process-specific settings    |
| 4           | Dotenv files          | Local or environment-specific configuration |
| 5           | Filesystem secrets    | Mounted credentials and secret values       |
| 6 — lowest  | Model defaults        | Baseline configuration                      |

CLI parsing is opt-in, so the default configuration normally begins with constructor arguments.

This ordering is not hardcoded as an immutable policy. The `settings_customise_sources()` class method can reorder, replace, supplement, or remove source objects.

The built-in method receives:

```
settings_customise_sources(    settings_cls,    init_settings,    env_settings,    dotenv_settings,    file_secret_settings,)
```

It returns sources in descending priority. In the standard construction pipeline, a default-values source is appended after the returned sources.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 3.2 Deep merging across sources

The merging semantics are more powerful than simple first-source-wins replacement of entire configuration sections.

Suppose a lower-priority source supplies:

```
{
  "database": {
    "host": "db.example",
    "port": 5432,
    "pool_size": 10
  }
}
```

A higher-priority source supplies:

```
{
  "database": {
    "pool_size": 24
  }
}
```

The combined value can retain the lower-priority `host` and `port` while replacing `pool_size` with `24`.

This is deep merging across the contributions of separate settings sources. It allows a base configuration to supply a complete configuration structure while later sources override only selected leaves. The precise outcome still depends on aliases, whether the values were successfully recognized as belonging to the same fields, and nested-model default semantics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



The distinction enables several general design patterns without bespoke configuration-composition code: a packaged baseline with environment overrides, a configuration file supplemented by secrets, or CLI overrides layered over deployment defaults.

### 3.3 The source system as a policy boundary

A custom source order can express materially different policies. For example, placing the environment before constructor arguments means operational environment overrides can defeat explicitly passed Python values. Removing the dotenv source disables one avenue for reading local files. Adding a remote secrets source can supply otherwise missing values without giving it precedence over runtime overrides.

These are semantic decisions, not only implementation details. In particular, a source with high priority can override values from a supposedly authoritative provider.

When evaluating layered configuration, the two crucial questions are therefore:

1. Which source is allowed to override which other source?
2. At what structural level do values merge rather than replace one another?

Both are directly expressible using native source mechanisms.

Sources: [Field-value priority](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#field-value-priority), [customizing settings sources](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#customise-settings-sources).

## 4. Environment variable resolution and advanced parsing

Environment-variable support extends beyond simple uppercase-name matching.

### 4.1 Field names, aliases, and namespace mapping

The principal controls are:

| Mechanism                     | Behavior                                                                |
| ----------------------------- | ----------------------------------------------------------------------- |
| `env_prefix`                  | Prefixes field-derived environment names, defaulting to an empty string |
| `Field(validation_alias=...)` | Defines a field's accepted input name                                   |
| `Field(alias=...)`            | Supplies a general Pydantic alias that can also affect serialization    |
| `AliasChoices(...)`           | Supports multiple accepted input names, in priority order               |
| `env_prefix_target`           | Controls whether prefixes apply to field names, aliases, or both        |
| `case_sensitive`              | Controls source-name matching, defaulting to case-insensitive           |
| `env_nested_delimiter`        | Converts names into nested data structures                              |
| `env_nested_max_split`        | Limits delimiter-based nesting depth                                    |

The `env_prefix_target` setting is particularly useful when a model combines conventional internal field names and legacy or external aliases:

- `variable` — the default — applies the prefix to field-derived names, not aliases.
- `alias` applies it to alias names rather than ordinary field names.
- `all` applies it to both.

A frequent mistake is to assume that an alias automatically receives the configured `env_prefix`. Under the default behavior, it does not.

Another subtlety concerns aliases on nested model fields. Assigning an alias can restrict the prefixes accepted for the nested subtree, including when values originate from different sources. If one source uses the alias while another uses the original field name, expected merging may not occur. `AliasChoices` or Pydantic's `populate_by_name`/`validate_by_name` can deliberately allow both spellings.

In 2.16.0, `validation_alias` consistently takes precedence over `alias` in configuration-file and CLI parsing. The release also makes `validate_by_alias=False` apply across all settings sources, rather than leaving aliases active in some source adapters.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs

+2



### 4.2 Nested environment variables

With `env_nested_delimiter="__"`, a variable such as:

```
APP_DATABASE__POOL_SIZE=24
```

can populate `database.pool_size`.

The same nested model could instead be supplied as JSON:

```
APP_DATABASE='{"host":"db.internal","pool_size":10}'
```

Both representations can contribute to the same object. Within the environment source, a more specific nested variable takes precedence over a corresponding property in top-level JSON.

`env_nested_max_split` matters when using a single underscore as the delimiter. Without a limit, an identifier such as `API_KEY` might be interpreted as two nesting levels instead of one field name. The maximum-split setting prevents this ambiguity when the configuration structure has a known depth.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 4.3 Complex value decoding

Environment variables are strings, so complex values need a representation.

By default, pydantic-settings treats complex types—such as lists, sets, dictionaries, and nested models—as JSON-encoded values. For example:

```
APP_ALLOWED_PORTS='[8080,8081,9090]'
```

A comma-separated string such as `8080,8081,9090` is not interchangeable with JSON for `list[int]`. Default parsing can raise `SettingsError` before Pydantic field validation begins.

Three mechanisms allow this behavior to be controlled:

- `NoDecode`: an `Annotated` metadata marker that disables the source's automatic JSON decoding for a field.
- `enable_decoding=False`: a model-level option disabling automatic complex-value JSON decoding.
- `ForceDecode`: a field-level marker restoring JSON decoding even when it has been disabled globally.

These compose with Pydantic's `BeforeValidator` or `field_validator(mode="before")`, allowing input conventions such as CSV, semicolon-separated identifiers, custom date formats, or domain-specific mini-languages to be converted before type validation.

```
from typing import Annotated, Anyfrom pydantic import BeforeValidatorfrom pydantic_settings import NoDecodedef split_csv(value: Any) -> Any:    return value.split(",") if isinstance(value, str) else valueCsvNames = Annotated[list[str], NoDecode, BeforeValidator(split_csv)]
```

For more complex parsing, a subclass of `EnvSettingsSource` can override `prepare_field_value()`. This centralizes source-specific conversion rather than scattering parsing logic across individual configuration fields.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 4.4 Empty, null, and enum values

Several independent behaviors need to be distinguished:

`env_ignore_empty=True` treats an empty environment value as absent, allowing a lower-priority value or default to apply. Without it, an empty string is processed as a supplied value, which may be valid for a string but invalid for another type.

`env_parse_none_str` defines a textual sentinel that represents Python `None`. This is different from an absent variable and may interact with nullable types and defaults.

`env_parse_enums=True` supports interpreting enumeration member names where the normal string-to-enum conversion would otherwise expect a different representation.

A useful general distinction is that missing, explicitly empty, explicitly null, and invalid are separate input states. Treating them as interchangeable can change configuration semantics.

### 4.5 Unknown environment variables and validation coverage

One easily overlooked limitation is that `extra="forbid"` does not reject arbitrary unknown process environment variables. Unrecognized environment names are filtered before the model is validated.

For instance, `APP_PRT` may be ignored even though the intended field is `port`, allowing a default to remain in effect silently.

Once a variable matches a known nested field prefix, however, an unknown key inside that nested model can trigger `extra_forbidden` if the nested model forbids extra fields.

This is an important distinction between model validation and environment namespace auditing. The library does not treat the entire process environment as a closed configuration schema.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Sources: [Environment names and aliases](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#environment-variable-names), [value parsing and nesting](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#parsing-environment-variable-values), [JSON-decoding controls](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#disabling-json-parsing).

## 5. Dotenv and structured configuration files

### 5.1 Dotenv files

Dotenv support is integrated through `python-dotenv` and accepts paths configured on the model or supplied at construction time.

```
model_config = SettingsConfigDict(    env_file=(".env", ".env.production"),    env_file_encoding="utf-8",    env_file_depth=2,)
```

The most consequential behaviors are:

- Multiple dotenv files are read in the supplied order, with later files overriding earlier files.
- Process environment values have greater priority than dotenv values under the default source ordering.
- `_env_file="other.env"` overrides the configured dotenv files for that construction.
- `_env_file=None` explicitly disables dotenv loading for that construction.
- The new `env_file_depth` option searches parent directories for relative paths when the file is absent in the current directory. The default depth is zero.
- Named pipes/FIFOs are supported as dotenv inputs, enabling integration with providers that expose credentials through a stream rather than a conventional persisted file.

Dotenv input differs from process-environment input in a consequential way: unknown dotenv keys are included in model input and can be rejected by the default `extra="forbid"`.

`dotenv_filtering="match_prefix"` limits inputs to matching prefixes, while `"only_existing"` limits them to recognized fields. Alternatively, `extra="ignore"` permits unrecognized values.

Merely setting `env_prefix` does not automatically filter all other keys in a shared dotenv file.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs

+1



### 5.2 JSON, YAML, TOML, and `pyproject.toml`

Pydantic-settings supplies structured-file source implementations:

| Source class                        | Data format and distinctive controls                                    |
| ----------------------------------- | ----------------------------------------------------------------------- |
| `JsonConfigSettingsSource`          | JSON with `json_file`, `json_file_encoding`                             |
| `YamlConfigSettingsSource`          | YAML with `yaml_file`, `yaml_file_encoding`, optional section selection |
| `TomlConfigSettingsSource`          | TOML with `toml_file`, `toml_table_header`                              |
| `PyprojectTomlConfigSettingsSource` | Project TOML configuration, table selection and upward file discovery   |

These formats are available as native source classes, but are not automatically included in the default settings-source sequence. Configuring `json_file`, `yaml_file`, or `toml_file` without registering the corresponding source is insufficient.

An illustrative explicit registration:

```
from pydantic_settings import (    BaseSettings,    PydanticBaseSettingsSource,    TomlConfigSettingsSource,    SettingsConfigDict,)class Settings(BaseSettings):    model_config = SettingsConfigDict(toml_file="settings.toml")    endpoint: str    retries: int = 3    @classmethod    def settings_customise_sources(        cls,        settings_cls: type[BaseSettings],        init_settings: PydanticBaseSettingsSource,        env_settings: PydanticBaseSettingsSource,        dotenv_settings: PydanticBaseSettingsSource,        file_secret_settings: PydanticBaseSettingsSource,    ) -> tuple[PydanticBaseSettingsSource, ...]:        return (            init_settings,            env_settings,            TomlConfigSettingsSource(settings_cls),            dotenv_settings,            file_secret_settings,        )
```

This gives the TOML file lower precedence than constructor arguments and process environment variables, but higher precedence than dotenv and secrets files. That is an explicit choice, not a universal recommended order.

### 5.3 A critical merging distinction

Structured-file sources can accept more than one file, but multiple files within one source are shallow-merged by default.

Consider:

```
# defaults.toml
[database]
host = "db.internal"
port = 5432
```

```
# overrides.toml
[database]
port = 6432
```

Without a deep merge, the second file's `database` table replaces the first table rather than automatically preserving `host`.

The structured-file source constructors support `deep_merge=True` to change this behavior. It is a constructor option on the relevant source, not a `SettingsConfigDict` option.

This must not be confused with deep merging between distinct settings sources, which is part of the overall settings-resolution process.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 5.4 Project metadata and packaged configuration

`PyprojectTomlConfigSettingsSource` reads configuration from `pyproject.toml`, conventionally under `[tool.pydantic-settings]`. Its depth-based discovery is useful where configuration belongs to a Python project rather than an arbitrary working directory.

Structured-file sources also support file-like package resources through Python's `importlib.resources` `Traversable` abstraction. This permits resources bundled inside distributions, including zipped packages, to be consumed without assuming a normal filesystem path.

Other distinctions include selecting nested YAML sections, selecting TOML table paths, and the explicit UTF-8 default for JSON and YAML decoding introduced in 2.16.0.

These facilities let a typed settings schema act as the common validation boundary for packaged defaults, project metadata, local configuration, and operational overrides. They do not imply that arbitrary nested merging, file watching, or distributed synchronization happens automatically.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs

+1



Sources: [Dotenv configuration](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#dotenv-env-support), [other settings sources](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#other-settings-source), [versioned 2.16.0 source documentation](https://github.com/pydantic/pydantic-settings/blob/v2.16.0/docs/index.md?utm_source=chatgpt.com).

## 6. Filesystem secrets and nested secret trees

### 6.1 Basic secret files

`SecretsSettingsSource` supports the convention where each file's name identifies a setting and its contents supply the value.

For example, a file `/run/secrets/database_password` can supply a field named `database_password` when:

```
model_config = SettingsConfigDict(secrets_dir="/run/secrets")
```

This maps naturally to Docker Secrets, Kubernetes-mounted secrets, and other mechanisms that provision credentials as files.

The source also accepts multiple directories. Later directories override earlier ones when names collide, allowing a default secret directory and a more specific override directory to coexist.

Under the default source order, process environment variables and dotenv files have higher priority than filesystem secrets. Thus, placing a value in a secret mount does not automatically guarantee it is the value ultimately selected.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 6.2 `NestedSecretsSettingsSource`

The default `SecretsSettingsSource` has an important limitation: it is designed around top-level fields, not recursively structured secret fields.

`NestedSecretsSettingsSource` is an explicit alternative that understands nested settings structures. It can map either flat, delimiter-separated file names or actual nested directories to nested Pydantic models.

For example, it can interpret a layout resembling:

```
/run/secrets/
├── database/
│   ├── user
│   └── password
└── service/
    └── api_key
```

To use it, replace the default filesystem secret source in `settings_customise_sources()`:

```
from pydantic_settings import NestedSecretsSettingsSource@classmethoddef settings_customise_sources(    cls, settings_cls, init_settings, env_settings,    dotenv_settings, file_secret_settings,):    return (        init_settings,        env_settings,        dotenv_settings,        NestedSecretsSettingsSource(file_secret_settings),    )
```

The relevant controls are:

| Configuration                | Function                                                |
| ---------------------------- | ------------------------------------------------------- |
| `secrets_nested_subdir=True` | Interpret actual subdirectories as nesting              |
| `secrets_nested_delimiter`   | Use a separate delimiter for flattened secret names     |
| `secrets_prefix`             | Configure a secrets-specific name prefix                |
| `secrets_case_sensitive`     | Configure secret-name matching independently            |
| `secrets_dir_missing`        | Choose `ok`, `warn`, or `error` for missing directories |
| `secrets_dir_max_size`       | Limit total directory size processed by the source      |
| `secrets_dir`                | Support one or more secret directories                  |

The size limit defaults to 16 MiB per secrets directory. This is a security and resource-management provision: the nested source loads potential secret values during initialization rather than reading only one requested file at a time.

The advanced `secrets_*` options have no effect with the default flat source; using them without installing `NestedSecretsSettingsSource` produces a warning. This is a significant availability distinction.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs

+2



### 6.3 Security properties and limits

Secret-file support changes where values come from, not their cryptographic properties.

The source does not encrypt file contents. Actual security depends on mount permissions, operating-system access controls, secret provisioning, and how values are subsequently handled.

`SecretStr` can reduce accidental exposure through a model's ordinary representation, but values can still be retrieved explicitly, serialized in ways that reveal them, or leaked through debugging.

The nested secrets implementation also has a version-sensitive security history: a symlink path-escape vulnerability was fixed in 2.14.2. The targeted 2.16.0 release includes that fix. Security-sensitive deployments should distinguish current behavior from older releases.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



Sources: [Filesystem secrets](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#secrets), [nested secrets and configuration](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#nested-secrets).

## 7. Cloud secrets and parameter-store integrations

Pydantic-settings provides first-party source adapters for several cloud secret-management services.

These are optional integrations, not services implemented by Pydantic itself. They rely on the respective cloud SDKs, credentials, permissions, and network availability, and they must be added explicitly to the source sequence.

| Provider                            | Source class                        | Important behavior                                                     |
| ----------------------------------- | ----------------------------------- | ---------------------------------------------------------------------- |
| AWS Secrets Manager                 | `AWSSecretsManagerSettingsSource`   | Reads a specified secret; maps keys to fields and nested models        |
| AWS Systems Manager Parameter Store | `AWSSystemsManagerSettingsSource`   | Recursively reads parameters under an SSM path; introduced in 2.16.0   |
| Azure Key Vault                     | `AzureKeyVaultSettingsSource`       | Resolves Key Vault names with alias and naming-conversion options      |
| Google Cloud Secret Manager         | `GoogleSecretManagerSettingsSource` | Reads GCP secrets, supports nested naming and explicit secret versions |

### 7.1 AWS Secrets Manager

`AWSSecretsManagerSettingsSource(settings_cls, secret_id)` integrates an AWS Secrets Manager secret into the settings pipeline.

It can resolve nested fields when secret keys use `--` separators. For example, a secret key named `database--password` can correspond to a nested database password field.

The documented adapter does not support array reconstruction through numbered keys such as `items--0` and `items--1`. Its naming conventions and retrieval scope are consequently different from arbitrary Python or JSON structures.

It uses `boto3`, installed through the `aws-secrets-manager` optional extra.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 7.2 AWS Systems Manager Parameter Store

Version 2.16.0 introduces `AWSSystemsManagerSettingsSource`, which operates on an entire parameter namespace.

For an `ssm_path` such as `/prod/service`, a parameter named:

```
/prod/service/database/password
```

can populate `database.password`.

The source recursively calls AWS Systems Manager's `GetParametersByPath`, with decryption enabled for `SecureString` values.

This is materially different from the Secrets Manager adapter: it makes a hierarchical parameter collection into a settings source rather than reading fields from one named secret. Because it enumerates a path recursively, the size of that namespace, AWS API behavior, IAM permissions, and network latency affect construction cost.

The dedicated installation extra is `aws-systems-manager`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs

+1



### 7.3 Azure Key Vault

`AzureKeyVaultSettingsSource` accepts a vault URL and an Azure credential object, commonly supplied through `DefaultAzureCredential`.

It supports naming transformations that avoid defining individual aliases everywhere:

- `snake_case_conversion=True` maps supported forms such as `MySetting` or `my-setting` to `my_setting`.
- `dash_to_underscore=True` maps hyphens in secret names to underscores in Python fields.
- Nested naming uses `--`, including combinations with the dash-to-underscore mapping.

Indexed arrays are not supported through numbered secret names.

These conventions matter because Key Vault identifiers cannot always follow the same naming rules as Python attributes or process environment variables. The source adapter addresses that impedance mismatch without a separate bespoke translation layer.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 7.4 Google Cloud Secret Manager

`GoogleSecretManagerSettingsSource` has several useful advanced behaviors.

Project resolution is deferred and follows an ordered strategy: an explicit `project_id`, a field previously resolved by a higher-priority source (configurable with `project_id_field`), or the project identified through Google authentication defaults.

This is a particularly valuable interaction between capabilities. An ordinary environment or constructor source can select the cloud project, which a later cloud source uses to retrieve further settings.

The integration also supports nested fields using a compatible `env_nested_delimiter`. Its `SecretVersion` annotation enables a field to select a particular secret version rather than the default `latest`.

That distinction can be important for reproducibility or controlled credential rotation: selecting a specific version is different from always requesting the provider's current version.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs

+1



### 7.5 Cloud-source tradeoffs

Cloud source adapters replace substantial custom code for provider authentication, value retrieval, naming conversion, and model population. Nevertheless, they introduce operational consequences.

Source construction may perform network I/O. An instance created repeatedly can repeatedly retrieve remote values. This affects startup latency, provider request volume, and failure behavior. Native instance caching, discussed below, can reduce repeated acquisition, but it also means remote changes are not automatically visible in an already cached object.

They also do not unify all provider semantics: AWS Secrets Manager key structures, SSM paths, Azure names, and GCP versions have different capabilities and limitations. The common Pydantic model unifies validation and consumption, not the underlying services' APIs.

Sources: [AWS Secrets Manager](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#aws-secrets-manager), [AWS Systems Manager Parameter Store](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#aws-systems-manager-parameter-store), [Azure Key Vault](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#azure-key-vault), [Google Cloud Secret Manager](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#google-cloud-secret-manager).

## 8. Native command-line configuration and application interfaces

CLI functionality is one of the library's most substantial capabilities beyond conventional configuration loading.

Its architecture supports two related but distinct roles:

CLI as a configuration source: Arguments override configuration from environment variables and files.

Pydantic models as CLI definitions: The model's types, fields, descriptions, aliases, and nested structure define an executable CLI, including subcommands and help output.

### 8.1 `CliSettingsSource`

CLI parsing is enabled with `cli_parse_args=True`, or programmatically by passing a list or tuple of arguments through `_cli_parse_args`.

When enabled through the standard configuration, `CliSettingsSource` has the highest priority in the source chain.

It supports nested fields using dotted names:

```
myapp --database.host=db.internal --database.port=5432
```

It also supports multiple representations of collections and mappings. For example, a list can be supplied as JSON, repeated flags, or a comma-separated argument accepted by the CLI parser.

This is more than thin `argparse` integration: it lets a Pydantic schema drive type-aware argument processing while preserving access to other configuration sources.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 8.2 Positional arguments, subcommands, and variadic options

The central annotations and utilities are:

| API                         | Role                                                  |
| --------------------------- | ----------------------------------------------------- |
| `CliPositionalArg[T]`       | Declares positional CLI values                        |
| `CliSubCommand[T]`          | Declares a subcommand represented by a Pydantic model |
| `get_subcommand()`          | Retrieves the selected subcommand model               |
| `CliVariadicArg[T]`         | Accepts multiple values after one named option        |
| `CliUnknownArgs`            | Captures otherwise unrecognized CLI arguments         |
| `CliMutuallyExclusiveGroup` | Groups mutually exclusive options                     |

`CliSubCommand` supports one subparser group per model, and subcommand declarations must be required fields without defaults. Subcommand types can derive from `BaseModel` or use Pydantic dataclasses. Positional arguments and subcommands remain case-sensitive, even with broader case-insensitivity enabled elsewhere.

The new `CliVariadicArg` distinguishes a repeated option such as:

```
--files a --files b
```

from a variadic option:

```
--files a b
```

Its semantics are not identical to `argparse`'s `append`: repeating a variadic option replaces the earlier sequence. Its greedy argument consumption can also absorb what would otherwise be interpreted as a subcommand.

`CliMutuallyExclusiveGroup` avoids manually implementing mutual exclusion, but cannot contain nested models or be used inside a union.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs

+1



### 8.3 `CliApp` as an application runner

`CliApp.run()` can instantiate a model from CLI arguments and execute its `cli_cmd` method.

`CliApp.run_subcommand()` performs corresponding dispatch for selected subcommands. Both support asynchronous command methods.

An important distinction is that `CliApp` works with ordinary Pydantic `BaseModel` classes and Pydantic dataclasses in addition to `BaseSettings`. For these non-settings model types, it uses CLI-oriented defaults such as required-argument enforcement, kebab-case names, implicit Boolean flags, and reduced reliance on JSON input.

This creates an option to use Pydantic model definitions as the interface contract for both configuration values and command execution, without requiring a separate application CLI framework for basic-to-moderately-complex command structures.

For applications already built around an extensive CLI framework, however, adding a second parser layer may be less attractive than integration with the existing parser.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 8.4 CLI serialization

`CliApp.serialize()` converts a Pydantic model into a sequence of command-line arguments.

It supports configurable collection representations through `list_style` and `dict_style`, as well as positional-argument ordering. The 2.16.0 release specifically improves round-trip behavior for enums, tuples, dates, decimals, explicit `None` values, empty containers, and variadic arguments.

This has interesting implications beyond interactive terminals. A typed model can serve as the source of generated invocation arguments for subprocesses, batch systems, or reproducible command construction.

A limitation is that the serialized argument list may contain sensitive model values, so it should not automatically be treated as safe for logs, shell histories, or diagnostics.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs

+1



### 8.5 Help, naming, and parser integration

CLI configuration includes:

`cli_implicit_flags`, `CliImplicitFlag`, `CliExplicitFlag`, `CliDualFlag`, and `CliToggleFlag` for Boolean behavior; `cli_kebab_case` and `cli_shortcuts` for names; `cli_prefix` and `cli_flag_prefix_char` for namespaces; `cli_enforce_required` for strictness; `cli_avoid_json` for help and argument presentation; `cli_show_env_vars` for environment-name annotations; and `cli_exit_on_error` for exception-versus-exit behavior.

The default `cli_enforce_required=False` for settings models is deliberate: a required setting may be provided by the environment even if absent on the command line. This differs from a standalone CLI where an argument might truly be mandatory.

`CliUnknownArgs` and `cli_ignore_unknown_args` permit selective handling of unrecognized arguments, including workflows in which arguments are forwarded to another tool. Version 2.16.0 fixes several interactions with subcommands and case handling.

Finally, `CliSettingsSource` can attach to an existing `argparse` parser through `root_parser`, supports pre-parsed arguments, and exposes parser-method hooks for compatible external parsers. It therefore does not always require replacing a pre-existing command-line system.

Sources: [Full CLI reference](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#command-line-support), [creating CLI applications](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#creating-cli-applications), [integrating with existing parsers](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#integrating-with-existing-parsers).

## Version update: 2.16.1 released today

Correction to the opening version label: Further verification against PyPI and the newly published GitHub release confirms that pydantic-settings 2.16.1 is the current stable release as of October 20, 2026, not 2.16.0. It was published today. The capability overview above applies to the 2.16 series, including 2.16.1.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI

+1



Version 2.16.1 is a focused patch with two CLI regression fixes:

- Fixed-length positional tuples and `NamedTuple` values are correctly treated as fixed-arity arguments, instead of incorrectly using the new variadic behavior.
- Type aliases representing lists of dictionaries once again accept JSON-array CLI inputs without collapsing the list into one dictionary.

For these CLI use cases, 2.16.1 is materially preferable to 2.16.0.

Primary release references: [2.16.1 release notes](https://github.com/pydantic/pydantic-settings/releases/tag/v2.16.1?utm_source=chatgpt.com), [PyPI 2.16.1](https://pypi.org/project/pydantic-settings/2.16.1/?utm_source=chatgpt.com), [version-specific upstream documentation](https://github.com/pydantic/pydantic-settings/blob/v2.16.1/docs/index.md?utm_source=chatgpt.com).

## 9. Custom settings sources and extension architecture

The extensibility of pydantic-settings is arguably its most architecturally significant feature.

The built-in source implementations are instances of the same abstraction used to integrate arbitrary configuration systems. A custom source can therefore participate in normal priority resolution and Pydantic validation without reproducing the full settings framework.

### 9.1 Source abstractions

The core extension type is `PydanticBaseSettingsSource`.

Two broad implementation strategies are available:

Field-oriented adapters implement methods such as `get_field_value()` and `prepare_field_value()`. These suit sources whose representations require per-field name lookup, conversion, or decoding. `EnvSettingsSource` provides useful inherited behavior when the provider's values resemble environment variables.

Whole-mapping adapters implement `__call__()` to return a dictionary of settings contributions. These suit providers that already expose structured configuration documents or mappings.

In both cases, the object becomes a participant in `settings_customise_sources()`. Values are subsequently merged with the other sources and validated against the model.

This makes custom support possible for configuration databases, remote HTTP configuration endpoints, encrypted-file readers, service-discovery providers, in-memory configuration registries, or generated configuration derived from another system. These are integration possibilities through the extension API, not claims that every provider has a bundled adapter.

### 9.2 Accessing earlier source results

Custom sources can access two particularly useful properties:

| Property                | Meaning                                                                        |
| ----------------------- | ------------------------------------------------------------------------------ |
| `current_state`         | The aggregate values resolved from higher-priority sources processed so far    |
| `settings_sources_data` | The individual results of previously processed sources, indexed by source name |

This enables dependent configuration resolution.

For example, a source ordering can allow an environment variable to determine a cloud project, a tenant, or a configuration namespace. A later source can inspect that previously resolved value and retrieve additional configuration from the corresponding provider.

A simplified conceptual source:

```
from typing import Anyfrom pydantic.fields import FieldInfofrom pydantic_settings import PydanticBaseSettingsSourceclass ProviderSource(PydanticBaseSettingsSource):    def get_field_value(        self, field: FieldInfo, field_name: str    ) -> tuple[Any, str, bool]:        raise NotImplementedError    def __call__(self) -> dict[str, Any]:        namespace = self.current_state.get("config_namespace")        return read_provider_config(namespace)  # Application-provided adapter
```

This is an illustrative extension sketch, not a complete runnable provider implementation.

The pattern is useful because the selection of a configuration source can itself be configuration-driven, without constructing a separate preliminary parser and manually reimplementing source precedence.

There are important boundaries:

- `current_state` contains resolved source inputs, not necessarily fully validated settings values.
- The custom source still owns provider-specific authentication, request behavior, error translation, and potentially decoding.
- A dependent source must appear after the source supplying the values it needs.
- Relying on a particular representation or naming convention in source-state dictionaries creates coupling that should be treated explicitly.

The existing Google Cloud source's ability to derive `project_id` from prior settings illustrates the same architectural mechanism in a first-party integration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs

+1



### 9.3 Interaction with Pydantic's validator system

A valuable separation of responsibilities is possible:

- A source adapter understands the provider's external representation.
- A field validator understands how to normalize a particular input into a domain value.
- A model validator enforces relationships between configuration fields.
- The source pipeline decides precedence.

This avoids putting provider-specific acquisition logic inside validators or duplicating application invariants across different parsers.

The distinction also makes the system more testable. Source adapters can be exercised against controlled provider data, while ordinary Pydantic models can validate constructed inputs independently of environment acquisition.

Source: [Adding custom sources and accessing prior results](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#adding-sources).

## 10. Settings lifecycle, caching, reloads, and performance

### 10.1 Configuration objects are snapshots

Creating a new settings instance normally rereads its configured sources and validates the resulting data.

An existing settings object does not automatically update when an environment variable changes, a file is replaced, or a remote secret is rotated.

This distinction is foundational: source availability does not imply live reconfiguration.

Consequently, an application must decide whether configuration should be loaded once at startup, reconstructed for individual operations, cached, or explicitly reloaded.

### 10.2 Native settings caching in 2.16+

Version 2.16 introduced:

```
Settings.settings_cached()Settings.settings_clear_cache()
```

`settings_cached()` supplies a process-local cached instance of a particular settings class. This removes the need for the common pattern of wrapping settings construction in an application-defined `functools.lru_cache`.

For example:

```
settings = Settings.settings_cached()# Reuses the existing cached instancesame_settings = Settings.settings_cached()# Constructs independently and rereads configured sourcesfresh_settings = Settings()# Invalidates the class's cached instanceSettings.settings_clear_cache()
```

The cache has important semantics:

- It is keyed by the specific settings class.
- Subclasses have distinct cached instances.
- Clearing the base class's entry does not clear cached subclasses.
- The cache is local to one process, not shared across workers.
- A cached instance is a shared Python object, so mutations can affect all consumers.
- A frozen Pydantic model does not deeply freeze nested mutable values.

The cache's benefit depends on the sources involved. Avoiding repeated environment parsing may be a small optimization; avoiding repeated filesystem access or cloud-secret retrieval can be much more consequential. No general throughput multiplier follows from the API alone.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 10.3 Reloading configuration

The documentation supports in-place reinitialization by calling an existing settings object's `__init__()` method. This rereads sources while retaining object identity.

However, in-place reinitialization has a concurrency hazard: another consumer can observe the object while its fields are being reconstructed.

For concurrent systems, constructing a complete replacement and then swapping the reference provides a cleaner consistency boundary. Readers see either the old validated configuration or the new validated configuration, rather than an object undergoing reinitialization.

Caching introduces a separate freshness issue: clearing a cache changes what subsequent `settings_cached()` calls return, but any code retaining the previously returned instance still holds that older object. Cache invalidation is not a broadcast update mechanism.

These are general lifecycle consequences of Python object identity and the documented caching contract.

### 10.4 Async application integration

Settings acquisition is synchronous, including disk-backed sources. Cloud SDK calls may additionally incur network latency.

The official documentation recommends moving potentially blocking construction into a worker thread when invoked from an asyncio event loop:

```
import asyncioasync def load_settings() -> Settings:    return await asyncio.to_thread(Settings)
```

This offloads construction; it does not make the underlying providers asynchronous. Native async CLI command execution, discussed earlier, should not be confused with asynchronous settings acquisition.

The library does not provide a general-purpose file watcher, change-notification subscription, or cross-process configuration-update protocol. Those remain distinct lifecycle responsibilities if an application requires them.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



Sources: [Caching settings](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#caching-settings), [in-place reloading](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#in-place-reloading), [async environments](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#async-environments).

## 11. Diagnostics, failure behavior, and operational correctness

### 11.1 Source-resolution diagnostics

Pydantic-settings has a built-in debugging mechanism that is especially useful when a value appears to have been ignored or unexpectedly overridden.

Setting:

```
PYDANTIC_SETTINGS_DEBUG=1
```

and enabling DEBUG-level logging for the `pydantic_settings` logger produces information about the contributions of individual settings sources, their precedence, and file discovery.

This can reveal:

- Which source provided a value.
- Which configured file could not be found.
- Whether an expected secret file was discovered.
- Whether source ordering explains an override.
- Whether a source contributed any values at all.

It is an important complement to Pydantic's normal validation errors, which explain why a resolved input is invalid but may not explain why that input was selected.

Security warning: Source-debug logging can expose unredacted secret values. It should be enabled only in trusted diagnostic contexts.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs



### 11.2 Distinguishing failure classes

The framework can surface different failures at different processing stages.

| Situation                                                           | Typical behavior                                                       |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| Required setting absent after all sources                           | Pydantic `ValidationError`                                             |
| Field type or constraint invalid                                    | Pydantic `ValidationError`                                             |
| Invalid JSON for a complex environment field                        | `SettingsError` during source processing                               |
| Unrecognized process environment name                               | Ignored before model validation                                        |
| Extra dotenv entry with default `extra="forbid"`                    | `ValidationError`                                                      |
| Missing ordinary secrets directory                                  | Warning; values remain absent                                          |
| Missing nested secrets directory with `secrets_dir_missing="error"` | `SettingsError`                                                        |
| CLI parsing error                                                   | CLI exit or `SettingsError`, depending on configuration                |
| Remote provider unavailable                                         | Provider/source error; not automatically converted into valid defaults |

These distinctions are relevant to diagnostics and failure handling. A missing field might indicate an absent secret, but it could also indicate an alias mismatch or an incorrectly configured prefix. A `ValidationError` alone does not establish which source was intended to provide the value.

An especially useful practice is to distinguish source-resolution failures from domain validation failures rather than catching both as an undifferentiated configuration exception.

### 11.3 Configuration transparency and provenance

The framework provides source-state access and diagnostic logging, but ordinary `BaseSettings` model attributes are not themselves a complete provenance record explaining every contributing source and override.

If a system needs a persistent per-field audit trail—for example, to explain which value was overridden by which source and when—the custom-source and diagnostic facilities are building blocks. A durable audit history is a separate capability.

Similarly, Pydantic can expose JSON Schema and structured validation errors, but generating a comprehensive operator-facing configuration contract, including all effective source names, precedence rules, and runtime values, may require additional presentation logic.

Sources: [Debugging settings sources](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#debugging-settings-sources), [Pydantic validation errors](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#overview).

## 12. Dependencies, compatibility, and recent evolution

### 12.1 Package and ecosystem boundaries

For the current 2.16.1 release, the principal compatibility characteristics are:

| Component                      | Status                                                   |
| ------------------------------ | -------------------------------------------------------- |
| Python                         | 3.11 or newer                                            |
| Pydantic                       | Pydantic 2.x; package declares a minimum of 2.7.0        |
| Settings implementation        | Separate `pydantic-settings` distribution                |
| Environment and dotenv parsing | Integrates `python-dotenv`                               |
| TOML                           | Standard-library `tomllib` for supported Python versions |
| YAML                           | Optional `yaml` extra, using PyYAML                      |
| AWS integrations               | Optional `boto3` dependency                              |
| Azure integration              | Optional Azure Identity and Key Vault SDK packages       |
| GCP integration                | Optional Google Cloud Secret Manager client              |
| License                        | MIT                                                      |

The published extras are `yaml`, `toml`, `aws-secrets-manager`, `aws-systems-manager`, `azure-key-vault`, and `gcp-secret-manager`. The `toml` extra remains for compatibility even though Python 3.11+'s standard-library TOML reader eliminates its historical dependency role.

The 2.16 release line also requires an updated `python-dotenv` dependency to include a security fix.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+2



One compatibility detail deserves emphasis: Pydantic and pydantic-settings are separate packages with independent releases. New Pydantic validation features or changes in Pydantic model behavior may affect settings integration even when the settings package itself has not changed.

### 12.2 Recent significant additions

| Release | Consequential capability or change                                                                                  |
| ------- | ------------------------------------------------------------------------------------------------------------------- |
| 2.12.0  | Nested filesystem secrets support                                                                                   |
| 2.13.0  | Optional deep merging within structured-file sources; richer YAML section paths                                     |
| 2.14.2  | Nested-secrets symlink path-escape security fix                                                                     |
| 2.15.0  | Case-sensitivity behavior extended to constructor and structured-file sources                                       |
| 2.16.0  | Native instance cache, SSM Parameter Store source, parent dotenv search, `CliVariadicArg`, Python 3.11+ requirement |
| 2.16.1  | Fixes CLI regressions involving fixed-arity positional tuples and list-of-dictionary type aliases                   |

This progression illustrates that pydantic-settings is no longer just the environment-variable capability that accompanied earlier versions of Pydantic. The source architecture, CLI facilities, remote secret adapters, and lifecycle controls have developed into significant independent capability areas.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

+2



## 13. Architectural implications and important distinctions

The most valuable architectural opportunities arise from combining the library's capabilities rather than considering each source adapter in isolation.

### 13.1 One typed schema across several configuration surfaces

A single Pydantic model can define values that arrive through configuration files, environment overrides, CLI arguments, and secret providers.

This can eliminate separate validation code for each input path and reduce disagreements about field names, accepted types, defaults, and invariants.

The important qualification is that different sources still have different parsing and naming semantics. JSON file values, environment strings, CLI arguments, and cloud secret names are not perfectly interchangeable. Their adapters normalize these inputs toward a common model, but source-specific distinctions remain.

### 13.2 Native configuration layering

Cross-source deep merging and customizable precedence can replace substantial hand-written configuration merge logic.

The main caveats are that source order establishes override authority, nested aliases affect which values can actually merge, and multi-file merging within a structured source is a separate behavior requiring explicit configuration.

The nested-model default partial-update option adds a further distinction between updating an existing default object and constructing a fresh nested object from supplied values and field defaults.

### 13.3 Shared configuration models for CLI and application execution

CLI generation from Pydantic models can reduce duplication between command-line argument declarations, configuration validation, and application data structures.

It can be especially expressive where an application has typed options, nested parameters, and moderately complex subcommands. Integration hooks make coexistence with an existing parser possible.

The native CLI system is nevertheless built around argparse-like abstractions. It should not be assumed to replace every capability offered by specialized terminal-interface frameworks, particularly where complex interactive behavior or custom command grammars are central.

### 13.4 Unified local and cloud secrets consumption

The secret sources allow ordinary typed application configuration to integrate directly with local mounted credentials and several cloud providers.

The benefit is avoiding provider-specific mapping and validation code. The cost is adding provider-specific authentication, network dependencies, and refresh policies to the configuration-loading lifecycle.

The presence of `settings_cached()` makes repeated loading cheaper but also turns freshness into an explicit architectural choice.

### 13.5 Better separation of acquisition and validation

The source API gives one place to implement external system integration, while Pydantic validators provide a different place to enforce configuration correctness.

That separation can produce smaller and more composable implementations than custom parsers that mix I/O, environment lookup, type conversion, validation, and precedence in the same code path.

The most important design choice is not necessarily which source provider to use, but whether the source pipeline can become the common boundary through which all configuration values pass.

## 14. Primary-source reference map

The references below are useful starting points for deeper investigation. They are direct URLs intended to remain accessible independently of this overview.

| Topic                               | Primary reference                                                                                                                                                                                                                                 |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Current release                     | [https://pypi.org/project/pydantic-settings/2.16.1/](https://pypi.org/project/pydantic-settings/2.16.1/?utm_source=chatgpt.com)                                                                                                                   |
| Current patch release notes         | [https://github.com/pydantic/pydantic-settings/releases/tag/v2.16.1](https://github.com/pydantic/pydantic-settings/releases/tag/v2.16.1?utm_source=chatgpt.com)                                                                                   |
| Major 2.16 feature release          | [https://github.com/pydantic/pydantic-settings/releases/tag/v2.16.0](https://github.com/pydantic/pydantic-settings/releases/tag/v2.16.0?utm_source=chatgpt.com)                                                                                   |
| Full settings concepts and examples | [https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com)                                                                         |
| API reference                       | [https://pydantic.dev/docs/validation/latest/api/pydantic_settings/](https://pydantic.dev/docs/validation/latest/api/pydantic_settings/?utm_source=chatgpt.com)                                                                                   |
| Settings-source customization       | [https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#customise-settings-sources](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#customise-settings-sources)                   |
| Environment parsing                 | [https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#parsing-environment-variable-values](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#parsing-environment-variable-values) |
| Full CLI system                     | [https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#command-line-support](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#command-line-support)                               |
| Filesystem and nested secrets       | [https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#nested-secrets](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#nested-secrets)                                           |
| Cloud secret adapters               | [https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#aws-secrets-manager](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#aws-secrets-manager)                                 |
| Cache and lifecycle                 | [https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#caching-settings](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#caching-settings)                                       |
| Tagged source and documentation     | [https://github.com/pydantic/pydantic-settings/tree/v2.16.1](https://github.com/pydantic/pydantic-settings/tree/v2.16.1?utm_source=chatgpt.com)                                                                                                   |
| Release history                     | [https://github.com/pydantic/pydantic-settings/releases](https://github.com/pydantic/pydantic-settings/releases?utm_source=chatgpt.com)                                                                                                           |

## Closing perspective

Pydantic-settings 2.16.1 is best understood as a composable, type-validated configuration resolution framework. Its core value extends well beyond loading environment variables.

The most consequential capabilities are its programmable settings-source pipeline, nested cross-source merging, advanced parsing controls, first-party structured-file and secrets adapters, integrated CLI modeling, custom source-state access, and native instance caching.

Together, those mechanisms can substantially reduce bespoke configuration infrastructure while keeping type validation, input normalization, and precedence centralized.

Its principal limits are equally important: external sources retain their individual naming and parsing semantics; configuration is not automatically live or distributed; source acquisition can be blocking; cache invalidation requires an explicit lifecycle policy; and security guarantees depend on the underlying secret providers and operational environment.

Those boundaries make it possible to use the library as a coherent configuration foundation without mistaking it for a general configuration-service or lifecycle-orchestration platform.

# pydantic-settings — Advanced Capabilities and Behavioral Semantics Addendum

Target version: 2.16.2\
Research date: November 1, 2026\
Python: 3.11+ | Pydantic: 2.x | License: MIT\
Companion document: pydantic-settings — Comprehensive Python Library Overview

## Scope and orientation

This addendum supplements the original library overview with advanced functionality, consequential execution semantics, provider-specific behaviors, and configuration edge cases that were omitted or insufficiently developed.

It is organized around the original document's capability families rather than repeating the underlying introduction, source catalog, or implementation examples.

The additions address several important distinctions:

- Configuration precedence determines effective values, but does not necessarily control whether a source executes.
- Partial updates to nested default models differ from ordinary deep merging across configuration sources.
- A settings schema can be reused with different acquisition policies through instance-specific constructor controls.
- Cloud-provider adapters expose more precise versioning, naming, authentication, and discovery behavior than a common settings interface might suggest.
- The CLI subsystem can act as a programmatic interface-definition and documentation facility, not merely a parser.
- Several source-specific behaviors affect correctness, portability, and diagnostics even when the same Pydantic model is used.

### Version status

Version 2.16.2, published October 28, 2026, supersedes the original guide's 2.16.1 target. PyPI identifies it as the latest stable release as of this research date. Its GitHub release entry does not provide a detailed functional changelog, so the additions below describe verified capabilities available in the 2.16 series rather than attributing undocumented functionality to the patch release.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pypi.org\&sz=32)

PyPI+1



Primary references:

- [https://pypi.org/project/pydantic-settings/2.16.2/](https://pypi.org/project/pydantic-settings/2.16.2/?utm_source=chatgpt.com)
- [https://github.com/pydantic/pydantic-settings/releases/tag/v2.16.2](https://github.com/pydantic/pydantic-settings/releases/tag/v2.16.2?utm_source=chatgpt.com)
- [https://github.com/pydantic/pydantic-settings/tree/v2.16.2](https://github.com/pydantic/pydantic-settings/tree/v2.16.2?utm_source=chatgpt.com)

## 1. Source execution semantics: precedence is not lazy resolution

Extends original §3 — Settings sources, precedence, and layered merging.

### 1.1 Every source in the configured pipeline participates in construction

The distinction between source priority and source execution is fundamental to the library's architecture.

Pydantic-settings evaluates the source sequence in order, collecting each source's contribution and combining the returned mappings through `deep_update`. A higher-priority source wins conflicts, including conflicts in nested structures, but the resolution engine does not implement a general short-circuit operation that skips lower-priority sources once a field has been populated.

The 2.16.2 implementation performs the following operations for each source:

1. Supply the source with the current accumulated state and previously collected source data.
2. Invoke the source through `source()`.
3. Record its returned mapping.
4. Merge that mapping into the accumulated state while preserving higher-priority values.

Validation occurs after source acquisition and merging. If a source raises an exception, construction can fail before a completed settings object exists.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com



This distinction is particularly consequential for sources that interact with databases, remote configuration services, cloud secret managers, or expensive local parsers.

For example, placing an AWS Secrets Manager source below `init_settings` allows explicit constructor values to override AWS-provided settings. It does not guarantee that AWS retrieval will be avoided when those values are present. Even a fully specified higher-priority configuration can be exposed to the lower-priority provider's latency or availability.

### 1.2 Source-state inspection enables conditional acquisition

The custom-source interface provides an opportunity to implement selective acquisition without reconstructing the entire settings-resolution framework.

A source can inspect:

- `current_state`: the accumulated values returned by previously processed, higher-priority sources.
- `settings_sources_data`: the individual mappings returned by those sources.

A custom source can use this information to determine which settings are still unresolved and restrict external queries accordingly.

This enables several distinct acquisition policies:

| Acquisition policy             | Mechanism                                               | Consequence                                             |
| ------------------------------ | ------------------------------------------------------- | ------------------------------------------------------- |
| Eager acquisition              | Read the provider on every construction                 | Simple, but incurs provider I/O regardless of overrides |
| Conditional acquisition        | Inspect `current_state` before requesting values        | Can avoid unnecessary remote access                     |
| Selective acquisition          | Request only fields absent from higher-priority sources | Can reduce payload size and provider operations         |
| Required-authority acquisition | Always consult the provider even when overrides exist   | Preserves mandatory provider checks, where needed       |

These are policies implementable through custom sources, not automatic modes of the settings engine.

An important qualification is that field presence is not equivalent to configuration completeness. If a higher-priority source supplies only `database.host`, a lower-priority source may still need to supply `database.port` or other members of the same nested model.

A conditional provider therefore needs to distinguish complete, partially populated, and missing configuration structures. Simply checking whether the top-level `database` key exists may incorrectly suppress required lower-priority values.

The library's source-state dictionaries are also not necessarily validated configuration objects. They contain acquired and partially normalized inputs, potentially with aliases and source-specific representations. Decisions based on them should not assume that downstream Pydantic validation has succeeded.

### 1.3 Operational and architectural implications

This separation creates three independently controllable concerns:

Override authority: Which provider's values take precedence?

Acquisition necessity: Which providers must actually be consulted?

Validation authority: Which invariants must the completed configuration satisfy?

The standard source pipeline directly addresses the first and third concerns. The second can be customized through source implementations, conditional retrieval, or configuration lifecycle management.

This can eliminate bespoke top-level configuration composition while retaining fine-grained control over costly providers. It also explains why configuration caching can have disproportionate benefits when remote sources are enabled: caching avoids constructing and evaluating the source pipeline again, rather than merely avoiding repeated Pydantic validation.

Primary source — tagged settings construction implementation:

[https://github.com/pydantic/pydantic-settings/blob/v2.16.2/pydantic_settings/main.py](https://github.com/pydantic/pydantic-settings/blob/v2.16.2/pydantic_settings/main.py?utm_source=chatgpt.com)

Relevant official documentation:

[https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#accessing-the-result-of-previous-sources](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#accessing-the-result-of-previous-sources)

## 2. Nested model defaults and partial-update semantics

Extends original §2.2, §3.2, and §13.2.

### 2.1 `nested_model_default_partial_update` controls an independent merge boundary

The configuration option `nested_model_default_partial_update` determines how externally supplied nested values interact with a populated default model instance.

It defaults to `False`.

When disabled, a partial external update can cause the nested model to be reconstructed using its declared field defaults rather than retaining every value from the preconfigured default object.

When enabled, the source pipeline can incorporate values from the default model instance into the nested input, preserving unspecified defaults while applying the external overrides.

Consider:

```
from pydantic import BaseModelfrom pydantic_settings import BaseSettings, SettingsConfigDictclass ConnectionConfig(BaseModel):    pool_size: int = 10    enabled: bool = Falseclass Settings(BaseSettings):    model_config = SettingsConfigDict(        env_nested_delimiter="__",        nested_model_default_partial_update=True,    )    connection: ConnectionConfig = ConnectionConfig(pool_size=40)
```

With `CONNECTION__ENABLED=true`, the resulting configuration retains `pool_size=40` and sets `enabled=True`.

Changing `nested_model_default_partial_update` to `False` results in `pool_size=10`, because the externally supplied partial data leads to construction using `ConnectionConfig`'s ordinary field default.

| Behavior                                                         | Partial update disabled | Partial update enabled            |
| ---------------------------------------------------------------- | ----------------------- | --------------------------------- |
| Preserve unspecified values from populated nested default        | No                      | Yes                               |
| Apply supplied nested overrides                                  | Yes                     | Yes                               |
| Use nested model's own field defaults for unspecified properties | Yes                     | Only where not otherwise supplied |
| Default setting                                                  | Yes                     | No                                |

This is distinct from deep merging between independent sources. Source merging operates on mappings contributed by the configured sources; nested-default partial updates determine how an already populated default model contributes to those mappings.

Enabling partial updates should not be interpreted as a guarantee that the original default object's Python identity is preserved or that the object is mutated in place. The relevant contract concerns resulting configuration values.

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

### 2.2 Interaction with discriminated unions

For nested fields typed as discriminated unions, indiscriminately merging the default model's fields into a supplied value can produce invalid combinations.

Suppose a configuration field accepts two model variants, distinguished by a `kind` discriminator. Its default is an instance of one variant, while an external source selects the other.

The intended behavior is:

- If the supplied configuration selects the same union member as the default, partial updates can retain compatible default values.
- If the supplied configuration selects a different member, values specific to the original default member must not be carried into the newly selected variant.

Pydantic-settings fixed regressions affecting this interaction in the 2.15 and 2.16 release lines. The 2.16.0 release specifically restored partial-update behavior for discriminated-union defaults when the incoming configuration does not select a different union member.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



This distinction enables heterogeneous configuration models to share a common typed interface while preserving variant-specific defaults. It avoids requiring separate manual merging logic for each supported variant, provided the discriminators and model defaults are defined consistently.

Primary references:

[https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#nested-model-default-partial-updates](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#nested-model-default-partial-updates)

[https://github.com/pydantic/pydantic-settings/releases/tag/v2.16.0](https://github.com/pydantic/pydantic-settings/releases/tag/v2.16.0?utm_source=chatgpt.com)

## 3. Per-instance configuration and dynamic acquisition policies

Extends original §2, §3, and §9.

### 3.1 Constructor-level overrides

`BaseSettings` exposes numerous underscore-prefixed constructor parameters that override the corresponding model-level acquisition options for an individual settings instance.

This allows the same schema to be constructed against different configuration namespaces or source environments without defining a different settings class for each context.

For example:

```
from pydantic_settings import BaseSettings, SettingsConfigDictclass Settings(BaseSettings):    model_config = SettingsConfigDict(        env_prefix="APP_",        env_file=".env",    )    host: str = "localhost"    port: int = 8000development = Settings(    _env_prefix="DEV_",    _env_file=".env.development",)production = Settings(    _env_prefix="PROD_",    _env_file=None,)
```

The two instances have identical field schemas and validation rules but different environment-variable namespaces and dotenv policies.

In the production construction, `_env_file=None` disables the configured dotenv source input. It does not disable process environment variables.

### 3.2 Available instance-specific controls

The constructor provides controls spanning several capability families.

| Configuration dimension | Instance parameters                                                                                   |
| ----------------------- | ----------------------------------------------------------------------------------------------------- |
| Name resolution         | `_case_sensitive`, `_env_prefix`, `_env_prefix_target`                                                |
| Nested resolution       | `_env_nested_delimiter`, `_env_nested_max_split`                                                      |
| Value handling          | `_env_ignore_empty`, `_env_parse_none_str`, `_env_parse_enums`                                        |
| Default-model updates   | `_nested_model_default_partial_update`                                                                |
| Dotenv loading          | `_env_file`, `_env_file_encoding`, `_env_file_depth`                                                  |
| Filesystem secrets      | `_secrets_dir`                                                                                        |
| CLI acquisition         | `_cli_parse_args`, `_cli_settings_source`, `_cli_prog_name`                                           |
| CLI parsing policy      | `_cli_implicit_flags`, `_cli_enforce_required`, `_cli_exit_on_error`, `_cli_ignore_unknown_args`      |
| CLI presentation        | `_cli_kebab_case`, `_cli_shortcuts`, `_cli_show_env_vars`, `_cli_hide_none_type`, and related options |

Most optional overrides use `None` to indicate that the class's `model_config` value should be retained.

`_env_file` is a significant exception: its default is a dedicated sentinel, so an explicitly supplied `None` can mean disable dotenv loading rather than use the class default.

Other important distinctions include the ability to pass an explicit list of CLI arguments through `_cli_parse_args` and to supply a custom `CliSettingsSource` through `_cli_settings_source`. These allow application code to select an invocation context without depending on the ambient process argument vector.

Not every `SettingsConfigDict` key has a matching public constructor override. In particular, structured-file source paths such as `toml_file` and `yaml_file` are normally controlled through model configuration or explicitly constructed sources.

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com

### 3.3 Class-definition configuration and inheritance

The settings-specific configuration keys are also registered with Pydantic's model configuration system, allowing declaration through class-definition keywords:

```
class ServiceSettings(    BaseSettings,    env_prefix="SERVICE_",    case_sensitive=True,):    endpoint: str
```

This is an alternative to defining those settings through `SettingsConfigDict`.

The mechanisms operate at different levels:

Class configuration establishes defaults for every instance of the settings type, subject to normal configuration inheritance.

Constructor overrides adjust supported source behavior for one construction.

Custom source objects can change the provider implementation itself, including capabilities not exposed through ordinary constructor options.

These provide three levels of configurability without requiring separate schema-validation implementations.

### 3.4 Interaction with native caching

The per-instance controls also clarify an important limitation of the native cache.

`Settings.settings_cached()` caches the default construction of a settings class. Its cache identity is associated with the class, not an arbitrary tuple of constructor overrides.

Consequently, a collection of instances created with different `_env_prefix` or `_env_file` arguments does not automatically produce independently cached variants through `settings_cached()`.

Separate subclasses, ordinary independently constructed instances, or an application-controlled parameterized cache can express those distinctions when required.

The first-party cache is deliberately a class-scoped cached default instance rather than a general parameterized configuration registry.

Primary references:

[https://pydantic.dev/docs/validation/latest/api/pydantic_settings/](https://pydantic.dev/docs/validation/latest/api/pydantic_settings/?utm_source=chatgpt.com)

[https://github.com/pydantic/pydantic-settings/blob/v2.16.2/pydantic_settings/main.py](https://github.com/pydantic/pydantic-settings/blob/v2.16.2/pydantic_settings/main.py?utm_source=chatgpt.com)

## 4. Cloud-source versioning, provider configuration, and lookup semantics

Extends original §7 — Cloud secrets and parameter-store integrations.

### 4.1 AWS Secrets Manager: selecting immutable secret versions

`AWSSecretsManagerSettingsSource` supports an optional `version_id` constructor parameter.

This is different from selecting the default currently active secret version.

A conceptual source construction is:

```
aws_source = AWSSecretsManagerSettingsSource(    settings_cls,    secret_id="production/service/config",    region_name="us-east-1",    version_id="specific-aws-secret-version-id",)
```

The source passes `version_id` to AWS Secrets Manager as the `VersionId` argument of `GetSecretValue`.

This supports a more precise relationship between an application configuration and the secret version from which it was constructed.

The distinction is useful for configuration reproducibility, controlled credential transitions, diagnostic reconstruction, and deployment systems that coordinate the activation of particular secret versions.

The source selects a version of the entire AWS Secrets Manager secret, not independent versions of different fields within that secret. The native constructor exposes `version_id`, rather than a general collection of per-field version selectors.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 4.2 Provider-client routing and payload assumptions

The AWS Secrets Manager constructor additionally accepts `region_name` and `endpoint_url`.

The Systems Manager Parameter Store source exposes the same routing controls.

`region_name` specifies the AWS client region, while `endpoint_url` can direct the underlying boto3 client to a particular service endpoint. This creates options for regional isolation, private endpoint configurations, and compatible local testing services without replacing the settings-source abstraction.

The AWS Secrets Manager adapter expects a `SecretString` that can be decoded as JSON containing configuration entries. Its implementation reads:

```
json.loads(response["SecretString"])
```

It should therefore not be treated as a general adapter for arbitrary binary Secrets Manager payloads or every supported AWS secret representation.

The Systems Manager adapter, in contrast, performs recursive parameter enumeration using `GetParametersByPath`, including decryption for encrypted parameters. Its `ssm_path` must start with `/`; an invalid relative path raises `SettingsError` during source initialization.

Both AWS sources expose controls for case sensitivity, prefixes, nested naming, null-string parsing, and enum parsing. These are provider-source constructor options, not evidence that AWS itself implements the corresponding Python configuration semantics.

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

Primary source:

[https://github.com/pydantic/pydantic-settings/blob/main/pydantic_settings/sources/providers/aws.py](https://github.com/pydantic/pydantic-settings/blob/main/pydantic_settings/sources/providers/aws.py?utm_source=chatgpt.com)

### 4.3 Google Cloud: project selection depends on resolved source keys

`GoogleSecretManagerSettingsSource` supports dynamically selecting its GCP project from a previously evaluated source.

The documented resolution order is:

1. An explicitly supplied `project_id`.
2. A value found in the accumulated higher-priority source state under `project_id_field`.
3. The project returned by Google Application Default Credentials.

The important additional distinction concerns aliases.

If the model declares:

```
gcp_project: str = Field(alias="GCP_PROJECT")
```

the preceding environment source may contribute the value under `GCP_PROJECT`, rather than under the Python field name `gcp_project`.

Accordingly:

```
GoogleSecretManagerSettingsSource(    settings_cls,    project_id_field="GCP_PROJECT",)
```

uses the expected source-state key.

A `project_id_field` value referring to the wrong representation may fail to locate the previously acquired project identifier and cause the source to fall back to another project-selection mechanism.

This illustrates a general constraint of dependent configuration acquisition: earlier source values can drive later source behavior, but source-state keys are not necessarily normalized to Python attribute names.

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

### 4.4 Google Cloud: field-level version selection and alias collisions

Google Cloud Secret Manager provides more granular secret-version selection through the `SecretVersion` annotation.

A settings model can declare separate fields corresponding to different versions of the same underlying secret.

For example, the following is a schema illustration; a GCP source must still be registered separately:

```
from typing import Annotatedfrom pydantic import Fieldfrom pydantic_settings import BaseSettings, SettingsConfigDictfrom pydantic_settings.sources.types import SecretVersionclass Settings(BaseSettings):    model_config = SettingsConfigDict(populate_by_name=True)    current_token: str = Field(alias="service-token")    pinned_token: Annotated[        str,        SecretVersion("7"),    ] = Field(alias="service-token")
```

`current_token` uses the provider's default `latest` selection, while `pinned_token` requests version `7`.

When two settings fields reference the same secret name through their aliases but select different versions, the official documentation requires `populate_by_name=True` or `validate_by_name=True`.

This allows the individual Python fields to remain distinguishable after source acquisition instead of collapsing into one alias-keyed input.

An explicit version that cannot be retrieved is not silently replaced with `latest` by the version-specific lookup path. The source treats that requested value as unavailable, which can lead to fallback through other settings sources or a validation failure depending on the final configuration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs+1



### 4.5 Google Cloud: case sensitivity changes discovery and permissions

The GCP source treats secret names as case-sensitive by default, independently of the ordinary environment source's default case-insensitivity.

When `case_sensitive=True`, the implementation can directly address individual secret names without enumerating the project's secret collection.

This avoids the `list_secrets` operation and can reduce the required IAM permissions to those necessary for accessing the referenced secrets.

When `case_sensitive=False`, the source performs name discovery so that it can map differently capitalized field names to available secrets.

This creates several additional behaviors:

- Exact secret-name matches take precedence over case-insensitive alternatives.
- Names that normalize to the same lowercase representation can collide.
- The implementation warns about ambiguous normalized names and uses deterministic selection when several candidates remain.
- Case-insensitive discovery can require permissions for listing secrets, beyond permissions to access particular known secret versions.

These differences make case sensitivity a provider-access and configuration-determinism decision, not merely a naming preference.

The source also accepts an explicitly constructed `secret_client`, enabling a caller-supplied Google Secret Manager client rather than requiring the adapter to construct one through default authentication.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs+2



### 4.6 Failure semantics are not uniform across cloud providers

The shared settings-source interface does not imply identical behavior when providers report missing credentials, missing values, unavailable secrets, or permission failures.

For example, the GCP source implementation has lookup paths that catch provider-access exceptions and return `None`, effectively treating some retrieval failures as unavailable values.

This differs from an adapter that propagates a provider exception immediately.

Depending on field requirements and lower-priority contributions, a missing value can therefore result in successful fallback, a validation error, or a provider-specific exception.

The distinction is significant for systems requiring authoritative secrets. Successful model construction alone does not prove that every configured cloud source was successfully consulted.

The provider's access and failure semantics should be considered separately from Pydantic's final type-validation semantics.

Primary references:

[https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#google-cloud-secret-manager](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#google-cloud-secret-manager)

[https://github.com/pydantic/pydantic-settings/blob/main/pydantic_settings/sources/providers/gcp.py](https://github.com/pydantic/pydantic-settings/blob/main/pydantic_settings/sources/providers/gcp.py?utm_source=chatgpt.com)

## 5. CLI introspection, interface composition, and advanced command semantics

Extends original §8 — Native command-line configuration and application interfaces.

### 5.1 Programmatic CLI help generation

Beyond accepting command-line input and serializing model instances, `CliApp` exposes two complementary interfaces:

`CliApp.format_help()` returns the formatted help text as a string.

`CliApp.print_help()` writes the help text to an output stream.

Both accept a model class or an appropriate model instance, allowing help for an interface to be generated without running the application's command method.

For example:

```
from pydantic import Fieldfrom pydantic_settings import BaseSettings, CliApp, SettingsConfigDictclass Settings(BaseSettings):    model_config = SettingsConfigDict(        env_prefix="APP_",        cli_show_env_vars=True,        cli_prog_name="service",    )    host: str = Field(        default="localhost",        description="Service host",    )help_text = CliApp.format_help(Settings, strip_ansi_color=True)
```

The API also accepts an explicitly configured `CliSettingsSource`, making it possible to format help through a customized parser configuration.

`print_help()` additionally accepts a `file` argument for directing the output.

This enables a useful interaction between the settings schema and operational documentation: the same field definitions can generate command-line help, environment-variable annotations, and consistent descriptions of accepted configuration arguments.

`format_help()` and `print_help()` are presentation facilities, not complete provenance or validation-contract exporters. They do not establish that a remote provider is accessible, identify the effective value of every field, or expose every possible runtime source interaction.

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

### 5.2 Environment-name introspection

With `cli_show_env_vars=True`, generated CLI help can include the environment-variable names corresponding to each option.

For fields using `AliasChoices`, the help formatter can expose multiple accepted environment names in their configured priority order.

An explicitly constructed `CliSettingsSource` also exposes an `env_var_names` mapping, keyed by CLI destination, when environment-name help is enabled.

This provides a limited machine-readable introspection facility in addition to human-readable help output.

There is an important source-consistency qualification. When a CLI source is constructed without passing its `_env_settings_source`, it constructs a fallback environment source from the settings model.

That fallback reflects `model_config`, but it may not reflect source-instance overrides such as a customized `env_prefix` or `env_nested_delimiter`.

Consequently, help generated through a separately constructed CLI source can describe different environment names from those actually used by an independently customized runtime environment source.

Passing the customized environment source to the CLI source is how the documented integration preserves consistency.

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

### 5.3 Suppressing options from generated help

Two native mechanisms control whether individual fields appear in help text:

- `CliSuppress[T]` suppresses a field by wrapping its annotated type.
- `CLI_SUPPRESS` suppresses it when supplied as the field description.

For example:

```
from pydantic import Fieldfrom pydantic_settings import CLI_SUPPRESS, BaseSettings, CliSuppressclass Settings(BaseSettings, cli_parse_args=True):    internal_limit: CliSuppress[int] = 100    compatibility_option: str = Field(        default="legacy",        description=CLI_SUPPRESS,    )
```

These mechanisms are useful when an interface needs to retain compatibility options while presenting a smaller public command surface.

They are intentionally help-presentation mechanisms. Suppressing a field does not establish an authorization boundary or prevent users from supplying that option through an otherwise accepted input path.

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

### 5.4 `AliasChoices` and `AliasPath` support composite CLI interfaces

The CLI source understands Pydantic's validation-alias mechanisms, including `AliasChoices` and `AliasPath`.

A field can accept multiple flags, and an `AliasPath` can select an indexed component of a composite argument.

For example:

```
from pydantic import AliasChoices, AliasPath, Fieldfrom pydantic_settings import BaseSettingsclass User(BaseSettings, cli_parse_args=True):    first_name: str = Field(        validation_alias=AliasChoices(            "f",            "first",            AliasPath("fullname", 0),        )    )    last_name: str = Field(        validation_alias=AliasChoices(            "l",            "last",            AliasPath("fullname", 1),        )    )
```

This supports distinct CLI representations such as:

```
--first Ada --last Lovelace
-f Ada -l Lovelace
--fullname Ada,Lovelace
```

One-character aliases become short options automatically.

The capability is particularly relevant to command-line compatibility and interface evolution. Multiple historical names or a composite representation can map to the same validated model fields without implementing a separate preprocessing layer.

This should not be conflated with general configuration-source alias resolution. The CLI has additional argument-grammar semantics, including short options and parsing composite positional components.

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

### 5.5 Union subcommands and dispatch constraints

`CliSubCommand` supports union-typed command models, allowing one declared subcommand field to represent several alternative command classes.

For example, a field annotated as `CliSubCommand[Alpha | Beta]` can accept the command models represented by that union.

However, the name and alias semantics differ from those of an ordinary field:

- Union subcommand names are derived from the component model class names.
- Assigning an alias to a union subcommand field does not rename the individual command alternatives.
- Non-union subcommand aliases can change the exposed command name.
- Command models with indistinguishable content can introduce union-validation ambiguity.
- Only one subparser group is supported per model, although that group can contain multiple subcommands.

`get_subcommand()` can retrieve the selected command model, and `is_required=False` permits a caller to handle the absence of a selected command without immediately raising an error.

For executable command dispatch, `CliApp.run_subcommand()` requires a command-entry method on the selected subcommand. The default method name is `cli_cmd`, but the application-running APIs also support `cli_cmd_method_name` for choosing another entrypoint.

These distinctions matter when using Pydantic models to represent command trees rather than a flat collection of configuration values.

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs+1

### 5.6 Boolean flag modes

The `cli_implicit_flags` option has richer behavior than a simple Boolean switch.

| Mode               | Behavior                                                                                             |
| ------------------ | ---------------------------------------------------------------------------------------------------- |
| `False`            | Booleans take explicit values, such as `--enabled=true`                                              |
| `True` or `"dual"` | Implicit flags expose positive and negative forms                                                    |
| `"toggle"`         | Optional Booleans expose a single flag that changes the default; required Booleans retain dual forms |

For a field with a default of `False`, toggle mode produces a positive flag such as `--enabled`.

For a field whose default is `True`, toggle mode produces the negative flag `--no-enabled`.

The explicit field-level annotations `CliExplicitFlag`, `CliImplicitFlag`, `CliDualFlag`, and `CliToggleFlag` can override the model's general policy.

This makes it possible to express different Boolean interface contracts within one typed command model, rather than manually translating every flag into a separate value representation.

Two adjacent naming details are also relevant:

`cli_kebab_case=True` uses kebab-case naming but does not transform enum fields; `cli_kebab_case="all"` includes them.

`cli_shortcuts` can map nested field paths to shorter options, but shortcut collisions are resolved in favor of the first matching field rather than being treated as an independent namespace.

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs+1

Primary references:

[https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#command-line-support](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#command-line-support)

[https://pydantic.dev/docs/validation/latest/api/pydantic_settings/](https://pydantic.dev/docs/validation/latest/api/pydantic_settings/?utm_source=chatgpt.com)

## 6. Forward-reference resolution and source diagnostics

Extends original §2.2, §9, and §11.

### 6.1 `IncompleteFieldDefinitionWarning`

Settings acquisition depends on the runtime types of model fields.

Those types may not be fully resolved when a settings class is first defined, particularly where forward references, postponed annotations, dynamically imported models, or circular type relationships are involved.

Since pydantic-settings 2.15.0, source processing can emit `IncompleteFieldDefinitionWarning` when it encounters a field whose definition has not been fully resolved.

The warning is significant because the settings source may need to determine whether a field is complex, represents a nested model, or requires JSON decoding before Pydantic performs final validation.

An unresolved field can therefore interfere with acquisition and normalization, not just with model validation.

Pydantic's `model_rebuild()` provides the relevant resolution mechanism once the referenced types are available. For example, the rebuild can be performed after all related model classes have been defined.

The warning is not a guarantee that every possible forward-reference problem can be automatically repaired; the required types must still be resolvable in the model's namespace.

In environments that elevate Python warnings to errors, this warning can cause settings construction to fail. That is a meaningful compatibility distinction for applications using strict diagnostic policies.

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

Primary source:

[https://github.com/pydantic/pydantic-settings/releases/tag/v2.15.0](https://github.com/pydantic/pydantic-settings/releases/tag/v2.15.0?utm_source=chatgpt.com)

### 6.2 Diagnostics for configured but inactive structured-file sources

Pydantic-settings has a further diagnostic safeguard for configuration keys associated with optional structured-file sources.

If the model configures a key such as `json_file`, `yaml_file`, or `toml_file`, but the corresponding source class is not registered, the implementation can emit a `UserWarning` explaining that the setting will be ignored.

The same applies to the relevant format-specific options, including file encodings, YAML section selection, and project TOML discovery configuration.

This is useful because the configuration dictionary alone does not activate those sources.

The warning distinguishes an explicitly configured but inactive source from an ordinary absence of configuration data. It can reveal an incomplete source-registration setup before the resulting missing values become a more ambiguous validation problem.

The implementation performs these checks against the assembled source sequence.

[image](https://www.google.com/s2/favicons?domain=https://raw.githubusercontent.com\&sz=32)

raw\.githubusercontent.com

Primary source:

[https://github.com/pydantic/pydantic-settings/blob/v2.16.2/pydantic_settings/main.py](https://github.com/pydantic/pydantic-settings/blob/v2.16.2/pydantic_settings/main.py?utm_source=chatgpt.com)

## 7. Environment-variable and dotenv correctness distinctions

Extends original §4 and §5.

### 7.1 Unprefixed dotenv entries matching declared fields

The original guide distinguishes environment-variable filtering from dotenv validation. One additional edge case qualifies that distinction.

With `env_prefix` configured, an unprefixed dotenv entry whose name matches a declared field can be silently skipped rather than being treated as an extra value.

Consider:

```
class Settings(BaseSettings):    model_config = SettingsConfigDict(        env_prefix="APP_",        env_file=".env",        extra="forbid",    )    debug: bool = False
```

For this model:

| Dotenv entry     | Behavior                    |
| ---------------- | --------------------------- |
| `APP_DEBUG=true` | Populates `debug`           |
| `debug=true`     | Can be silently ignored     |
| `unrelated=true` | Can raise `extra_forbidden` |

Thus, `extra="forbid"` does not establish the same strict namespace-validation behavior for every possible dotenv entry.

The asymmetry matters particularly where one dotenv file contains values for multiple configuration namespaces or when a prefix has been added to an existing settings model.

It also reinforces the distinction between validating the data that reaches a model and auditing an entire external configuration namespace.

[image](https://www.google.com/s2/favicons?domain=https://pydantic.dev\&sz=32)

Pydantic Docs

### 7.2 Windows environment case sensitivity

On Windows, the operating-system environment handling exposed through Python does not preserve the original case of environment-variable names in a way that permits fully case-sensitive lookup.

Consequently, `case_sensitive=True` does not enforce case-sensitive matching for ordinary process environment variables on Windows.

Dotenv files are different: their parsed keys preserve their written case, so case-sensitive matching remains meaningful for values loaded from those files.

Filesystem secrets are also a distinct source family with their own case-matching behavior. The 2.16.0 release includes a fix ensuring that `secrets_case_sensitive=True` is honored on Windows.

The broader architectural implication is that the same settings-level case-sensitivity policy does not guarantee identical lookup behavior across the process environment, dotenv files, mounted secrets, and cloud providers.

A configuration contract that relies on case alone to distinguish external names may therefore be nonportable even when the resulting Pydantic field schema is unchanged.

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

Primary reference:

[https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#case-sensitivity](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#case-sensitivity)

## 8. Nested secrets: mutually exclusive layout controls

Extends original §6.2.

`NestedSecretsSettingsSource` supports two different representations of hierarchical secret names:

Delimiter-based nesting: A flat directory contains filenames whose names encode multiple configuration levels.

Directory-based nesting: Actual filesystem subdirectories correspond to nested model structure.

The relevant options are `secrets_nested_delimiter` and `secrets_nested_subdir`.

These are alternatives rather than independently composable options.

With `secrets_nested_subdir=True`, the implementation uses the operating system's path separator to interpret nested secret paths.

Explicitly configuring `secrets_nested_delimiter` at the same time raises `SettingsError`.

For example, the following combination is invalid:

```
SettingsConfigDict(    secrets_dir="/run/secrets",    secrets_nested_delimiter="__",    secrets_nested_subdir=True,)
```

This distinction prevents ambiguous interpretations of hierarchical secret names.

It also means that the choice between flat filenames and physical directory hierarchy belongs to the source's naming contract. That choice affects how external secret-provisioning systems should present values, even though the resulting Python settings model can remain unchanged.

The advanced nested-secret options do not activate the nested source automatically; `NestedSecretsSettingsSource` must still be included through source customization, as described in the original guide.

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs

Primary reference:

[https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#nested-secrets](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#nested-secrets)

## 9. `pyproject.toml` discovery and table-selection controls

Extends original §5.4.

### 9.1 Project configuration discovery

`PyprojectTomlConfigSettingsSource` provides a distinct set of configuration controls for locating a Python project's configuration file and selecting a table within it.

Its default behavior is to search for `pyproject.toml` in the current working directory.

`pyproject_toml_depth` permits searching a specified number of parent directory levels when the file is not found in the current directory.

The default depth is zero, so no upward discovery is performed automatically.

The source can also receive an explicit file path during construction. In this case, the specified path is used rather than performing the normal current-directory and parent-directory discovery process.

These modes represent different location contracts:

- Working-directory discovery associates configuration with the process's current execution context.
- Parent-directory discovery can associate configuration with an enclosing Python project.
- Explicit paths select a known configuration resource independently of where the process was launched.

The second and third modes can avoid separate project-root discovery code when the expected file organization matches these contracts.

### 9.2 Table selection is structural, not a dotted string split

The `pyproject_toml_table_header` option selects the TOML table from which settings fields are read.

Its default is:

```
("tool", "pydantic-settings")
```

corresponding to `[tool.pydantic-settings]`.

A custom value such as:

```
("tool", "my_application", "configuration")
```

selects the corresponding nested TOML table.

The representation is a tuple of path components, not a single dot-separated string. This distinction allows individual TOML table-name components themselves to contain periods.

An empty tuple selects the root of the TOML document.

This makes the source useful for structured project configuration without requiring the settings model to reproduce the entire `pyproject.toml` document hierarchy.

### 9.3 Generic TOML has an analogous root-selection mechanism

`TomlConfigSettingsSource` supports `toml_table_header` for selecting a specific table in ordinary TOML configuration files.

An explicitly supplied `toml_table_header=()` on the source constructor selects the root table even if `model_config` defines another table header.

This matters because an empty tuple is an intentional override, not equivalent to omitting the constructor parameter.

The distinction allows an application to reuse a settings schema across TOML files with different internal layouts without modifying the model's field definitions.

[image](https://www.google.com/s2/favicons?domain=https://docs.pydantic.dev\&sz=32)

Pydantic Docs+1

Primary references:

[https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#pyprojecttoml](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/?utm_source=chatgpt.com#pyprojecttoml)

[https://pydantic.dev/docs/validation/latest/api/pydantic_settings/](https://pydantic.dev/docs/validation/latest/api/pydantic_settings/?utm_source=chatgpt.com)

## 10. Architectural synthesis: separating configuration decisions

The preceding capabilities reveal a useful way to reason about the complete pydantic-settings system.

The framework offers several composable boundaries, each with a different responsibility:

| Boundary             | Native mechanisms                                              | Key distinction                                                                             |
| -------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Schema definition    | `BaseSettings`, Pydantic models, aliases, validators           | Defines the accepted configuration and its invariants                                       |
| Source acquisition   | Built-in and custom source objects                             | Determines where input values are obtained and what external work is performed              |
| Source precedence    | `settings_customise_sources`, ordered merging                  | Determines which contribution wins without necessarily avoiding lower-priority acquisition  |
| Default composition  | `DefaultSettingsSource`, `nested_model_default_partial_update` | Controls how populated default models contribute to partially supplied nested configuration |
| Instance context     | Underscore-prefixed constructor overrides                      | Allows one schema to be loaded under different supported acquisition policies               |
| Interface generation | `CliSettingsSource`, `CliApp`, CLI metadata and annotations    | Exposes the schema as a command-line input and documentation contract                       |
| Lifecycle            | Ordinary construction, native cache, explicit reload           | Determines when configuration is reacquired and how objects are shared                      |

These boundaries can be combined to avoid several kinds of bespoke machinery.

A common typed model can support multiple configuration namespaces, structured-file layouts, and cloud providers. Source-state inspection can guide dependent retrieval or selective acquisition. The same model can generate CLI help and validate invocation parameters.

However, the resulting abstraction does not erase differences in provider behavior. Source order does not imply lazy retrieval; aliases can affect the representation available to dependent sources; default-model updates are distinct from source merging; and cloud-provider availability can be handled differently by each adapter.

The practical value of the library therefore extends beyond replacing custom environment-variable parsing. Its more advanced capabilities provide a way to centralize configuration semantics while allowing acquisition, validation, interface presentation, and lifecycle decisions to remain independently understandable.

## Primary-source reference map for this addendum

The references below supplement the source map in the original guide.

| Subject                                        | Direct primary reference                                                                                           |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Version 2.16.2                                 | `https://pypi.org/project/pydantic-settings/2.16.2/`                                                               |
| Tagged settings-resolution implementation      | `https://github.com/pydantic/pydantic-settings/blob/v2.16.2/pydantic_settings/main.py`                             |
| Nested model default updates                   | `https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#nested-model-default-partial-updates`     |
| Source customization and dependent acquisition | `https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#accessing-the-result-of-previous-sources` |
| Settings constructor and API reference         | `https://pydantic.dev/docs/validation/latest/api/pydantic_settings/`                                               |
| AWS provider implementation                    | `https://github.com/pydantic/pydantic-settings/blob/main/pydantic_settings/sources/providers/aws.py`               |
| GCP provider implementation                    | `https://github.com/pydantic/pydantic-settings/blob/main/pydantic_settings/sources/providers/gcp.py`               |
| CLI capabilities and generated help            | `https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#command-line-support`                     |
| Nested filesystem secrets                      | `https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#nested-secrets`                           |
| Configuration files and project TOML           | `https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#other-settings-source`                    |
| Release 2.15 compatibility changes             | `https://github.com/pydantic/pydantic-settings/releases/tag/v2.15.0`                                               |
| Release 2.16 behavior changes                  | `https://github.com/pydantic/pydantic-settings/releases/tag/v2.16.0`                                               |

## Closing perspective

The additions in this document concern the advanced operational semantics of functionality already present in pydantic-settings, rather than newly discovered top-level subsystems.

The most consequential are the separation of source execution from precedence, the independent treatment of populated nested defaults, instance-level acquisition policies, provider-specific version and lookup controls, and CLI metadata generation.

Together, these clarify how pydantic-settings can serve as a composable configuration framework while making its important boundaries explicit: acquisition is not necessarily lazy, source inputs are not necessarily validated before dependent retrieval, different providers do not share identical failure semantics, and a common typed model does not guarantee identical naming or discovery behavior across every configuration surface.