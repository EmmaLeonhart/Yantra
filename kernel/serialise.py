"""Orchestrator serialisation — easy slice (Emma 2026-05-24 direction).

Captures an axon's output value (the structured-embedding payload tensor)
as Rust-portable bytes, round-tripping bit-exact so a future tick or a
separate process can reconstruct it. The bytes encode JUST the payload —
the ``role``/``from_proc``/``keys`` metadata that an :class:`Axon` wraps is
orchestrator routing state, not part of the value the program emitted. A
caller that wants those fields persisted alongside composes them at the
caller layer (the kernel primitive doesn't impose an envelope).

This is the easy slice (axon output) per Emma's storage-tier-moves direction.
The long pole — serialising a *running* program's full state (weights +
in-flight memory + scheduler position) — needs Sutra-side
``serialise-process-state`` and is genuinely out of scope until that
primitive exists. See ``planning/26-orchestrator-serialisation.md`` for
the design + format spec; ``todo.md`` § 1 for the standing direction.

Format (Rust-portable; no Python pickle):

    Offset  Size  Field
    0       4     Magic b'YAXN' (Yantra AXoN)
    4       1     Version (uint8, current: 1)
    5       1     Dtype tag: 0=float32, 1=float64, 2=complex64, 3=complex128
    6       2     Reserved (pads header to 8-byte boundary)
    8       4     Width (uint32 little-endian; payload vector length)
    12      W*S   Raw little-endian payload bytes (W=width, S=dtype size)

Round-trip is bit-exact via ``torch.equal``. Tested through the calc's real
VSA so that every binding (a, b, op_char, ...) decodes unchanged from the
restored tensor — the substrate value is captured, not a host approximation.
"""
from __future__ import annotations

import struct
from typing import Any

import torch

_MAGIC = b"YAXN"
_VERSION = 1
_HEADER_FMT = "<4sBBHI"  # little-endian: magic, version, dtype_tag, reserved, width
_HEADER_SIZE = 12

# Dtype tags — fixed wire numbers; extending the table is allowed but never
# reassigning an existing tag. The eventual Rust reader must agree on this
# mapping, so it lives here as the source of truth.
_DTYPE_TAGS: dict[torch.dtype, int] = {
    torch.float32: 0,
    torch.float64: 1,
    torch.complex64: 2,
    torch.complex128: 3,
}
_TAGS_DTYPE: dict[int, torch.dtype] = {v: k for k, v in _DTYPE_TAGS.items()}


class AxonSerialiseError(ValueError):
    """Raised on malformed bytes, unsupported version, or shape/dtype mismatch."""


def serialise_axon_payload(payload: torch.Tensor) -> bytes:
    """Encode a 1-D axon payload tensor as Rust-portable bytes.

    The payload is the value an axon carries (``Axon.payload``). The bytes
    encode only the tensor — not the role, sender, or keys metadata.

    Constraints:
      - ``payload`` must be a ``torch.Tensor`` (host floats/ints aren't axons).
      - ``payload`` must be 1-D (axons are vectors at the router; higher-rank
        tensors are not axon outputs).
      - Dtype must be one of float32 / float64 / complex64 / complex128.

    Returns bytes with a 12-byte header + ``width * dtype_size`` body. The
    returned object is a plain ``bytes`` (immutable) and is safe to write to
    disk, hand to an IPC channel, or hash for an audit log.
    """
    if not isinstance(payload, torch.Tensor):
        raise AxonSerialiseError(
            f"payload must be a torch.Tensor, got {type(payload).__name__}"
        )
    if payload.dim() != 1:
        raise AxonSerialiseError(
            f"payload must be 1-D, got shape {tuple(payload.shape)}"
        )
    dtype = payload.dtype
    if dtype not in _DTYPE_TAGS:
        raise AxonSerialiseError(
            f"unsupported dtype {dtype}; supported: float32, float64, "
            "complex64, complex128"
        )
    width = int(payload.shape[0])
    # Move to CPU + contiguous for a predictable byte layout. ``detach``
    # drops any autograd history; serialisation is a value capture, not a
    # gradient capture.
    cpu = payload.detach().to("cpu").contiguous()
    body = cpu.numpy().tobytes()
    header = struct.pack(_HEADER_FMT, _MAGIC, _VERSION, _DTYPE_TAGS[dtype], 0, width)
    return header + body


def deserialise_axon_payload(
    data: bytes | bytearray | memoryview,
    device: Any = "cpu",
) -> torch.Tensor:
    """Decode bytes produced by :func:`serialise_axon_payload` back into a tensor.

    The returned tensor has the original dtype and width, placed on
    ``device`` (default ``"cpu"``). Round-trip is bit-exact: for any payload
    ``t`` produced by the encoder, ``torch.equal(deserialise_axon_payload(
    serialise_axon_payload(t)), t.cpu())`` holds.

    Raises :class:`AxonSerialiseError` on bad magic, unsupported version,
    unknown dtype tag, or body-size mismatch.
    """
    if len(data) < _HEADER_SIZE:
        raise AxonSerialiseError(
            f"data too short for header: {len(data)} bytes (need >= {_HEADER_SIZE})"
        )
    magic, version, dtype_tag, _reserved, width = struct.unpack(
        _HEADER_FMT, bytes(data[:_HEADER_SIZE])
    )
    if magic != _MAGIC:
        raise AxonSerialiseError(f"bad magic {magic!r}; expected {_MAGIC!r}")
    if version != _VERSION:
        raise AxonSerialiseError(
            f"unsupported version {version}; this build reads version {_VERSION}"
        )
    if dtype_tag not in _TAGS_DTYPE:
        raise AxonSerialiseError(f"unknown dtype tag {dtype_tag}")
    dtype = _TAGS_DTYPE[dtype_tag]
    elem_size = torch.tensor([], dtype=dtype).element_size()
    expected_body = width * elem_size
    actual_body = len(data) - _HEADER_SIZE
    if actual_body != expected_body:
        raise AxonSerialiseError(
            f"body size mismatch: got {actual_body} bytes, "
            f"expected {expected_body} ({width} * {elem_size})"
        )
    # ``torch.frombuffer`` views the buffer in-place and requires a writable
    # buffer; bytes is immutable, so copy into a bytearray first. The
    # subsequent ``.clone()`` cuts the tie to the buffer so the returned
    # tensor owns its memory.
    body = bytearray(data[_HEADER_SIZE:])
    cpu_tensor = torch.frombuffer(body, dtype=dtype, count=width).clone()
    return cpu_tensor.to(device)


__all__ = [
    "AxonSerialiseError",
    "serialise_axon_payload",
    "deserialise_axon_payload",
]
