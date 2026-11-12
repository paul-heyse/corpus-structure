# PyTorch (`torch`) — Comprehensive Python Library Reference

Research date: November 12, 2026 | Target version: PyTorch 2.15.0 (stable, released October 28, 2026)

Official repository: `https://github.com/pytorch/pytorch`\
Documentation: `https://docs.pytorch.org/docs/2.15/`\
Package: `https://pypi.org/project/torch/`

## 1. Executive overview

PyTorch is a general-purpose tensor computation, automatic differentiation, and machine-learning execution framework. Although best known for deep neural networks, its capabilities extend into GPU-accelerated numerical computing, differentiable programming, compilation, heterogeneous hardware execution, distributed computation, and high-performance inference.

Its defining architectural characteristic is the combination of a flexible Python programming model with a performance-oriented native execution system, compiler infrastructure, and device-specific kernels.

PyTorch 2.15 additionally expands distributed fault tolerance, accelerator execution, precision management, and compilation. Notable changes include a rewritten default NCCL backend, one-sided distributed communication through NIXL, finer FSDP2 and pipeline controls, improved low-precision GPU execution, and broader accelerator support.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://pytorch.org\&sz=32)

PyTorch+1



### 1.1 The important distinction: computation versus job orchestration

For systems that execute many different workloads from a common Python codebase, PyTorch provides several useful execution and concurrency primitives, but it is not itself a general-purpose job orchestration, scheduling, or multi-service management platform.

This distinction matters because several mechanisms that appear to address similar problems actually operate at different layers.

| Requirement                                                           | PyTorch capability                                           | Boundary                                          |
| --------------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------- |
| Execute tensor operations on CPU/GPU                                  | Native, extensive                                            | Core responsibility                               |
| Run multiple computations concurrently                                | CUDA streams, asynchronous operations, threads and processes | Does not schedule independent application jobs    |
| Run separate GPU worker processes                                     | `torch.multiprocessing`                                      | No durable queue or global resource scheduler     |
| Parallelize one training job over GPUs                                | `torch.distributed`, DDP, FSDP2, DTensor                     | Designed for coordinated computation              |
| Launch and recover distributed training workers                       | `torchrun`, TorchElastic                                     | Job execution, not general workflow orchestration |
| Reuse a GPU across multiple model workloads                           | Device contexts, streams, memory management                  | Resource arbitration remains external             |
| Deploy multiple independently scalable inference services             | Integrates with inference-serving frameworks                 | Not provided by `torch` alone                     |
| Schedule heterogeneous jobs with priorities, retries and dependencies | No unified native implementation                             | External job runtime or workflow engine           |
| Coordinate workers across multiple machines                           | Distributed primitives and companion frameworks              | General-purpose cluster scheduling is external    |

A useful mental model is to separate four responsibilities:

Job orchestration and service management

Ray, Celery, Temporal, Dagster, Prefect, Kubernetes

Worker execution and distributed runtime

Processes, actors, services, TorchElastic, Monarch

PyTorch computation and model execution

Tensor operations, autograd, modules, compiled graphs, distributed tensor operations

Hardware execution

CPU, CUDA, ROCm, MPS, XPU, hardware runtimes and memory managers

These layers are composable. An external scheduler can manage a long-lived PyTorch worker, while PyTorch manages the tensor operations and GPU execution inside that worker. Conversely, distributed PyTorch can coordinate hundreds of GPUs for one logical training job without providing application-level scheduling for unrelated tasks.

For a Python system with multiple services, the most consequential adjacent technologies are Ray, Monarch, Celery, Temporal, and specialized model-serving frameworks. They address different parts of the problem and are examined in detail later.

## 2. Tensor computation and numerical capabilities

### 2.1 Tensor representation, memory and device semantics

`torch.Tensor` is the principal data abstraction. A tensor combines a multidimensional array's values with metadata defining its shape, data type, device, layout, strides, storage relationships and optional gradient-tracking behavior.

Unlike a generic numerical array, the same tensor programming interface can participate in automatic differentiation, device execution, compilation and distributed tensor computation.

| Capability              | Native mechanisms                                                   | Consequential behavior                                                                |
| ----------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| Multidimensional arrays | `Tensor`, broadcasting, indexing, slicing                           | Vectorized computation on CPU and accelerators                                        |
| Memory layouts          | Strided, channels-last, sparse layouts                              | Physical representation influences performance                                        |
| Views and aliasing      | `view`, `transpose`, `permute`, `as_strided`, `reshape`             | Some transformations share storage; others allocate copies                            |
| Numeric precision       | FP64, FP32, TF32 execution modes, FP16, BF16, FP8 and integer types | Supported arithmetic depends on device and kernel                                     |
| Complex arithmetic      | Complex tensors, conjugation, complex linear algebra                | Useful in signal processing, scientific computing and differentiable complex programs |
| Device transfers        | `Tensor.to`, pinned memory, nonblocking copies                      | Movement can be explicit and asynchronous                                             |
| Interoperability        | NumPy, DLPack, C++ and custom extensions                            | Can reduce unnecessary copies across numerical frameworks                             |
| Sparse and ragged data  | Sparse COO/CSR/CSC/BSR/BSC; nested tensors                          | Avoids representing all sparse structures as dense arrays                             |

A particularly important distinction is between a tensor view and a tensor copy. Views reuse the underlying storage; changes to a view may affect its source. Operations requiring a different physical layout may allocate fresh storage even when the new logical shape appears simple.

This matters in performance-sensitive systems because what looks like a cheap shape transformation in Python can trigger device memory allocation or a copy.

Source: `https://docs.pytorch.org/docs/2.15/tensor_view.html`&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation+1



### 2.2 General-purpose mathematical computing

PyTorch has a broader numerical scope than neural-network training.

Linear algebra: `torch.linalg` supports linear systems, least-squares problems, matrix factorizations, eigenvalue problems, SVD, QR, LU, Cholesky, matrix rank, norms, pseudoinverses and matrix functions.

Signal processing and transforms: `torch.fft` provides multidimensional real and complex FFTs, inverse transforms, frequency utilities and related operations.

Statistical and probabilistic computing: Tensor reductions, random sampling, `torch.distributions`, special mathematical functions and random number generators provide a base for Monte Carlo methods and differentiable statistical computation.

Structured tensor computation: Batched matrix products, tensor contractions, `einsum`, broadcasting, indexed updates, gather/scatter operations and advanced reductions support substantial computations without constructing Python loops.

Differentiable numerical algorithms: Provided the operations have appropriate gradient support, programs can differentiate through linear algebra, iterative calculations, simulation steps and optimization-related functions.

These capabilities make PyTorch potentially useful even when the primary workload is not conventional machine learning. Its advantage is particularly strong when a calculation benefits from batched GPU operations and differentiability.

However, native numerical functionality does not make it a complete general-purpose scientific solver. Specialized sparse direct solvers, constrained nonlinear optimizers and mathematical-programming solvers remain separate capabilities. PyTorch can provide differentiable tensor operations within those larger systems, but it does not replace packages such as SciPy or dedicated optimization solvers.

