# Installed Protobuf and gRPC tools

The Protobuf/gRPC setup now includes these **32 commands**, with pinned versions:

| Tool | Version | Purpose |
|---|---|---|
| `protoc` | 36.2 | Protobuf compiler |
| `buf` | 1.75.0 | Schema builds, linting, formatting, compatibility checks, and generation |
| `protoc-gen-buf-lint` | 1.75.0 | Buf linting through protoc |
| `protoc-gen-buf-breaking` | 1.75.0 | Breaking-change checks through protoc |
| `grpcurl` | 1.9.4 | Discover and invoke gRPC services |
| `grpcui` | 1.5.4 | Browser-based gRPC explorer |
| `ghz` | 0.121.0 | gRPC load testing |
| `grpc_health_probe` | 0.4.61 | Standard gRPC health checks |
| `evans` | 0.10.11 | Interactive gRPC REPL |
| `granc` | 0.7.7 | Rust-native dynamic gRPC client |
| `protoscope` | Commit `8e7a6aafa2c9` | Inspect and assemble Protobuf wire data |
| `prototext` | 0.3.5 | Lossless binary/text conversion and schema inference |
| `protolens` | 0.3.5 | Interactive binary-message browser |
| `protoscan` | 0.3.5 | Extract descriptors from binaries |
| `reproto` | 0.3.5 | Reconstruct `.proto` schemas from descriptors |
| `reproto-instantiate-schema` | 0.3.5 | Generate sample binary messages |
| `protoc-gen-prost` | 0.5.0 | Generate Rust Prost messages |
| `protoc-gen-tonic` | 0.5.0 | Generate Rust Tonic service bindings |
| `protoc-gen-prost-serde` | 0.4.0 | Generate ProtoJSON-compatible Serde implementations |
| `protoc-gen-prost-crate` | 0.5.0 | Generate Rust module and crate scaffolding |
| `protoweld` | 0.1.2 | Orchestrate multi-language generation |
| `protofetch` | 0.1.22 | Fetch and lock schema dependencies |
| `protolint` | 0.58.0 | Schema linting, fixes, and MCP capability |
| `txtpbfmt` | Commit `7c8a61a7a736` | Format textproto messages |
| `protoc-gen-doc` | 1.5.1 | Generate schema documentation |
| `protoc-gen-jsonschema` | 0.8.0 | Generate JSON Schema |
| `protoc-gen-go` | 1.36.12 | Generate Go message types |
| `protoc-gen-go-grpc` | 1.6.2 | Generate Go gRPC bindings |
| `protoc-gen-grpc-gateway` | 2.33.0 | Generate Go HTTP/JSON gateways |
| `protoc-gen-openapiv2` | 2.33.0 | Generate Swagger/OpenAPI 2 specifications |
| `protoc-gen-openapiv3` | 2.33.0 | Generate OpenAPI 3.1 specifications; alpha |
| `otelcol-contrib` | 0.164.0 | Receive, process, and export telemetry |

The supporting diagnostic tools available now include:

| Tool | Purpose |
|---|---|
| `nghttp` | HTTP/2 inspection |
| `h2load` | HTTP/2 load testing |
| `wireshark` | Graphical packet analysis |
| `tshark` | Command-line packet analysis; newly installed |
| `tcpdump` | Packet capture |
| `ngrep` | Packet pattern matching; newly installed |
| `strace` | System-call tracing |
| `socat` | Network relays and socket testing |
| `bpftrace` | Kernel and application tracing |
| `bpfcc-tools`, including `opensnoop-bpfcc` | BCC-based performance diagnostics |
| `hyperfine` | CLI benchmarking |
| `flamegraph` / `cargo-flamegraph` | Rust CPU profiling |
| `grpc_cpp_plugin` | C++ gRPC generation; newly installed |

C/C++ support also includes `libprotobuf-dev`, `libgrpc-dev`, and `libgrpc++-dev`, plus their required Abseil, c-ares, RE2, and runtime dependencies.

Your existing Go **1.27.2**, stable Rust **1.99.1**, LLVM **23**, and uv **0.13.6** remain available. Default Python remains **3.14.10**; the two `reproto` commands use an isolated Python **3.13.18** environment.

Ubuntu’s older compiler remains available as `/usr/bin/protoc` for matching C++ builds. Legacy `protoc-gen-validate` was intentionally omitted.
