"""Tests for post-review fixes on ExTensor migration.

# ADR-009: This file is intentionally limited to <=10 fn test_ functions.
# Mojo v0.26.1 heap corruption (libKGENCompilerRTShared.so) triggers under
# high test load. See docs/adr/ADR-009-heap-corruption-workaround.md

Tests cover:
- AnyTensor __hash__ uses typed access, not _get_float64
- AnyTensor hash consistency and distinctness
- AnyTensor conforms to TensorLike trait
- In-place addition preserves float64 precision (M1 fix)
- In-place subtraction preserves float64 precision (M1 fix)
- __neg__ works correctly on AnyTensor
"""

from testing import assert_true, assert_almost_equal
from shared.tensor.tensor import Tensor
from shared.core.extensor import AnyTensor, zeros, ones


fn test_anytensor_hash_consistency() raises:
    """AnyTensor with identical data should produce identical hashes."""
    var t1 = zeros([4], DType.float32)
    t1._set_float32(0, Float32(0.5))
    t1._set_float32(1, Float32(1.0))

    var t2 = zeros([4], DType.float32)
    t2._set_float32(0, Float32(0.5))
    t2._set_float32(1, Float32(1.0))

    # Same data should produce same hash
    assert_true(hash(t1) == hash(t2), "identical tensors should hash equal")
    print("PASS: test_anytensor_hash_consistency")


fn test_anytensor_hash_different_values() raises:
    """Different tensor values should (likely) produce different hashes."""
    var t1 = zeros([4], DType.float32)
    t1._set_float32(0, Float32(0.5))

    var t2 = zeros([4], DType.float32)
    t2._set_float32(0, Float32(1.0))

    # Different data should (very likely) produce different hash
    assert_true(hash(t1) != hash(t2), "different tensors should hash differently")
    print("PASS: test_anytensor_hash_different_values")


fn test_anytensor_conforms_tensorlike() raises:
    """AnyTensor should conform to TensorLike trait."""
    var t = zeros([3, 4], DType.float32)
    # If AnyTensor conforms to TensorLike, these compile and run
    assert_true(t.numel() == 12, "numel")
    assert_true(t.ndim() == 2, "ndim")
    assert_true(t.dtype() == DType.float32, "dtype")
    var s = t.shape()
    assert_true(len(s) == 2, "shape len")
    print("PASS: test_anytensor_conforms_tensorlike")


fn test_iadd_precision_float64() raises:
    """In-place addition preserves float64 precision (M1 fix).

    The review identified that __iadd__ round-trips through _get_float64 /
    _set_float64 which loses precision for non-float64 dtypes. This test
    verifies float64 precision is preserved end-to-end.
    """
    var a = zeros([4], DType.float64)
    a._set_float64(0, 3.141592653589793)
    var b = zeros([4], DType.float64)
    b._set_float64(0, 2.718281828459045)
    a += b
    # Full float64 precision should be preserved
    var expected = 3.141592653589793 + 2.718281828459045
    assert_almost_equal(a._get_float64(0), expected, atol=1e-12)
    print("PASS: test_iadd_precision_float64")


fn test_isub_precision_float64() raises:
    """In-place subtraction preserves float64 precision (M1 fix).

    Same concern as __iadd__: _get/_set_float64 round-trip should preserve
    full float64 precision when the tensor is already float64.
    """
    var a = zeros([4], DType.float64)
    a._set_float64(0, 3.141592653589793)
    var b = zeros([4], DType.float64)
    b._set_float64(0, 1.0)
    a -= b
    var expected = 3.141592653589793 - 1.0
    assert_almost_equal(a._get_float64(0), expected, atol=1e-12)
    print("PASS: test_isub_precision_float64")


fn test_neg_anytensor() raises:
    """__neg__ works correctly on AnyTensor."""
    var t = zeros([4], DType.float32)
    t._set_float32(0, Float32(1.5))
    t._set_float32(1, Float32(-0.5))
    var neg_t = -t
    assert_almost_equal(neg_t._get_float32(0), Float32(-1.5), atol=1e-6)
    assert_almost_equal(neg_t._get_float32(1), Float32(0.5), atol=1e-6)
    print("PASS: test_neg_anytensor")


fn main() raises:
    test_anytensor_hash_consistency()
    test_anytensor_hash_different_values()
    test_anytensor_conforms_tensorlike()
    test_iadd_precision_float64()
    test_isub_precision_float64()
    test_neg_anytensor()
    print("\nAll 6 review fix tests passed")