Sources: `https://docs.pytorch.org/docs/2.15/linalg.html`, `https://docs.pytorch.org/docs/2.15/fft.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation+1



### 2.3 Sparse and irregular tensors

PyTorch supports compressed sparse layouts and sparse operations to avoid allocating dense representations when most entries are zero.

The important distinction is that sparse storage support does not imply parity with dense tensor operator coverage. Particular arithmetic, device, dtype and autograd combinations may be unsupported.

Nested tensors address a different problem: irregular shapes, especially sequences with variable lengths. The `torch.jagged` layout stores values in a packed representation with offsets describing batch boundaries.

This can avoid padding all sequences to the longest sequence in a batch. PyTorch documents useful interactions with `torch.compile`, although the nested-tensor APIs still have incomplete operator coverage and development-status qualifications.

For workloads with variable-length inputs, packed execution can reduce unnecessary arithmetic and memory consumption, but the benefit depends on the model's operators and supported kernels.

Sources: `https://docs.pytorch.org/docs/2.15/sparse.html`, `https://docs.pytorch.org/docs/2.15/nested.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation+1



## 3. Automatic differentiation and functional transformations

### 3.1 Autograd's execution model

`torch.autograd` is a native automatic differentiation engine.

During ordinary eager execution, PyTorch records differentiable operations in a dynamic computation graph. Backpropagation traverses that graph to compute derivatives.

The graph is reconstructed as execution proceeds, allowing ordinary Python control flow to select different computational paths.

Core facilities include `backward()`, `torch.autograd.grad()`, custom `autograd.Function` implementations, forward-mode automatic differentiation and higher-order derivatives.

Autograd also exposes mechanisms that are important for advanced numerical systems: gradient hooks, saved-tensor hooks, anomaly detection, gradient checking and custom derivative rules.

The key architectural opportunity is that derivative generation can be part of the numerical program rather than a separate symbolic or hand-coded implementation.

There are limits. Only supported differentiable types and operations participate in autograd, in-place mutations must respect graph invariants, and some operations have undefined or numerically unstable derivatives.

Source: `https://docs.pytorch.org/docs/2.15/notes/autograd.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation+1



### 3.2 `torch.func`: composable differentiation and vectorization

`torch.func`, originating from functorch, is one of PyTorch's most consequential advanced capabilities.

Rather than operating primarily on stateful modules and gradient accumulation, it transforms Python functions into new numerical functions.

| Transformation    | Purpose                                                | Advanced applications                                    |
| ----------------- | ------------------------------------------------------ | -------------------------------------------------------- |
| `grad`            | Gradient of a function                                 | Differentiable objectives                                |
| `grad_and_value`  | Compute gradient and function value                    | Optimization loops                                       |
| `vjp`             | Vector-Jacobian product                                | Reverse-mode sensitivity analysis                        |
| `jvp`             | Jacobian-vector product                                | Directional derivatives and matrix-free methods          |
| `jacrev`          | Jacobian via reverse-mode AD                           | Jacobians with comparatively few outputs                 |
| `jacfwd`          | Jacobian via forward-mode AD                           | Jacobians with comparatively few inputs                  |
| `hessian`         | Second derivative matrix                               | Curvature and second-order optimization                  |
| `vmap`            | Vectorize function execution over a batch dimension    | Per-example operations without explicit Python loops     |
| `functional_call` | Evaluate a module with supplied parameters and buffers | Stateless model evaluation and parameter transformations |

The main advantage is composition.

For example, `vmap(grad(f))` computes per-example gradients; `jacfwd(jacrev(f))` computes a Hessian using a forward-over-reverse strategy.

These compositions are valuable for sensitivity analysis, per-sample gradients, meta-learning, uncertainty estimation and differentiable numerical methods. They can eliminate substantial custom derivative and batching machinery.

However, `vmap` is not a job queue or a distributed scheduler. It vectorizes related operations inside a computational workload. Individual mapped operations are not independent durable jobs with separate lifecycles.

`torch.func` remains documented as beta, and transform compatibility varies by operator. Forward-mode differentiation does not yet cover every operator supported by reverse-mode AD.

Source: `https://docs.pytorch.org/docs/2.15/func.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.14 documentation+2



## 4. Neural-network construction and training

### 4.1 Stateful model composition

`torch.nn.Module` provides the central abstraction for stateful computational models.

Modules register parameters, buffers and child modules, forming hierarchical structures with discoverable state and reusable execution behavior.

The surrounding `torch.nn` and `torch.nn.functional` APIs provide transformations such as linear layers, convolutions, normalization, attention, activations, recurrent operations, embeddings, losses and many other building blocks.

Advanced capabilities include parameter tying, module hooks, state-dictionary hooks, parametrizations, custom forward and backward behavior, and lazy or device-aware initialization patterns.

This makes `nn.Module` more than a neural-network layer container. It is a mechanism for combining parameterized computation with structured state management.

For a system executing multiple distinct models, modules can share definitions and utility functions without sharing mutable runtime instances.

### 4.2 Optimization and mixed precision

`torch.optim` supplies first-order optimization algorithms, parameter groups, stateful optimizers, learning-rate schedules and optimizer hooks.

Parameter groups allow different subsets of model parameters to have different optimization policies.

Where supported, `foreach` and fused implementations reduce overhead by operating on groups of parameters more efficiently.

Automatic Mixed Precision through `torch.autocast` and `torch.amp.GradScaler` lets selected operations execute at reduced precision while preserving higher precision where required.

It is important to distinguish BF16, FP16, FP8 and TF32. They differ in exponent range, mantissa precision, overflow behavior and available hardware operations; they are not interchangeable performance settings.

### 4.3 Memory-efficiency mechanisms

PyTorch provides several complementary approaches to reducing training memory requirements.

Activation checkpointing recomputes selected intermediates during backward execution rather than retaining them throughout the forward pass. This trades additional computation for lower activation-memory consumption.

More advanced selective checkpointing supports policies at the operator level. In PyTorch 2.15, policy options include mandatory or preferred saving, recomputation and CPU offloading. These policies interact with compilation and autograd behavior.

FSDP2, covered later, attacks a different source of memory pressure by sharding model parameters, gradients and optimizer states between GPUs.

The distinction matters: activation checkpointing reduces retained intermediates, whereas sharding distributes persistent model state.

