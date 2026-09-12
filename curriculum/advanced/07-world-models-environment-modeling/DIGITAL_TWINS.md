# Deep Dive: Digital Twins Are Scoped, Synchronized Models

A digital twin is a model of **selected** properties and dynamics of a real counterpart, synchronized with observations to a defined degree. It may be deterministic or stochastic, physics-based, data-driven, discrete-event, state-machine based, or hybrid. It is never automatically exact.

## Digital twin is not sandbox

```text
Sandbox      -> isolates execution
Simulator    -> predicts under assumptions
World model  -> represents state and transition dynamics
Digital twin -> synchronizes a scoped model with a real counterpart
```

An in-memory SQLite clone is useful for isolated schema tests. Call it a sandbox or test replica unless it genuinely has the synchronization, scope, dynamics, and validation needed to justify “digital twin.” SQLite does not reproduce every PostgreSQL permission, trigger, lock, extension, replication, concurrency, query-planning, data-distribution, or network behavior.

Therefore:

```text
the sandbox did not raise an exception
!=
the production action is safe or authorized
```

Simulation can reduce the probability of unsafe actions by detecting failures that the model represents accurately. It cannot eliminate model error, stale state, unknown dependencies, races, drift, or implementation defects.

The canonical notebook applies this definition with versioned observations, a `ModelSnapshot`, applicability checks, typed predicted state, and a separate approval-bound execution envelope.

See NIST's [digital twin glossary](https://csrc.nist.gov/glossary/term/digital_twin), NIST's [definitions overview](https://www.nist.gov/digital-twins/definitions-and-state-art), and AWS's operational [TwinMaker concepts](https://docs.aws.amazon.com/iot-twinmaker/latest/guide/what-is-twinmaker.html).
