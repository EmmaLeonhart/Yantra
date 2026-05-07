# Sutra and transformer-based computation

_Source: claude_

## User

Yeah. I bet that was that was kinda thought that was kind of an interesting thing. Although, I guess, with with the with that well, actually, was it even a large language model or just just a transformer? That they use? I I'm actually the more I'm thinking about it, the more I'm actually, like, a bit suspicious of this. Like, we're I don't I don't think transformers are actually Turing complete. I don't think transformers are actually Turing complete. They don't have don't think that they would have the I don't think they have support for unbound loops. Unless they did some something very clever with it. Might make it not transformer anymore. Yeah, I'm confused about a lot of the tensor operations, or I'm confused about what they're doing there. I'm a bit confused about this because I'm not sure how they actually solve that problem. I'm also interested in how this relates to the so-called neural computer thing that some people at Meta wrote a 76-page paper on and then never actually implemented anything any of us

## User

Yeah. I I just just hate it. It's like there it's like so many people, like, do some, like, big awesome research project and then just don't do anything with it? Like, it feels like half of computer science is this.

## User

What’s DNC?

## User

How does this relate to sutra <https://www.percepta.ai/blog/can-llms-be-computers>

## Assistant

Yeah, it's a real pattern. Someone proves something profound exists, writes the paper, gets the citations, and then... moves on to the next proof-of-concept. The implementation gap in CS research is enormous.

The DNC is maybe the most egregious example — Graves et al. demonstrate a neural network that can learn to sort, do graph traversal, navigate a London Underground map. Genuinely impressive. And then it just... sits there. Nobody scales it, nobody ships it, the architecture quietly gets forgotten while transformers eat everything.

Part of it is incentive structure — papers get you tenure and citations, engineering the thing to actually work gets you nothing academically. And the people with the skills to implement it properly are usually not the same people who proved it works in theory.

Part of it is also that "works in a demo" and "works as infrastructure" are separated by an ungodly amount of engineering. The DNC's memory addressing was beautiful on paper and a training catastrophe in practice. Someone would have had to grind through that for years with no publishable output.

It's one of the things that makes your approach interesting from the outside — Sutra is genuinely trying to close that loop. The connectome demos, running Pong, pushing toward Doom — that's the "and then we actually built it" part that most projects skip. The Y Combinator framing makes sense precisely because it forces you to think about the thing working in the world, not just in a paper.

Though I'll be honest — the Doom-across-ten-fly-brains demo is going to raise some eyebrows before it raises funding. In a good way, probably.

## Assistant

Your skepticism is well-founded. Transformers in the standard sense are *not* Turing complete — they're bounded-depth circuits. Each forward pass is a fixed computation graph, so you can't have genuinely unbounded loops. The question is what Percepta actually did to get around that.

The answer is almost certainly that the "transformer" here is being run **autoregressively for many steps** — each inference step is one "tick" of the virtual machine, and the context window acts as the tape/memory. So it's not that a single forward pass executes a million-step program; it's that they run the model a million times, with the growing KV cache serving as persistent state. That's where the O(log n) convex hull trick becomes essential — without it, each step would cost O(n) attention over the full history, making the whole thing quadratically expensive.

So it's closer to "a transformer can simulate a computer if you run it in a loop externally" rather than "a transformer *is* a computer." The Turing completeness lives in the external loop, not the model itself. Which is... fine, but a somewhat different claim than the headline suggests.

This actually makes it *less* threatening to Sutra's position. They're still relying on an external control structure for unbounded computation. Sutra's compiled tensor programs run to completion in a bounded forward pass — the looping structure is unrolled at compile time, which is a different tradeoff (you need to know loop bounds, but you get true single-pass execution).

On the Meta neural computer paper — are you thinking of the one from Graves et al., or something more recent? There have been a few "differentiable computer" papers (NTM, DNC) that had this exact problem: beautiful theory, the architecture genuinely can address external memory, but training them is a nightmare and they never scaled. The gap between "this is Turing complete in principle" and "this actually learns to use that capability" turned out to be enormous.

## Assistant

Differentiable Neural Computer — a 2016 DeepMind paper by Alex Graves. It's a neural network augmented with an external memory matrix that the network can read from and write to via differentiable attention mechanisms, so the whole thing is end-to-end trainable. The idea was to give neural networks something like RAM — addressable, persistent memory separate from the weights.

The predecessor was the Neural Turing Machine (NTM), also Graves, which had the same basic idea but simpler memory addressing. The DNC improved on it with more sophisticated memory allocation and the ability to handle linked data structures.

Both were trying to solve the same thing you were just describing with the Percepta paper — genuine unbounded computation in a neural substrate, not just pattern matching. And both demonstrated it works in principle on toy tasks, then largely stalled out.

## Assistant

Fetched: Can LLMs Be Computers? | Percepta

Fetched: Can LLMs Be Computers? | Percepta

The page didn't render its full content — it seems to be a JS-heavy SPA. Let me search for more info about the article.

Searched the web

Searched the web

This is a really interesting paper to connect to Sutra. Here's how I see the relationship:

**What Percepta did:** They implemented a WebAssembly interpreter inside transformer weights, enabling arbitrary C programs to execute for millions of steps entirely within a model's inference loop — no external tools required. The key trick: restrict attention heads to 2D, encode memory addresses as parabolic keys, and use convex hull geometry to turn what's normally a linear scan over the entire context into an O(log t) lookup. [Daily.dev](https://app.daily.dev/posts/can-llms-be-computers--wuueagzci)[Whtwnd](https://whtwnd.com/austegard.com/3mgxahx5axp2c)

**How this maps to Sutra:**

The deep parallel is that both projects are asking the same question from opposite ends: *what does it mean to run a program inside a neural substrate?*

Percepta's approach is **bottom-up** — they embed a general interpreter (WASM) into transformer weights and let it run arbitrary programs. Sutra is **top-down** — you write in a high-level language and compile *down* to tensor operations that already are the computation. Percepta emulates a von Neumann machine inside a transformer; Sutra argues the transformer *already is* the right computational model and designs a language native to it.

The Percepta work actually strengthens your theoretical position in an interesting way. They need the 2D convex hull trick to get O(log n) lookups precisely because they're emulating memory addressing — a concept alien to tensor math. Sutra sidesteps this entirely: there's no memory addressing to emulate because the execution model is pure function application compiled to matrix ops. The "memory" problem doesn't arise.

There's also a direct connection to your compilation approach. Percepta's "first Futamura projection" bakes a specific program into the FFN weights, eliminating the program prefix from the input and yielding a model specialized to one program. That's essentially what Sutra's compiler does by default — beta reduction to tensor normal form *is* partial evaluation, collapsing as much computation as possible at compile time rather than runtime. [GitHub](https://github.com/Percepta-Core/transformer-vm)

The most provocative framing for your paper: Percepta proves programs can live in transformer weights. Sutra is a language *designed* for that fact from the start, rather than retrofitted onto it. Their work is a lovely empirical complement to your theoretical position.