Source: `https://docs.pytorch.org/docs/2.15/checkpoint.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation+1



### 4.4 Attention and variable-length execution

PyTorch includes scaled dot-product attention and backend dispatch to optimized attention implementations where supported.

It also provides newer attention functionality, including FlexAttention, which allows more expressive attention-score modifications and masking strategies to participate in optimized execution.

Together with jagged tensors, compilation and low-precision kernels, these capabilities support transformer architectures beyond basic dense attention.

The most consequential distinction is between expressing an attention operation and choosing its execution backend. Shape, masking, dtype and hardware support determine which optimized kernel can actually execute.

## 5. Compilation, graph transformations and execution optimization

PyTorch 2.x includes a substantial compiler architecture. This is one of its most important capabilities for building high-performance, reusable computation services.

### 5.1 `torch.compile`

`torch.compile` attempts to capture portions of Python/PyTorch execution and compile them into optimized executable graphs.

Its main components are:

| Component                       | Responsibility                                        |
| ------------------------------- | ----------------------------------------------------- |
| TorchDynamo                     | Captures Python execution into graph regions          |
| FX                              | Represents and transforms captured computation graphs |
| AOTAutograd                     | Captures and partitions forward/backward computations |
| TorchInductor                   | Lowers graphs into optimized execution code           |
| Triton and other kernel systems | Execute generated device kernels                      |

Inductor can perform fusion, code generation, kernel selection and autotuning. On supported devices it can leverage optimized CUDA-oriented or other accelerator-specific compilation routes.

The primary benefit is not simply fewer Python instructions. Compilation may fuse operations, reduce memory traffic, eliminate unnecessary intermediate tensors and choose more efficient kernels.

### 5.2 Compilation modes and specialization

`torch.compile` supports modes including `default`, `reduce-overhead`, `max-autotune` and `max-autotune-no-cudagraphs`.

`reduce-overhead` targets Python launch overhead, particularly through CUDA Graphs where applicable. `max-autotune` explores optimized kernel choices at the cost of more compilation preparation.

Compilation is guarded by assumptions about the program and inputs. Different shapes, dtypes, devices or Python conditions may require separate compiled variants.

Dynamic shape support can reduce shape-driven recompilation, but it is not unlimited. Data-dependent output shapes and unsupported control flow remain consequential constraints.

The compiler also supports backend extensibility, allowing integration with alternatives such as Torch-TensorRT, OpenVINO or other compilation systems where compatible.

For multiple services, the key implication is that each workload may have its own compilation behavior, cache characteristics, initialization cost and optimal execution mode. Compiling every function is not automatically beneficial, especially for short-lived or highly variable jobs.

Sources: `https://docs.pytorch.org/docs/2.15/generated/torch.compile.html`, `https://docs.pytorch.org/docs/2.15/user_guide/torch_compiler/torch.compiler_troubleshooting.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation+2



### 5.3 FX and program transformation

`torch.fx` is a Python-level graph-transformation toolkit containing a symbolic tracer, graph intermediate representation and Python code-generation system.

It allows programs to inspect operations, identify patterns, rewrite graph regions, substitute implementations and reconstruct executable modules.

Its usefulness is broader than automatic performance optimization. It supports graph analysis, instrumentation, model rewriting, partitioning and integration with external execution backends.

FX symbolic tracing has important limitations around data-dependent Python control flow. A graph captures what its tracing mechanism can represent; it is not an unrestricted serialization of the entire Python application.

Source: `https://docs.pytorch.org/docs/2.15/fx.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation



### 5.4 `torch.export` and ahead-of-time deployment

`torch.export` differs from `torch.compile` in a fundamental way.

`torch.compile` primarily optimizes execution of Python programs and manages compiled variants at runtime. `torch.export` attempts to produce a more explicit, portable representation of tensor computation with recorded constraints.

An exported program uses normalized tensor operations and records assumptions required for its validity.

This makes export useful when an execution environment should not depend on the original Python control flow.

Related deployment paths include AOTInductor packages, ONNX export, Torch-TensorRT and ExecuTorch.

| Mechanism           | Primary role                                                    |
| ------------------- | --------------------------------------------------------------- |
| `torch.compile`     | Optimize execution while retaining the Python programming model |
| `torch.export`      | Capture a constrained computational program                     |
| AOTInductor         | Compile an exported program into an ahead-of-time artifact      |
| `torch.onnx.export` | Translate supported models to ONNX                              |
| ExecuTorch          | Run prepared models on mobile and edge hardware                 |
| Torch-TensorRT      | Lower supported PyTorch workloads to TensorRT execution         |

These mechanisms are not automatically interchangeable. Exportability, supported operators, dynamic shape constraints, target hardware and runtime requirements must be evaluated separately.

The export-based ONNX path is the modern PyTorch direction. TorchScript remains relevant to existing deployments, but is no longer the preferred starting point for new graph-export pipelines.

Sources: `https://docs.pytorch.org/docs/2.15/user_guide/torch_compiler/export/programming_model.html`, `https://docs.pytorch.org/docs/2.15/onnx.html`, `https://docs.pytorch.org/executorch/stable/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation+2



### 5.5 Custom operators and compiler interoperability

`torch.library` provides operator registration mechanisms that allow nonstandard implementations to participate in PyTorch's dispatcher and transformation infrastructure.

Among the important interfaces are `custom_op`, `triton_op`, `register_kernel`, `register_fake`, `register_autograd` and `opcheck`.

Custom operators require explicit contracts about mutation and aliasing. These are not merely documentation requirements: they affect functionalization, tracing, compilation and automatic differentiation.

A particularly important distinction is that `custom_op` can treat its implementation as opaque, while `triton_op` exposes supported Triton-backed computation for compiler optimization.

At lower levels, C++/CUDA extensions and dispatcher integrations support custom kernels, accelerator backends and specialized execution behavior.

This enables PyTorch to act as a common computational interface even when particular operations are implemented elsewhere.

Source: `https://docs.pytorch.org/docs/2.15/library.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation+1



## 6. Distributed computation and large-scale training

PyTorch's distributed APIs are sophisticated, but most are designed to execute one coordinated computational job across multiple processes or accelerators.

That distinction is essential when comparing distributed PyTorch with general-purpose job-management systems.

### 6.1 Collective communication and device meshes

`torch.distributed` provides communication primitives through process groups and backend implementations.

The central model is a collection of processes, typically with one process responsible for each GPU, communicating through collective or point-to-point operations.

Supported communication patterns include all-reduce, reduce-scatter, all-gather, broadcast, barriers and process-to-process communication.

Collectives are useful because distributed training and numerical computation frequently involve synchronized exchange of intermediate data or gradients.

The higher-level `DeviceMesh` abstraction represents the topology of participating devices. `DTensor` attaches distributed placement semantics to tensors, including replication and sharding.

This allows distributed computations to be expressed in terms of logical tensor placements rather than manually implementing every communication operation.

In PyTorch 2.15, the distributed communication subsystem also incorporates the rewritten NCCL backend and newer NIXL-based communication facilities. These changes are relevant to coordinated accelerator workloads, not to durable scheduling of unrelated application jobs.

Sources: `https://docs.pytorch.org/docs/2.15/distributed.html` and `https://docs.pytorch.org/tutorials/beginner/dist_overview.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

torch.distributed — PyTorch 2.15 documentation+2



### 6.2 Distinct forms of parallelism

| Mechanism                           | How work is distributed                                | Primary purpose                                       | Important limitation                                  |
| ----------------------------------- | ------------------------------------------------------ | ----------------------------------------------------- | ----------------------------------------------------- |
| DistributedDataParallel (DDP)       | Replicated model, different data partitions            | Scale training throughput                             | Each rank normally maintains a full model replica     |
| Fully Sharded Data Parallel (FSDP2) | Sharded parameters, gradients and optimizer states     | Train models too large for efficient full replication | Communication and synchronization overhead            |
| Tensor parallelism                  | Partition individual tensor operations or layers       | Execute large layers across accelerators              | Frequent inter-device communication                   |
| Pipeline parallelism                | Partition model stages and process microbatches        | Distribute deep models across devices                 | Pipeline bubbles, stage balance and shape constraints |
| Hybrid parallelism                  | Compose data, tensor, pipeline and sharding dimensions | Scale very large distributed workloads                | More complex topology and communication management    |

