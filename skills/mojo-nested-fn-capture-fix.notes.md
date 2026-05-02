# Mojo Nested Fn Capture Fix — Raw Notes

## Session Date: 2026-03-15

## Error Message

```text
examples/googlenet-cifar10/train.mojo:89:8: error: cannot synthesize fieldwise init
because field 'field0' has non-copyable and non-movable type 'GoogLeNet'

examples/mobilenetv1-cifar10/train.mojo:89:8: error: cannot synthesize fieldwise init
because field 'field0' has non-copyable and non-movable type 'MobileNetV1'
```

Both errors triggered by `--Werror` being promoted to compilation failures.

## Files Affected

- `examples/googlenet-cifar10/train.mojo` — nested `fn compute_batch_loss` captured `GoogLeNet`
- `examples/mobilenetv1-cifar10/train.mojo` — nested `fn compute_batch_loss` captured `MobileNetV1`

## Pattern Discovered

When a nested `fn` is defined inside another function in Mojo, the compiler synthesizes an
implicit capture struct to hold all variables from the outer scope that the nested fn references.
The compiler then tries to generate a fieldwise initializer for this capture struct.

If any captured variable has a type that is:

- non-copyable (no `__copyinit__`)
- non-movable (no `__moveinit__`)

...the fieldwise init synthesis fails with the error above.

Complex ML model structs (GoogLeNet, MobileNetV1, etc.) have heap-allocated weight tensors that
make them non-copyable and non-movable by default in Mojo.

## Fix Applied

Removed the `fn compute_batch_loss` nested function from both files and inlined the batch
processing loop directly in `train_epoch`, calling `model.forward()` directly in the loop body.

Also removed now-unused `TrainingLoop` imports from both files.

## Reference Pattern

`examples/resnet18-cifar10/train.mojo` already used the correct pattern — it had no nested
capturing fn and called model methods directly in the loop. This was used as the template for
the fix.

## CI Context

The failures appeared with `--Werror` flag, which promotes all warnings to errors. The nested fn
capture struct synthesis issue was treated as an error in this mode.

## Investigation Notes

- Line 89 in both files was the `fn compute_batch_loss(...)` definition line
- `field0` in the error message refers to the first captured variable (the model struct)
- The error is a compiler-level limitation, not a user code logic error
- No changes to model structs themselves were needed; only the usage pattern in the example

## Alternatives Considered

### UnsafePointer approach

Could store the model as `UnsafePointer[GoogLeNet]` in the capture struct to avoid
non-copyability. Rejected because it introduces unsafe code for no real benefit when
inlining is trivially available.

### Ownership transfer with ^

Could rewrite `compute_batch_loss` to take `model` by ownership (`^`). Rejected because
this would require returning the model from the nested fn, significantly restructuring the
`train_epoch` function signature and logic.

### @register_passable on model

Considered marking the model structs as `@register_passable`. Rejected because this is for
simple register-sized value types, not for complex structs with heap-allocated fields
like weight matrices.
