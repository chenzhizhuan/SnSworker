# Cqlib SDK Contract

## Selection Boundary

Use Cqlib only when the selected `QMLRoute` names `sdk=cqlib`, the installed version passes
capability inspection, and the selected variant passes its own materialized smoke. Cqlib
currently provides circuit and simulator primitives rather than maintained high-level QML
estimators; do not describe a primitives-based adapter as a native Cqlib QML algorithm.

## Library-First Components

- Use `cqlib.Circuit` and `cqlib.Parameter` for circuit and parameter semantics.
- Use `cqlib.simulator.SimpleSimulator` for the local PyTorch-backed differentiable path.
- Keep tensors connected through `SimpleSimulator.probs()` or statevector computation; do
  not convert to `float`, NumPy, or detached values before the loss.
- Prove a finite nonzero gradient and one effective parameter update before claiming native
  autodiff.

## Runtime Adapter

Call `materialize_qml_adapter`, then use:

```python
from algorithm.qml_runtime.runtime import load_and_infer, train_and_save

train_and_save("models/qml-model.bin", rows=train_rows, targets=train_targets)
result = load_and_infer("models/qml-model.bin", fixture_request)
```

Keep application-specific data preparation and configuration outside
`algorithm/qml_runtime/**`. Do not create another task-local classifier, reservoir, QNN
wrapper, simulator bridge, or replacement implementation.

## Parameter and Measurement Semantics

Record qubit and classical-output ordering, parameter insertion and binding order, tensor
dtype/device, statevector or probability shape, observable construction, and conversion into
the profile output. Do not detach, cast to `float`, or convert to NumPy before a differentiable
loss. The C backend is not equivalent to the local PyTorch-backed simulator.

## Persistence

The offline training script writes model state under `models/`; the inference bundle records
its hash, preprocessing, route, package versions, request/response schemas, and known fixture.
Reload in a fresh Python process and verify the fixture before publishing the bundle.

## Unsupported Behavior

If the materialized adapter lacks the selected variant's actual model and acceptance smoke,
return an unavailable capability. Do not replace it with a one-qubit feature, linear
placeholder, another SDK, or TianYan execution. This Skill is local-only and must not submit
cloud jobs.

## Evidence

Record the Cqlib and PyTorch versions, simulator class, tensor dtype, device, parameter/wire
mapping, reused adapter ID/version, gradient or non-gradient method, model hash, reload fixture,
and profile-specific diagnostics.