FSDP2's `fully_shard` API builds on DTensor and uses parameter-level sharding rather than the earlier FSDP1 flattened-parameter model. Parameters can be all-gathered for execution and subsequently reshard, while gradients are reduced and distributed.

Pipeline parallelism introduces schedules such as GPipe, 1F1B and interleaved variants. These are execution schedules inside a model, not scheduling algorithms for unrelated service requests.

Different parallelism strategies can be composed, but each composition introduces communication, memory and synchronization consequences. More GPUs do not automatically yield better efficiency.

Sources: `https://docs.pytorch.org/docs/2.15/distributed.fsdp.fully_shard.html` and `https://docs.pytorch.org/docs/2.15/distributed.pipelining.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation+1



### 6.3 TorchElastic and `torchrun`

TorchElastic provides fault-tolerant distributed worker execution.

`torchrun` can launch a process group across one or more machines, coordinate rendezvous, respond to worker failures and restart a group according to configured policies.

Its mechanisms include elastic membership, restart budgets, rank assignment and distributed job initialization.

This is meaningful process supervision, but the unit being supervised is fundamentally a distributed worker group participating in a logical job.

For example, `torchrun` can manage eight coordinated training processes. It does not provide the general service-level semantics needed to manage a document-processing queue, embedding service, classifier, model-training service and arbitrary background computations with independent priorities and retry policies.

For those requirements, TorchElastic is a potential execution component beneath an external orchestrator, not a replacement for one.

Source: `https://docs.pytorch.org/docs/2.15/elastic/run.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation+1



### 6.4 Distributed checkpointing

`torch.distributed.checkpoint` (DCP) provides coordinated saving and loading of distributed state.

Its particularly valuable capabilities include parallel I/O across ranks, saving distributed tensor shards, load-time resharding and asynchronous checkpoint operations.

Load-time resharding allows checkpoint state to be restored into a different distributed topology where supported.

Checkpointing is central to fault recovery, but checkpoint files do not themselves provide durable job definitions, retry policies, task queues or service lifecycle management.

Source: `https://docs.pytorch.org/docs/2.15/distributed.checkpoint.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch main documentation+1



## 7. Managing multiple independent jobs and services

This is where PyTorch's native capabilities and its ecosystem need to be distinguished most carefully.

### 7.1 Four different meanings of concurrent execution

It is useful to distinguish four requirements that are often described simply as running multiple jobs.

| Type                                       | Example                                                                               | Appropriate execution model                          |
| ------------------------------------------ | ------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| Parallel operations                        | Thousands of similar computations evaluated together                                  | Tensor batching, `vmap`, kernels                     |
| Concurrent operations in one process       | Overlapping transfers and GPU kernels                                                 | CUDA streams, asynchronous execution                 |
| Independent background jobs                | Different computations with separate inputs, errors and completion states             | Worker processes, task queues, Ray tasks             |
| Long-lived independently scalable services | Embedding, classification and inference endpoints, each with different resource needs | Actors, service deployments, container orchestration |

PyTorch handles the first two directly and supplies important building blocks for the third.

It does not supply one integrated system that turns all four into independently scheduled, durable, observable services.

### 7.2 Native multiprocessing

`torch.multiprocessing` extends Python's standard multiprocessing module with tensor-aware data sharing.

CPU tensors sent between compatible processes can share their underlying storage rather than requiring an ordinary serialized copy of all tensor data.

CUDA tensors can also be transferred between processes using CUDA interprocess-sharing mechanisms, subject to stricter lifecycle requirements.

This enables useful patterns such as independent worker processes, asynchronous training algorithms, process-based producer-consumer pipelines and CPU preprocessing alongside GPU computation.

However, creating multiple processes is not equivalent to managing a job service.

For independent production-style jobs, the application still needs to determine how work is submitted, queued, assigned, retried, cancelled and monitored.

CUDA multiprocessing constraints are significant:

- CUDA should not be initialized in a process that is subsequently forked into CUDA workers; `spawn` or `forkserver` is needed for appropriate CUDA subprocess use.
- CUDA tensor sharing imposes producer/consumer lifetime obligations, and abnormal consumer termination can complicate cleanup.
- Multiple processes may independently initialize models, CUDA contexts and allocator pools, duplicating GPU memory consumption.
- Native queues do not provide durable delivery, scheduling priorities, distributed discovery or automatic recovery after a machine failure.

These are reasons to distinguish a multiprocessing primitive from a managed worker runtime.

Sources: `https://docs.pytorch.org/docs/stable/notes/multiprocessing.html` and `https://docs.pytorch.org/docs/2.15/multiprocessing.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.14 documentation



### 7.3 Threads, asynchronous execution and data-loading workers

PyTorch also supports several forms of concurrency below the independent-job level.

CPU operations can use intra-operation and inter-operation thread pools. `torch.set_num_threads` and `torch.set_num_interop_threads` expose relevant controls, subject to initialization and lifecycle constraints.

GPU operations are commonly enqueued asynchronously relative to the Python host. CUDA streams can permit overlapping work where the device, data dependencies and available resources allow.

`DataLoader` can use multiple worker processes, prefetching and pinned memory to prepare batches concurrently with model execution.

These capabilities are useful, but their scheduling scopes are different.

`DataLoader` workers serve a data-ingestion pipeline. CUDA streams schedule ordered device operations. CPU thread pools parallelize operator execution.

None is a general-purpose manager of independently addressed application services.

Sources: `https://docs.pytorch.org/docs/2.15/data.html`, `https://docs.pytorch.org/docs/2.15/notes/cuda.html`, and `https://docs.pytorch.org/docs/2.15/generated/torch.set_num_threads.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch main documentation+2



### 7.4 Distributed RPC: important historical capability

PyTorch has a distributed RPC framework supporting remote function execution, remote object references, distributed autograd and related coordination patterns.

This is substantially closer to application-level remote invocation than collective distributed training.

However, its lifecycle status matters. At the PyTorch 2.15 baseline, the RPC framework is maintained rather than being the main area of new distributed-runtime development. Newer development documentation identifies deprecation beginning in 2.16 and directs users toward alternatives such as Monarch, Ray and conventional service RPC.

Accordingly, its existing capabilities should be understood separately from its suitability as the foundation of a new multi-service platform.

Source: `https://docs.pytorch.org/docs/stable/rpc.html`; development status: `https://docs.pytorch.org/docs/main/distributed/rpc.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.14 documentation+1



### 7.5 What an independent job-management layer adds

A service-oriented workload manager generally has responsibilities not implemented as a unified subsystem in `torch`.

| Requirement                | Why it matters                                                                      |
| -------------------------- | ----------------------------------------------------------------------------------- |
| Job identity and lifecycle | Submit, inspect, cancel and recover an individual job                               |
| Routing                    | Send different work classes to appropriate services or worker pools                 |
| Resource-aware admission   | Avoid launching more CPU/GPU work than available resources can sustain              |
| Queueing and backpressure  | Bound outstanding work and protect shared resources                                 |
| Failure isolation          | Keep one failed job from terminating unrelated services                             |
| Retry and timeout policies | Handle transient failures and unresponsive workers                                  |
| Durable execution state    | Recover submitted work after process or machine failures                            |
| Service scaling            | Scale different types of workers independently                                      |
| Dependency scheduling      | Start downstream work only when prerequisite results are available                  |
| Observability              | Attribute queue delay, device usage, failures and throughput to each job or service |

