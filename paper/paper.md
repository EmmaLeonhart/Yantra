# Yantra: A Neuro-Symbolic, GPU-Native Operating System for Critical Systems

## Abstract

Conventional operating systems treat the CPU as the brain and the GPU as an accelerator, and treat AI as something bolted on through serialization layers (text, JSON, tool-call schemas). For workloads where both **predictable latency under load** and **first-class local AI** matter — defense, aerospace, industrial control, medical devices, autonomous systems — neither inversion is paid for, but both costs are felt: GPU-resident models thrash against CPU-resident schedulers, and every round trip through the OS/AI boundary costs an embed/decode pair that drops information and adds jitter.

**Yantra** is an operating system written in [Sutra](https://github.com/Emma-Leonhart/Sutra) (a typed functional language whose compiled forward pass is a PyTorch neural network) in which the kernel, processes, IPC, and GUI are all the same artifact: a single differentiable tensor-op graph executing on the GPU. The CPU is reduced to an orchestrator that boots the system, manages a cold-store of suspended processes in RAM, and arbitrates GPU admission. Userspace processes are Sutra programs of type `(Axon) -> Axon`, where an *axon* is a fixed-width vector produced by rotation binding over a codebook of role-fillers. IPC is axon-passing; capabilities are the rotation operators themselves — possessing the operator is the only way to read or write a slot, so revocation is operator rotation.

Three structural properties fall out of this design. (1) **Predictable performance under load**: every admitted process declares its compute and synthetic-dimension footprint at install time; the runtime guarantees those allocations until exit, so adding processes either fits cleanly or fails admission — never degrades what is already running. (2) **A verification-friendly surface**: the non-AI parts of the system reduce to a fused tensor-op graph, polynomial Kleene logic, and tail-recursive loops with soft-halt RNN cells; equivalence checking is algebra rather than control-flow traversal, and termination obligations reduce to monotonicity of a halt scalar. AI parts are explicitly *not* claimed verifiable — they are quarantined behind axon-typed contracts, provenance roles, and runtime monitors. (3) **AI-native by construction**: every process already takes an axon and returns an axon, so a local model's residual activations, a JEPA's predicted latents, and a `read_file()` syscall result are all the same kind of tensor, with no translation layer.

This paper is a position paper, not an empirical paper. It describes a planning corpus — the architecture, axon model, lifecycle, security argument, verification story, target-market analysis, and roadmap have been worked out across sixteen design documents in this repository — and articulates the claims those documents commit to, so that the design can be reviewed before implementation begins. The Sutra compiler and the C and JS/TS transpilers that Yantra depends on are tracked as separate projects; Yantra itself is currently a planning artifact targeting a forthcoming Sutra-native implementation.

## 1. Introduction

The dominant computing paradigms were fitted around scarce serial compute and disembodied language models. Two facts about the current substrate make that fit increasingly poor.

**GPUs are the default.** Critical-systems vendors increasingly ship accelerator-heavy boxes anyway — for radar processing, sensor fusion, vision, planning, ML inference. A connectionist operating system is not chasing exotic hardware; it is using what is already there more honestly.

**AI is everywhere but feels bolted on.** RAG, MCP, function calling, agent scaffolding, tool-use frameworks — these are all plumbing around the same hole. Models think in vectors; software speaks in bytes. Every loop iteration through that plumbing is an opportunity to drop information, mistranslate intent, hallucinate a response, or stall. The phrase "the model uses the computer" hides a long chain of `model activation → text → parse → execute → output → re-embed → model activation`.

Yantra collapses that loop into `model activation → Sutra program → tensor output → directly consumable`. Because every Sutra program already lives in the same embedding space the model is thinking in, perception (e.g. JEPA), reasoning (LLM activations), and action (Sutra tensor ops) become first-class operations on the same representation. There is no translation layer because there is nothing to translate to.

Yantra is **not** an LLM with tool use; it is the substrate beneath that. It is **not** a consumer desktop replacement; users who want 100 Chrome tabs and arbitrary side-loaded software are not the customer. It is **not** "von Neumann with a GPU instead of a CPU"; the GPU is doing connectionist work, not pretending to be a CPU. And it is **not** a video-generation world model of a computer — see §7 for the contrast with Meta's *Neural Computers* paper, which inspired the framing but went the opposite direction.

### 1.1 Contributions of this paper

This paper does not report an implementation. It contributes:

1. **A coherent system design** that takes "the symbol *is* the computation" seriously down to the kernel, articulated across sixteen planning documents this paper synthesises.
2. **A capability model based on rotation operators**: roles are not labels but the rotations that produce axon slots; possessing the operator *is* the capability. Revocation is operator rotation. Sandboxing is handing a child a derived sub-codebook.
3. **A verification story honest about what it covers**: the non-AI parts reduce to a small set of polynomial obligations over a known tensor graph; the AI parts are explicitly *not* in scope for formal verification but are bounded behind contracts.
4. **A target-market argument** that explains why critical systems are the right first market, not consumer desktops — the same properties (no `eval`, no service workers, no AOT-vs-runtime divergence, fixed allocations, small syscall surface) that look like compatibility losses to a desktop user are procurement criteria to defense and aerospace.

## 2. The thesis

The thesis Yantra commits to is that **a GPU-resident, embedding-typed process model is a better fit for the critical-systems workload than a CPU-resident, byte-typed one, once local AI is part of the stack**. This rests on three structural inversions of conventional OS design.

**CPU is the brain → CPU is the orchestrator.** The CPU loads the bootloader, kicks off the GPU runtime, and shuffles inactive processes to and from RAM. It does no application work. It is closer in role to a CUDA host than to a conventional kernel.

**Programs use the OS to talk to AI → AI talks via the OS.** The OS doesn't expose an "AI API" on top of a conventional process model. The process model itself is embedding-shaped: every process is something that takes an axon and returns an axon. AI integration is what you get for free; it is not a feature that was added.

**File system is internal → File system is the legible surface.** The compute is opaque (matrix soup, by design). The file system is the part that has to remain readable by humans and forensics — so the FS stays conventional (ext4/btrfs/zfs), and the boundary between "compute world" and "storage world" is a small, well-defined set of syscalls that read and write axons from files.

## 3. Architecture

The system is a layer cake whose top six layers all execute on the GPU as a single differentiable tensor-op graph, with the bottom two layers running on a small conventional CPU/RAM/storage tier.

```
+----------------------------------------------------------+
|  GUI layer (everything-is-a-browser)                      |
|  HTML5 + CSS + AOT-compiled JS/TS + WebGL                 |
+----------------------------------------------------------+
|  Userspace processes — Sutra programs (Axon) -> Axon      |
+----------------------------------------------------------+
|  Kernel services — process table, axon router, FS bridge, |
|  display server, input router, network stack              |
+----------------------------------------------------------+
|  Sutra runtime — tensor-op graph executor, GPU memory     |
|  arenas, soft-halt RNN cells driving tail-recursive loops |
+----------------------------------------------------------+
|  Init + resource manager (small CPU program)              |
+----------------------------------------------------------+
|  CPU + RAM + storage (conventional)                       |
+----------------------------------------------------------+
```

### 3.1 The axon model

The Sutra-language axon spec is authoritative; Yantra inherits it. An axon is a fixed-width vector produced by *rotation binding* over a codebook of roles:

$$ a = \mathrm{bundle}\left(\mathrm{bind}(R_{subject}, F_{alice}),\; \mathrm{bind}(R_{action}, F_{send}),\; \ldots\right) $$

`bind` is multiplication by a Haar-orthogonal rotation matrix $R_{role}$ keyed to the role's identity; `bundle` is superposition (sum + normalise); `unbind` is multiplication by $R_{role}^{-1} = R_{role}^{\top}$. Rotation binding is the chosen primitive because, on frozen LLM-scale embedding substrates measured in the Sutra paper, it decodes bundles at 100% accuracy through widths where Hadamard-product binding has already collapsed (2.5% at width 8 on `mxbai-embed-large`).

In Yantra specifically, the axon spec is tightened in two ways. **Fixed width is mandatory, not optional** — the axon width per process goes in the install manifest, because the runtime cannot schedule GPU allocation without it. **Crosstalk depth caps surface as runtime errors, not silent degradation** — a process that would exceed its bundle-depth budget gets a clean rejection rather than garbled output.

### 3.2 IPC and the syscall surface

IPC is axon-passing. The kernel maintains a process table and an axon router; processes hand axons to roles, the router delivers them. The filesystem bridge is the single largest external surface and is the place the design earns its keep:

```
read_file  : { R_path } -> { R_bytes_axon, R_metadata_axon }
write_file : { R_path, R_payload_axon } -> { R_status }
```

`R_bytes_axon` carries the file's contents in one of two modes — a literal embedding produced by an embedding model (when the file is meant to be consumed *semantically*, e.g. by a search process), or a Sutra-compiled axon that decodes losslessly to bytes (when the file is meant to be consumed *exactly*, e.g. executables, configs, binary blobs). The mode is part of the file's metadata, not the syscall's job. The conventional filesystem and the embedding-typed kernel meet at exactly this boundary.

### 3.3 Capability transfer via rotation operators

In the Sutra spec, roles are not labels but *operators*: the rotation $R_{role}$ is the only way to read or write the corresponding slot. Yantra turns that property into a security mechanism with three useful consequences.

**Process isolation.** A process is bound to a set of roles. Roles it does not possess decode any axon's slot to noise, by construction. There is no permission table to consult; the inability is geometric.

**Sandboxing.** Handing a child process a smaller codebook (or a derived child codebook) restricts it to that subset. The child cannot synthesise the parent's operators because it has never seen them.

**Revocation.** Rotating the parent operator invalidates all derived copies. Existing axons in flight that carry the revoked role become unreadable in that slot. This is much cleaner than capability-table mutation in a conventional capability OS.

The full threat model and crosstalk analysis live in `planning/08-security-and-isolation.md`.

### 3.4 Fixed allocations and admission control

Each process declares its compute and synthetic-dimension footprint at install time. The runtime guarantees those allocations until the process exits. The resource manager (a small CPU-side program) keeps a table of active GPU-resident processes and a cold-store of suspended ones in RAM, and decides which to evict and which to resume — but it does *not* schedule. The GPU runs everything that fits, simultaneously. New launches that don't fit fail admission; nothing already running degrades.

This is the property critical-systems customers actually need. Conventional OSes trade predictability for flexibility — they are brilliant at running 100 Chrome tabs and a video call simultaneously, and mediocre at guaranteeing that a control loop's deadline is met when something else on the box gets busy. Yantra inverts the trade.

## 4. Verification

A blunt division of the system: the **non-AI parts** (kernel, init, FS bridge, capability check, resource manager, browser engine, transpiler outputs of finite programs) are formally verifiable in principle. The **AI parts** (any embedding-model invocation, any process whose semantics depend on a learned weight matrix) are not, and we should not pretend otherwise. They get bounded behavior guarantees, capability discipline, provenance roles, and runtime monitoring instead.

### 4.1 What makes the non-AI side easy to verify

Three Sutra design choices combine to make this work:

1. **Beta reduction to tensor normal form.** Sutra programs reduce to a canonical, fused tensor-op graph. Two programs that are semantically equivalent reduce to the same graph (modulo trivial differences). Equivalence checking is algebra, not control-flow traversal.

2. **Polynomial Kleene logic for branches.** What looks like `if/else` in source is, after reduction, a polynomial that smoothly interpolates between the branches based on a fuzzy truth value. The Kleene connectives are Lagrange-interpolated polynomials exact on the $\{-1, 0, +1\}$ truth grid and $C^{\infty}$ elsewhere — closed-form expressions whose value range, sign, and derivatives are all symbolically tractable.

3. **Tail-recursive loops as soft-halt RNN cells.** Each loop is a bounded recurrence. The runtime's halt cell decides termination. Termination proofs reduce to "the halt signal is monotone within bounded steps."

Together these take "verify a kernel" from "navigate millions of lines of imperative C" to "discharge a finite set of polynomial obligations over a known tensor graph."

### 4.2 The DO-178C-shaped argument

For an aerospace certification audience the argument structure is:

- **Plan**: a fixed kernel image plus a fixed set of critical processes, manifests published, no runtime code loading.
- **Software requirements**: axon-typed contracts on every kernel role and critical process (input roles, output roles, status conditions).
- **Design**: Sutra source, whose tensor normal forms *are* the designs.
- **Verification artefacts**: mechanical proofs that the normal forms satisfy the contracts; polynomial-logic obligations discharged by an SMT solver or similar.
- **Trace**: every capability grant and every admit/evict from the resource manager, written to an append-only log.
- **Tooling assurance**: the Sutra compiler is in scope for qualification; its output (normal form) is the artefact under review, not the source.

This is the *shape* of a real certification effort. We are not shipping a certified Yantra v1; we are shipping an architecture that is friendly to certification when the time comes.

### 4.3 What we are not claiming

- Yantra is not a certified system out of the box. A certified configuration is per-customer, per-mission.
- Yantra is not formally verified end-to-end today. The architecture is verification-friendly. The proofs are an ongoing project, most of which has not started.
- Yantra does not make AI safe. It makes AI *quarantinable* — the unsafe parts are bounded, contracted, and monitored. That is not the same as safe.

## 5. AI-native by construction

A model running on Yantra is not bolted on top of a computer issuing string commands. Its outputs *are* axons that can be routed directly to the input role of any process that accepts that role; its inputs *are* axons coming from other processes. There is no text serialization layer between the model and the rest of the system.

Three consequences:

**Perception is a process.** A JEPA-style joint-embedding predictive model emits its predicted latents as axons. The application that consumes those latents is not "the AI" — it is just a process whose input role is a JEPA latent. The application can be a Sutra program written by hand, a transpiled JS dashboard, or another model. They all see the same shape.

**Local AI is everywhere by default.** A file manager doing semantic search asks the FS bridge for files in `semantic` mode and runs cosine similarity. A terminal suggesting commands runs a small local model over shell-history axons. A monitoring dashboard runs an embedding-distance check against a baseline. None of these need a special "AI API"; they just consume axons.

**The alignment pacemaker.** A specific design pattern that drops out of this: a small alignment monitor sits between AI processes and any user-visible output, watching for known failure modes. Because every axon carries provenance roles, the monitor can refuse to forward an axon whose provenance does not match the kind of decision that is downstream. This is a *runtime* mechanism, not a formal one; it complements the verification story rather than replacing it.

## 6. Target markets

The customer in one sentence: *an organization that runs critical software, can't tolerate performance jitter, has to pass a certification audit, increasingly wants local AI as part of the stack, and is paranoid about its attack surface.*

That excludes consumer desktops on purpose. It includes defense (mission systems, sensor fusion, command-and-control), aerospace (avionics, ground stations, DO-178C-shaped work), industrial control (robotics, factory automation, process control), medical devices (imaging, surgical assistants, embedded diagnostics), and autonomous systems (drones, ground vehicles, marine, field robotics).

The three structural properties from §1 map onto three pain points these customers have:

| Property | Pain point addressed |
|---|---|
| Predictable performance under load | Jitter under contention on conventional OSes |
| Small verifiable trusted base | Multi-year, multi-million-dollar certification cost |
| No `eval`, no service workers, AOT-only, small syscall surface | Procurement security in eventually-adversarial environments |

The "it can't run your existing software" line is normally a deal-breaker; in this market it is the same sentence as "it can't run your existing malware." The incompatibility is the feature.

### 6.1 The ChromeOS comparison

Customers will reflexively compare Yantra to ChromeOS because the GUI is "everything is a browser." The comparison is the punchline of the pitch — same surface area, opposite engineering everywhere underneath:

|  | ChromeOS | Yantra |
|---|---|---|
| Surface area | Browser-only userspace | Browser-only userspace |
| Why | Cheapest possible thin client | Best possible critical-systems endpoint |
| Local AI | Cloud-dependent | Native, first-class |
| Verifiability | None | Cleanly verifiable kernel + critical processes |
| Hardware target | Chromebooks (cheap) | High-end GPU (or analog substrate later) — expensive |
| Position | Cheapest | Best |

"It looks like ChromeOS to your users. It is the opposite of ChromeOS in every way that matters underneath."

## 7. Related work

**Meta's *Neural Computers* (Schmidhuber et al., 2026, arXiv:2604.06425).** A 76-page position paper proposing a class of systems where computation, memory, and I/O are unified inside a learned neural latent state, with video-diffusion-style prototypes (CLIGen, GUIWorld) that roll out plausible screen frames from prompts and user actions. Their own paper enumerates the failure modes: poor symbolic stability, weak long-horizon reasoning, no robust reuse of routines, behavior drift. **They are doing neural *simulation* of interfaces; Yantra is building neural *execution*.** The high-level ambition overlaps; the engineering posture is the opposite. The Meta paper validates the design space and demonstrates the failure modes of going "all the way neural" without compositionality.

**Differentiable Neural Computer / Neural Turing Machines (Graves et al., 2014/2016).** Same family of ambitions: a neural network with external addressable memory, end-to-end differentiable, in principle Turing-complete. The toy demonstrations worked (sorting, graph traversal, London Underground navigation). Scaling did not. The lesson for Yantra: *theoretical Turing-completeness is not the asset.* What matters is that the substrate is programmable *in practice* — a real language, a real compiler, real programs running reliably on real workloads. Yantra leans on this: it has a compiler (Sutra), transpilers (C, JS/TS), fixed allocations, and a verification story. The DNC had a beautiful idea and no ecosystem.

**Percepta — "Can LLMs Be Computers?"** A WASM interpreter implemented inside transformer weights, with 2D-restricted attention heads, parabolic-key memory addresses, and convex-hull memory lookup at O(log t). They run arbitrary C programs to completion in millions of inference steps. **This is the bottom-up version of the question Yantra answers top-down.** Their first Futamura projection (specialising the interpreter for a specific program, baking it into FFN weights) is essentially what the Sutra compiler does by default — beta reduction *is* partial evaluation. Their need for the convex-hull / parabolic-key trick exists because they're emulating memory addressing, a concept alien to tensor math. Yantra sidesteps it: there is no memory to address, because execution is pure function application compiled to matrix ops.

**Plan 9, Oberon, TempleOS.** The historical "different OS" projects worth respecting. Plan 9's "everything is a file" rhymes with Yantra's "everything is an axon"; the lesson is that elegance is not enough by itself — you need a market that values the elegance, and consumer desktops have never been that market. Oberon (Wirth) demonstrates that a system from kernel to GUI written in one language with a small implementation is possible; Yantra is the same shape (Sutra all the way down) and should inherit the same discipline.

**Vector-symbolic architectures (VSA/HDC).** Plate, Kanerva, and the rest of the field. The intellectual ancestor of Sutra's binding/bundling primitives. Modern implementations (TorchHD, etc.) are good libraries; none of them is a programming language compiled to tensor normal form. Sutra is what happens when you take VSA seriously enough to build a typed functional language out of it.

**Neuro-symbolic frameworks (Scallop, DeepProbLog, Logic Tensor Networks).** Each pairs a neural component with a symbolic reasoner that talk via an explicit boundary. The Yantra position is that *the boundary is unnecessary*: symbolic and neural are not two systems that communicate, they are the same system viewed at different resolutions. A symbol is just an embedding that got very lucky about being unambiguous; a neural representation is a distribution over symbols.

**Differentiable programming (JAX, Julia/Zygote, PyTorch's `torch.compile`).** The mainstream cousin. Yantra goes further in two ways: the whole operating system is in the differentiable substrate (not just an application), and control flow is fuzzy by design via polynomial Kleene logic (not via differentiable approximations of discrete branches).

## 8. Status, roadmap, and what would falsify the design

### 8.1 Status

This repository is a **planning corpus**, not an implementation. The sixteen documents under `planning/` cover vision, architecture, axon model, process lifecycle, kernel/init, filesystem bridge, GUI stack, transpilers, security/isolation, verification, AI-native interface, debugging/observability, target markets, hardware roadmap, milestones, open questions, and related work. The Sutra compiler and runtime (which Yantra depends on) and the C and JS/TS transpilers live in adjacent projects. This paper is the entry-point synthesis of the planning corpus, written so the design can be reviewed before implementation begins.

### 8.2 Milestones to first useful prototype

In rough order of "must work" to "would be nice":

1. **Sutra runtime with fixed allocations** — multi-process Sutra runtime where every process declares its compute and synthetic-dimension footprint at install time, and the runtime guarantees those allocations until exit.
2. **Axon-based IPC** — a standard data model and protocol for passing axons between processes, with the rotation-operator capability check.
3. **Init + resource manager** — a small CPU program that loads the bootloader, kicks off the GPU runtime, and manages eviction/resume against the RAM cold-store.
4. **GUI** — HTML5 + CSS + AOT-compiled JS/TS + WebGL. JS/TS transpiles to Sutra ahead of time. No `eval`, no service workers, no continuous server-emitted JS.

### 8.3 What would falsify the design

A position paper is worth less if it can't be wrong. The claims that would cause us to retract or substantially revise:

- **Crosstalk-depth scaling.** If, for a representative critical-systems workload, the bundle-depth budget required to keep the IPC graph correct turns out to be too small to be useful (e.g. if a sensor-fusion process needs to bundle more roles than rotation binding can resolve cleanly on the embedding substrate), the axon model as Yantra commits to it is not viable. The Sutra paper measures this on a range of substrates; the Yantra-specific question is whether *real workloads* fit inside those measured budgets.
- **Compiler qualification cost.** If qualifying the Sutra compiler under DO-178C-style tooling rules turns out to cost more than qualifying a conventional toolchain, the verification-friendliness argument collapses. A self-hosted bootstrap with a verified microcompiler at the bottom is the candidate solution, but it is not built.
- **GPU admission-control granularity.** If the smallest unit a real GPU can pre-allocate compute against is much coarser than a Yantra process needs, the "fixed allocations, no degradation" property degrades to a software fiction over hardware sharing — at which point it is no different from conventional scheduler-with-priorities.
- **Embedding-model identity attestation.** A swappable embedding model is a trust hole. If we cannot ship a credible attestation story (signed model bundles, reproducible builds of the embedder, etc.), the FS bridge is unsafe in any setting that takes supply-chain attacks seriously. This is an open question, not a solved one.

### 8.4 What this paper does not commit to

Reviewer-relevant non-commitments, made explicit:

- **First lighthouse customer.** The market argument is generic to defense/aerospace/industrial. We do not commit to a specific first reference deployment.
- **Open-source vs. dual-license.** Default is "OS open, hardware/services closed"; specific subsystems (the certification toolchain especially) may dual-license.
- **Certification ordering.** FIPS 140-3, Common Criteria, DO-178C are all plausible; the order matters and we don't have it locked.
- **Per-tenant codebooks vs. one global codebook with namespaced roles.** Real partitioning question for multi-tenant deployments; the answer differs between defense/aerospace and a hypothetical consumer-grade Yantra.

## 9. Conclusion

A connectionist operating system makes sense when (a) the workload already runs on GPUs and the CPU is along for the ride, (b) local AI is part of the stack and the model wants to think continuously rather than emit strings, and (c) the customer values predictable latency under load and a small verifiable trusted base more than mass-market compatibility. Defense, aerospace, industrial control, medical, and autonomous systems all sit at that intersection.

Yantra is the operating system you get when you take "the symbol *is* the computation" seriously, all the way down to the kernel. The compute is opaque and embedding-typed; the file system is conventional and forensics-readable; the boundary between them is a small set of axon-typed syscalls. The CPU orchestrates. The GPU computes. Capabilities are rotation operators. Verification is polynomial algebra over tensor normal forms. AI is everywhere because there is no place where it would be second-class.

The implementation has not started. This paper is the design committing to the claims that the implementation will be measured against.

## Acknowledgements

Yantra builds on the Sutra language (separate project) and on a long line of vector-symbolic-architecture work (Plate, Kanerva, et al.). The Meta *Neural Computers* paper and the Percepta "Can LLMs Be Computers?" demonstration sharpened the framing by occupying adjacent but opposite positions in the design space. Critical-systems framing borrows from the DO-178C and Common Criteria practitioner literature.

## References

Full reference list is captured inline in the planning corpus under `planning/16-related-work.md`. Key entries:

- Meta + Schmidhuber et al., *Neural Computers*, arXiv:2604.06425 (2026).
- Graves et al., *Neural Turing Machines*, arXiv:1410.5401 (2014); *Differentiable Neural Computer*, *Nature* 538 (2016).
- Percepta, "Can LLMs Be Computers?" (perceptave.ai blog, 2025).
- Plate, *Holographic Reduced Representations* (1995); Kanerva, *Hyperdimensional Computing* (2009).
- Pike, Presotto, Dorward, Flandrena, Thompson, Trickey, Winterbottom, *Plan 9 from Bell Labs* (Bell Labs CS Tech Report, 1995).
- Wirth, *The Programming Language Oberon* (1988); Reiser & Wirth, *Programming in Oberon* (1992).
- DO-178C, *Software Considerations in Airborne Systems and Equipment Certification*, RTCA (2011).
- The Sutra paper (companion submission), describing the language, compiler, and the rotation-binding measurements Yantra's axon model depends on.