Some of these can be written around `torch.multiprocessing` and Python standard-library facilities.

The relevant architectural tradeoff is whether custom implementation of this machinery remains justified when an existing runtime already supplies it.

## 8. Multiple jobs sharing the same GPU

Executing unrelated PyTorch workloads on one GPU is technically possible, but resource sharing is more complicated than merely launching multiple processes.

### 8.1 GPU execution versus memory ownership

CUDA permits multiple processes to use a GPU, subject to hardware capacity, drivers and runtime configuration.

However, each process ordinarily maintains its own CUDA context, model allocations and caching-allocator state.

A worker can therefore consume substantial GPU memory before performing any active computation.

When several services maintain separate model instances, their resident model weights can dominate memory consumption. Concurrent execution may then be limited primarily by memory capacity rather than computing throughput.

### 8.2 CUDA streams

CUDA streams represent ordered sequences of device operations.

Independent streams can overlap eligible kernel execution and data transfers, but overlap is not guaranteed. Dependencies, memory bandwidth, kernel occupancy and hardware scheduling all matter.

A CUDA stream does not provide a durable job identifier, service-level priority, retry logic or memory isolation.

CUDA Graphs address a different optimization: capturing eligible operations for low-overhead replay. They can be particularly effective for stable, repeated inference workloads, but impose constraints on memory, captured operation structure and execution dependencies.

Source: `https://docs.pytorch.org/docs/2.15/notes/cuda.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation+1



### 8.3 Memory limits and resource scheduling

`torch.cuda.memory.set_per_process_memory_fraction` constrains allocations managed by PyTorch's caching allocator for a process.

That is not equivalent to partitioning physical GPU memory between services. CUDA allocations outside the relevant allocator and other processes can still consume device resources.

Similarly, a resource scheduler that allocates fractional GPUs may be doing logical admission control, not enforcing physical hardware isolation.

For example, two workers configured to use half a GPU each may both run on the same physical GPU, yet still compete for VRAM and compute resources.

Source: `https://docs.pytorch.org/docs/2.15/generated/torch.cuda.memory.set_per_process_memory_fraction.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation



### 8.4 Approaches to GPU sharing

| Strategy                                     | What it offers                                                          | Important qualification                                                      |
| -------------------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| One long-lived worker hosting several models | Shared process, controlled scheduling and potential reuse of resources  | Models still consume memory; independent service isolation is reduced        |
| Several PyTorch worker processes             | Fault and lifecycle isolation                                           | Separate contexts, allocators and potentially duplicated model weights       |
| CUDA streams                                 | Overlap eligible computations within an execution context               | No independent-job scheduling or hard resource isolation                     |
| NVIDIA Multi-Process Service (MPS)           | GPU execution sharing across CUDA processes                             | Does not replace application scheduling or guarantee isolated memory budgets |
| NVIDIA Multi-Instance GPU (MIG)              | Hardware-partitioned GPU instances on supported devices                 | Device-specific support and partitioning constraints                         |
| Ray GPU resource scheduling                  | Assign workers to GPU resources; support fractional logical allocations | Logical allocation alone does not enforce a VRAM quota                       |
| External batch queues                        | Serialize or limit the number of GPU-intensive jobs                     | May reduce concurrency to avoid memory contention                            |
| Dynamic batching                             | Combine compatible inference requests into larger batches               | Best suited to compatible model execution, not unrelated computations        |

For a single GPU running heterogeneous workloads, a long-lived GPU actor or service is often a useful option because it can own the accelerator lifecycle and control how requests enter execution.

That is an architectural option, not a universal optimization. It may be inappropriate when workloads require separate failure domains, incompatible dependencies, strict latency isolation or independent scaling.

NVIDIA documentation: `https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/`. Ray scheduling documentation: `https://docs.ray.io/en/latest/ray-core/scheduling/resources.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.nvidia.com\&sz=32)

NVIDIA Multi-Instance GPU User Guide+1



## 9. Libraries for multiple jobs and services

Several external packages address the capabilities that `torch` does not provide. They differ substantially in their execution models, even when all can run PyTorch code.

### 9.1 Comparison of the main options

| Library                        | Primary abstraction                     | Multiple heterogeneous workloads        | GPU-aware execution                       | Durable workflows                                                                 | Long-lived model services                                  |
| ------------------------------ | --------------------------------------- | --------------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| TorchX                         | Job specification and launcher          | Yes, including multi-role jobs          | Through scheduler resource declarations   | No native DAG engine                                                              | Not its primary purpose                                    |
| Monarch                        | Distributed actors and process meshes   | Yes                                     | GPU process meshes and explicit placement | Not a general durable workflow engine                                             | Possible, but infrastructure is application-defined        |
| Ray Core                       | Distributed tasks and actors            | Yes, directly                           | Logical GPU scheduling and placement      | Retries and recovery; not a full durable workflow engine                          | Yes, through actors                                        |
| Ray Serve                      | Model-serving deployments               | Yes, multiple services and applications | Yes                                       | No                                                                                | Yes, central purpose                                       |
| Celery                         | Broker-backed task queues               | Yes, with named queues and workers      | No native GPU resource allocator          | Task retries and persistence depend on configuration; limited workflow primitives | Not a model-serving framework                              |
| Temporal                       | Durable workflows and activities        | Yes                                     | External worker/device placement          | Yes, central purpose                                                              | Orchestrates service activities rather than serving models |
| Prefect / Dagster              | Workflows, pipelines and scheduled runs | Yes                                     | Through execution infrastructure          | Yes, with different execution semantics                                           | Not their primary purpose                                  |
| BentoML                        | Model APIs and service deployment       | Yes                                     | Yes                                       | Includes asynchronous task facilities; not a general workflow engine              | Yes                                                        |
| NVIDIA Triton Inference Server | Model instances and inference requests  | Yes, across models                      | Yes, with model-instance scheduling       | No general application workflow engine                                            | Yes                                                        |

The distinction between TorchX, Monarch and Ray is especially important because they are the closest matches to the requested combination of Python, PyTorch, heterogeneous workloads and multiple services.

### 9.2 TorchX: portable execution of heterogeneous jobs

TorchX is a separate project in the PyTorch ecosystem, not part of the `torch` Python package.

It is a general job launcher whose central abstractions are `AppDef`, `Role`, `Resource`, `Component`, `Runner` and `Scheduler`.

`AppDef` defines an application job. An application can contain several `Role` objects, each with its own entry point, runtime image, arguments, replica count and resource requirements.

Multiple roles can represent a heterogeneous application. For example, a coordinator, several workers and a separate data-loading role can form one submitted job.

Resources describe CPU, GPU and memory requirements. Scheduler adapters translate the job into execution on backends such as local processes, Docker, Kubernetes and Slurm.

The `Runner` supports submitting a job and subsequently querying status, waiting, retrieving logs and requesting cancellation.

This is closer to general job handling than `torchrun`.

TorchX also supports reusable components written as Python functions and extensible scheduler integrations. Its application code does not require TorchX at runtime.

The key limitation is that TorchX is primarily a job definition, launch and lifecycle abstraction. It is not a complete durable workflow engine, and it delegates important scheduling and resource guarantees to the chosen backend.

For example, TorchX's local scheduler does not enforce all resource specifications as hard hardware quotas. Its Kubernetes support also does not automatically provide every advanced scheduling facility, such as gang scheduling or priority admission.

TorchX is especially relevant when the same Python computation needs to launch in several infrastructure environments, or when a coordinated job contains several different worker roles.

Sources: `https://meta-pytorch.org/torchx/main/basics.html` and `https://meta-pytorch.org/torchx/main/index.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://meta-pytorch.org\&sz=32)

PyTorch/TorchX main documentation+1



### 9.3 Monarch: distributed actors and structured GPU coordination

Monarch is another separate PyTorch ecosystem project, distributed as `torchmonarch`.

Its main abstraction is a distributed actor system. Actors run in processes organized into meshes and communicate through message-based endpoints.

Unlike a conventional distributed-training API, actors can have different behaviors and responsibilities. A training actor, model-evaluation actor and data-generation actor do not have to execute the same operation.

Important capabilities include remote actors, broadcast messaging to process meshes, asynchronous invocation, distributed tensors, supervision trees for failure handling and RDMA-based transfers.

Monarch also has a `monarch.job` API for obtaining host resources from backends including local execution and Slurm. A job specification can request separately named meshes for different roles.

For example, one resource specification may request hosts for trainers and another for data loaders, with both represented in the resulting job state.

This is meaningful job-resource management, not merely a collection of process-spawning functions.

Monarch's most distinctive capability is combining heterogeneous distributed roles with PyTorch-native computational and tensor communication mechanisms.

However, its GPU-sharing documentation makes an important limitation explicit: the actor API does not itself reserve GPUs for processes. Device visibility and placement must be established through process configuration or an underlying resource manager.

Nor does an actor mesh automatically supply a durable business-task queue, arbitrary workflow history or all the service deployment functions of a model-serving platform.

Monarch is therefore most compelling when the complexity lies in coordinating distributed computational components, particularly components that need close interaction and efficient tensor transfer.

Sources: `https://meta-pytorch.org/monarch/stable/`, `https://meta-pytorch.org/monarch/stable/api/monarch.job.html` and `https://meta-pytorch.org/monarch/stable/generated/examples/gpu_sharing.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://meta-pytorch.org\&sz=32)

Monarch v0.7.0 documentation+2



### 9.4 Ray Core: heterogeneous tasks and stateful workers

Ray is a general-purpose distributed execution framework for Python.

Its two most relevant abstractions are remote tasks and actors.

A remote task executes an independent function. An actor is a stateful worker process that remains alive between method calls.

This distinction is particularly valuable for PyTorch workloads.

A remote task can execute a self-contained CPU preprocessing job, while an actor can load a model once and serve many subsequent GPU requests.

Ray provides resource declarations for CPU, GPU and custom logical resources, plus task placement, process isolation, object references, distributed scheduling, failure-handling controls and named actor mechanisms.

Actors can be given different resource allocations and lifecycles. The same Python codebase can define many types of actors and tasks, including non-PyTorch services.

Ray also provides actor-level concurrency controls and placement groups for coordinated resource reservation.

The central advantage is that heterogeneous job dispatch, stateful model workers and resource-aware scheduling share one distributed programming model.

Its limitations are equally important. Ray's resource declarations are primarily scheduling controls, not hard physical memory partitions. Stateful actors also require deliberate recovery and restart policies; an actor's process memory is not inherently durable.

Sources: `https://docs.ray.io/en/latest/ray-core/actors.html` and `https://docs.ray.io/en/latest/ray-core/scheduling/resources.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.ray.io\&sz=32)

Ray 2.60.0+1



#### Related Ray capabilities

Ray's companion modules are important because they handle distinct workload families without requiring separate execution ecosystems.

| Package or feature | Capability                                                     |
| ------------------ | -------------------------------------------------------------- |
| Ray Core tasks     | Parallel and distributed function execution                    |
| Ray Core actors    | Long-lived stateful workers and model instances                |
| Ray Jobs API       | Submit applications remotely to a cluster                      |
| Ray Data           | Distributed data transformation, ingestion and batch inference |
| Ray Train          | Distributed training, including PyTorch integration            |
| Ray Tune           | Hyperparameter search, trial scheduling and early stopping     |
| Ray Serve          | Deployment, scaling and routing of online inference services   |

Ray Tune, for example, solves a more specialized scheduling problem: it coordinates many model-training trials and can allocate resources between competing experiments.

Ray Serve addresses another problem: deploying independently scaled model endpoints and composing services through deployment handles.

Ray Core plus Ray Serve is one of the most direct combinations for a Python system with multiple different computational services.

Ray Jobs can additionally submit whole applications to the cluster, but should not be confused with Ray Core's individual remote tasks.

Sources: `https://docs.ray.io/en/latest/cluster/running-applications/job-submission/index.html`, `https://docs.ray.io/en/latest/serve/model_composition.html` and `https://docs.ray.io/en/latest/train/getting-started-pytorch.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.ray.io\&sz=32)

Ray 2.60.0+2



### 9.5 Ray Serve: multiple independently scalable inference services

Ray Serve extends the actor model into an application-serving runtime.

A Serve application can contain multiple deployments, and each deployment can have its own code, replica count, resource requirements and scaling behavior.

Deployments can call one another using handles rather than requiring all model execution to run inside a single application process.

Ray Serve also supports multiple applications in a cluster, which is useful when endpoints have different release or operational lifecycles.

This makes the following general arrangement possible:

Request entry / service routing

HTTP endpoints and application composition

Preprocessing

CPU replicas

Embedding

GPU replicas

Classification

GPU replicas

Each deployment can have a separate replica count, model instance and resource allocation.

This is a conceptual arrangement, not a claim that every deployment has automatic hardware isolation. GPU placement still follows Ray's resource model, and independently deployed model replicas may compete for memory if they share an accelerator.

The particularly useful distinction is between one service hosting several models and several independently scalable services. Ray Serve supports the latter while also allowing composed pipelines.

Sources: `https://docs.ray.io/en/latest/serve/multi-app.html` and `https://docs.ray.io/en/latest/serve/model_composition.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.ray.io\&sz=32)

Ray 2.60.0+1



### 9.6 Celery: independently routed background jobs

Celery is a strong fit when workloads are best represented as independent tasks submitted to queues.

It uses brokers such as RabbitMQ or Redis to distribute tasks to workers.

Tasks can be routed by type or name. Workers can subscribe to different queues, allowing heterogeneous services to execute separate categories of work from a common Python application.

For instance, image processing, data extraction, CPU-intensive transformations and GPU inference can have separately configured worker pools.

Celery supports retries, worker concurrency, scheduling facilities, result backends and queue-specific behavior.

It does not natively understand the CUDA device's memory capacity or reserve model-specific VRAM.

A GPU worker queue can limit concurrency to avoid oversubscription, but this is an application-level policy rather than PyTorch-aware resource isolation.

Delivery and acknowledgement semantics also matter: task execution may be repeated after failures, so side-effecting operations should be designed for idempotence where retries are enabled.

Celery is a comparatively direct solution for background task execution when distributed tensor communication or complex GPU-resource scheduling is unnecessary.

Source: `https://docs.celeryq.dev/en/stable/userguide/routing.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.celeryq.dev\&sz=32)

Celery 5.7.0 documentation



### 9.7 Temporal: durable execution across many services

Temporal solves a different and complementary problem: reliably advancing a multi-step workflow over time.

Its Python SDK provides workflow definitions, activities, workers, task queues, retry policies, timers and execution histories.

Unlike a simple remote function invocation, a Temporal workflow can survive worker interruption and resume from recorded durable state.

For a workflow that invokes several separate computational services, this can be more important than the numerical performance of any one task.

Temporal does not itself partition GPU resources or accelerate PyTorch tensor computation. An activity worker executing a GPU task still needs appropriate resource allocation and process management.

A Temporal workflow could coordinate work dispatched to Ray, an HTTP inference service or another execution system, but that integration must be implemented explicitly.

Its strongest use case is reliable orchestration of long-running, failure-sensitive sequences, not low-level GPU scheduling.

Source: `https://docs.temporal.io/develop/python`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.temporal.io\&sz=32)

Temporal Documentation



### 9.8 Prefect and Dagster: structured data and ML pipelines

Prefect and Dagster are relevant when the primary requirement is coordinating data processing, model training, evaluation and recurring pipeline execution.

Prefect centers on flows, tasks, deployments, work pools and scheduling.

Dagster centers on assets, jobs, schedules, sensors and the relationships between data-producing operations.

These frameworks can orchestrate PyTorch workloads while delegating actual execution to local workers, process infrastructure, containers or cloud environments.

They are particularly valuable when dependencies, schedules, materialization history and pipeline observability matter more than low-latency request routing.

They are less direct alternatives to an actor system for managing many long-lived, interactive model instances.

Dagster documentation: `https://docs.dagster.io/`. Prefect documentation: `https://docs.prefect.io/`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 9.9 BentoML: model-serving application development

BentoML is oriented toward building and deploying model-backed services.

Its service abstraction supports class-based model endpoints, resource declarations, lifecycle management and deployment packaging.

It also provides model composition, adaptive batching, distributed services and asynchronous task facilities.

This combination is useful when the main concern is turning multiple Python model implementations into operational APIs rather than coordinating arbitrary numerical computation.

A notable distinction from Ray Core is the starting abstraction: BentoML begins with services and their deployment requirements, whereas Ray Core begins with tasks, actors and resource scheduling.

BentoML documentation: `https://docs.bentoml.com/en/latest/build-with-bentoml/services.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.bentoml.com\&sz=32)

BentoML



### 9.10 NVIDIA Triton Inference Server: scheduling across models

NVIDIA Triton Inference Server is especially relevant to GPU-heavy multi-model inference.

It supports model loading and management, multiple inference backends, model-instance configuration, dynamic batching and request scheduling.

One easily overlooked capability is its cross-model rate limiter.

Unlike ordinary per-model request queues, Triton's rate limiter can coordinate execution across loaded model instances and apply priorities and resource constraints.

This can be useful when simultaneously executing several models would overload available resources or produce out-of-memory failures.

Triton is therefore a specialized option for a particular problem: efficiently managing requests across resident inference models.

It does not substitute for a general workflow engine responsible for arbitrary Python tasks, external service calls and persistent business-process state.

Sources: `https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/rate_limiter.html` and `https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/batcher.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.nvidia.com\&sz=32)

NVIDIA Triton Inference Server+1



### 9.11 TorchServe: historically relevant, but no longer actively maintained

TorchServe was built specifically to expose PyTorch models as inference services.

It includes multi-model serving, worker management, model-loading behavior and HTTP inference APIs.

However, its official documentation states that the project is no longer actively maintained and that no updates, bug fixes, new features or security patches are planned.

Consequently, while TorchServe remains important when understanding existing PyTorch infrastructure, it should not be presented as a maintained peer to current inference-serving frameworks.

Source: `https://docs.pytorch.org/serve/index.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch/Serve master documentation



## 10. Architectural patterns for heterogeneous workloads

The following patterns illustrate how these capabilities compose without assuming any particular application architecture.

### 10.1 Independent CPU and GPU jobs

A workload may consist of unrelated tasks: some use ordinary Python and CPU resources, while others use PyTorch models on GPUs.

Ray Core can express these as remote tasks or stateful actors with separate resource declarations.

Celery can instead express them as messages routed to distinct queues and worker pools.

The key distinction is whether the system benefits more from Ray's resource-aware distributed execution and actor model, or from broker-backed task delivery.

### 10.2 Many small requests to one expensive GPU model

Loading a model for every task is often expensive.

A long-lived model actor or inference-service replica can retain weights in GPU memory and process successive requests.

Batching may further improve throughput by combining compatible inputs before executing the model.

Ray Serve, BentoML and Triton each provide ways to implement this pattern, with different deployment and scheduling facilities.

### 10.3 Several unrelated models on one accelerator

This pattern involves a different optimization problem.

Even if requests are individually small, concurrent resident models may exhaust memory.

The main choices are maintaining several models in one controlled process, running separate model processes with admission control, or using a dedicated serving framework that schedules model instances.

Triton's cross-model rate limiter is relevant here. Ray actors and Monarch actors provide flexible execution models, but their applications still need a policy governing resident models, request concurrency and memory pressure.

### 10.4 One job spanning many accelerators

A single training job that needs eight GPUs is not the same kind of workload as eight independent one-GPU jobs.

For the former, PyTorch distributed primitives, DDP, FSDP2, tensor parallelism and pipeline parallelism provide the computational coordination.

TorchX can launch the job onto a scheduler. TorchElastic can manage the participating worker group.

Monarch is another option when execution includes several distinct coordinated actor roles rather than one uniform training worker program.

### 10.5 Multi-stage durable workflows

Consider a workflow that performs data ingestion, GPU extraction, validation, model inference and results publication.

The stages may run in different services and fail independently.

Temporal, Dagster or Prefect can express the relationships and lifecycle of that workflow.

The individual GPU stages can still use ordinary PyTorch, Ray workers, TorchX-launched jobs or dedicated inference services.

This separation avoids forcing a numerical library to represent business-level execution state.

### 10.6 A small illustrative Ray example

The following unexecuted example demonstrates how the same Python application can define a CPU task and a separate stateful GPU service without putting both workloads into one process.

```
import rayimport torchray.init()@ray.remote(num_cpus=1)def preprocess(values: list[float]) -> torch.Tensor:    return torch.tensor(values, dtype=torch.float32).reshape(1, 8)@ray.remote(num_cpus=1, num_gpus=1)class InferenceWorker:    def __init__(self):        self.model = torch.nn.Linear(8, 4).cuda().eval()    @torch.inference_mode()    def predict(self, batch: torch.Tensor) -> torch.Tensor:        result = self.model(batch.cuda())        return result.cpu()worker = InferenceWorker.remote()batch_ref = preprocess.remote([1.0] * 8)prediction_ref = worker.predict.remote(batch_ref)prediction = ray.get(prediction_ref)
```

The important features are not the example's simple model. They are the independent execution lifecycles, resource declarations and persistent model worker.

Additional classes can define different services with different allocations. Ray's scheduler decides when their resource requests can be satisfied.

The example does not provide durable workflow state or physically partition GPU memory; those remain distinct concerns.

## 11. Operational capabilities and important limits

### 11.1 Profiling and observability

`torch.profiler` captures CPU and accelerator activities, operator timing, memory-related information and execution traces.

This is valuable for understanding whether performance limitations arise from Python overhead, host-to-device transfers, synchronization, particular operators or GPU kernels.

PyTorch also exposes CUDA memory statistics and snapshots, structured logging controls, distributed diagnostics and monitoring facilities.

These mechanisms are complementary to an orchestration system's telemetry.

The orchestrator may report that a job waited for a GPU or failed three times. PyTorch's profiler can explain what happened inside the computation once execution began.

Source: `https://docs.pytorch.org/docs/2.15/profiler.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.14 documentation



### 11.2 Serialization, state and security

`torch.save` and `torch.load` provide model and tensor-state serialization.

The distinction between a model's state and an executable application is important. Saving a state dictionary does not save service definitions, process lifecycles, queue positions or deployment configuration.

Modern PyTorch defaults toward restricted `weights_only` loading, but this should not be treated as making arbitrary untrusted model artifacts risk-free.

`torch.export`, ONNX and ahead-of-time compilation represent separate deployment paths with different guarantees.

Likewise, PyTorch distributed checkpointing has different semantics from an ordinary single-process state dictionary.

Source: `https://docs.pytorch.org/docs/2.15/generated/torch.load.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation



### 11.3 Determinism and numerical precision

GPU acceleration, compiler transformations, mixed precision and distributed execution can change numerical behavior.

Even mathematically equivalent operations may differ at floating-point precision because of reduction order, selected kernels or execution strategy.

PyTorch offers deterministic-algorithm controls and random-number-generator management, but reproducibility still depends on the operators, platforms and execution environment.

This matters when the same computation is run by several services, on different devices or with different compilation settings.

Source: `https://docs.pytorch.org/docs/2.15/notes/randomness.html`.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.pytorch.org\&sz=32)

PyTorch 2.15 documentation



### 11.4 Hardware availability is build-dependent

PyTorch supports multiple device families, including CPU, CUDA, ROCm, Apple MPS and Intel XPU configurations.

Availability of a particular dtype, operator, compiler feature or kernel is not universal across devices.

Low-precision operations, sparse kernels, accelerator graphs and custom kernels are especially sensitive to platform support.

The current stable release should therefore be distinguished from a specific installed wheel, which may expose a different combination of accelerator functionality.

### 11.5 Companion packages are separate from `torch`

Several significant extensions belong to the broader PyTorch ecosystem rather than the core Python package.

| Companion library | Relevant specialization                                             |
| ----------------- | ------------------------------------------------------------------- |
| `torchvision`     | Computer-vision data, models and transformations                    |
| `torchaudio`      | Audio processing and related model workflows                        |
| `torchao`         | Quantization, low-precision execution and model optimization        |
| `torchrec`        | Large-scale recommendation-model infrastructure                     |
| `torchtitan`      | Large-model training recipes and distributed training integrations  |
| `torchrl`         | Reinforcement-learning components and training infrastructure       |
| `torchdata`       | Data-loading ecosystem utilities, subject to its evolving API scope |
| `executorch`      | Deployment on mobile and embedded or edge devices                   |
| `torchmonarch`    | Distributed actor-based execution                                   |
| `torchx`          | Job specification, launch and lifecycle management                  |

This distinction prevents attributing companion-package functionality to an ordinary `import torch` installation.

## 12. Capability-based selection guide

For the specific requirement of executing multiple kinds of work from one Python codebase, the most useful dividing line is what constitutes a job and who must own its lifecycle.

| Workload shape                                                            | Most directly relevant capabilities                     |
| ------------------------------------------------------------------------- | ------------------------------------------------------- |
| Many similar tensor operations                                            | Native PyTorch batching, `torch.func.vmap`, compilation |
| Independent local processes with limited coordination                     | `torch.multiprocessing`                                 |
| One distributed training job                                              | DDP, FSDP2, DTensor, pipeline parallelism, TorchElastic |
| Launch heterogeneous application roles on multiple backends               | TorchX                                                  |
| Coordinate heterogeneous actors with close distributed tensor interaction | Monarch                                                 |
| Schedule mixed Python/CPU/GPU jobs with long-lived stateful workers       | Ray Core                                                |
| Expose multiple independently scalable model services                     | Ray Serve or BentoML                                    |
| Schedule inference requests among many resident models                    | NVIDIA Triton Inference Server                          |
| Route independent background tasks through persistent queues              | Celery                                                  |
| Ensure multi-service workflows resume correctly after interruption        | Temporal                                                |
| Schedule recurring data and ML pipelines with explicit dependencies       | Dagster or Prefect                                      |
| Coordinate cluster-level resource admission and container lifecycle       | Kubernetes, Slurm or other external resource managers   |

### The most consequential distinctions

Ray versus Monarch: Both support stateful distributed computation. Ray offers a broader general-purpose task, scheduling, data, training and serving ecosystem. Monarch emphasizes PyTorch-oriented actor meshes, structured process supervision and distributed tensor communication. Monarch's job-allocation API is relevant, but it does not make its execution model identical to Ray's.

TorchX versus Ray: TorchX standardizes how jobs are defined and launched on external schedulers. Ray provides an active distributed execution runtime with remote tasks, actors, object management and logical resource scheduling. They solve adjacent, rather than identical, problems.

Ray Serve versus Triton: Ray Serve emphasizes Python service composition, deployment and independent scaling. Triton emphasizes high-performance inference execution, batching, model instances and cross-model request scheduling.

Celery versus Temporal: Celery primarily routes executable tasks to workers. Temporal primarily persists and advances the state of workflows that invoke activities. Both can participate in a heterogeneous system, but their recovery models and abstractions are different.

PyTorch versus all of them: PyTorch remains responsible for the mathematical computation and model execution. Orchestration technologies control when, where and under what lifecycle policies those computations run.

## Conclusion

PyTorch is a comprehensive numerical and machine-learning execution framework, with important capabilities extending far beyond ordinary model training: functional differentiation, vectorization, sparse and irregular tensors, compiler transformations, custom operator registration, heterogeneous device execution, distributed tensor computation and fault-tolerant distributed training.

For multiple independent jobs across a variety of services within the same Python codebase, its own multiprocessing, CUDA-stream and distributed-execution facilities are useful but incomplete.

The closest additional libraries are:

TorchX when the main requirement is defining and launching heterogeneous jobs across execution environments; Monarch when the main requirement is coordinating heterogeneous distributed PyTorch actors; and Ray Core, potentially combined with Ray Serve, when the main requirement is scheduling and operating a mixture of independent Python computations and long-lived GPU-backed services.

Celery, Temporal, BentoML and Triton then address more specialized requirements around task delivery, durability and inference serving.

The general architectural opportunity is to use PyTorch as the computation engine while assigning job lifecycle, resource management and service execution to a runtime explicitly designed for those responsibilities.