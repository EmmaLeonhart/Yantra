"""Axon router — the kernel's IPC primitive.

An `Axon` here is a simple value-object: a payload tensor plus the
role it was bound under. The real Sutra-side axon (rotation-bound
fixed-width vector) compiles to a torch tensor of shape
`(axon_width,)`; the router does not re-bind, it just delivers.
The capability check happens at delivery time, not at write time —
so a process can compose an axon for a role it can't write, and the
router refuses to deliver it. (This matches the threat-model story
in `paper/paper.md` § 3.3.1: capability check happens before bundle
composition at the receiver, rotation operators are themselves the
gate.)

In v0.0 the payload is a Python object (typically a `torch.Tensor`)
that crosses thread boundaries by reference. This is *not* the
production model — the production model passes axons by value via
device-side serialisation — but it is sufficient to demonstrate
process-to-process communication and the capability-check semantics
the architecture commits to.
"""

from __future__ import annotations

import dataclasses
import threading
from collections import defaultdict, deque
from typing import Any, Iterator

from kernel.manifest import Manifest


class CapabilityError(PermissionError):
    """A process tried to send or receive on a role it doesn't possess."""


class NotAdmittedError(LookupError):
    """A process name was referenced that init never admitted."""


@dataclasses.dataclass(frozen=True)
class Axon:
    """A single in-flight message between processes.

    `role`        — the role-name the payload was bundled under
    `payload`     — the tensor (or tensor-like value) the role carries
    `from_proc`   — the name of the sending process (for capability +
                    audit)
    """
    role: str
    payload: Any
    from_proc: str


class AxonRouter:
    """In-memory router with capability check on send and receive.

    The router holds:
      - `_processes` : name → manifest, populated by init at admission
      - `_inboxes`   : name → deque[Axon], one inbox per admitted process
      - `_routes`    : role → list[receiver-name], the delivery table

    The route table is rebuilt at admission time from the union of
    every admitted process's `read_roles`. Multiple receivers on one
    role is a fan-out (every receiver gets a copy); zero receivers on
    a role is a black-hole (the send is logged and dropped, *not* an
    error — sending a "log" axon to a logger that hasn't been admitted
    yet is normal startup-order, not a capability violation).
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._processes: dict[str, Manifest] = {}
        self._inboxes: dict[str, deque[Axon]] = {}
        self._routes: dict[str, list[str]] = defaultdict(list)
        self._dropped_audit: list[Axon] = []

    # --- admission lifecycle (called by init) ---

    def register(self, manifest: Manifest) -> None:
        """Add a process and route its read-roles into the table."""
        with self._lock:
            if manifest.name in self._processes:
                raise ValueError(
                    f"router: process {manifest.name!r} already registered"
                )
            self._processes[manifest.name] = manifest
            self._inboxes[manifest.name] = deque()
            for role in manifest.read_roles:
                self._routes[role].append(manifest.name)

    def deregister(self, name: str) -> None:
        """Remove a process and tear down its routes."""
        with self._lock:
            if name not in self._processes:
                raise NotAdmittedError(name)
            for role in self._processes[name].read_roles:
                receivers = self._routes.get(role, [])
                if name in receivers:
                    receivers.remove(name)
                if not receivers:
                    self._routes.pop(role, None)
            del self._processes[name]
            del self._inboxes[name]

    # --- send / receive (called by services) ---

    def send(self, axon: Axon) -> int:
        """Deliver `axon` from `axon.from_proc`. Returns receiver count.

        Capability check on send: the sender must possess `axon.role`
        in its write_roles. Returns the number of receivers the axon
        was delivered to (0 is allowed; see class docstring).
        """
        with self._lock:
            sender = self._processes.get(axon.from_proc)
            if sender is None:
                raise NotAdmittedError(axon.from_proc)
            if axon.role not in sender.write_roles:
                raise CapabilityError(
                    f"process {axon.from_proc!r} cannot write role "
                    f"{axon.role!r} (write_roles={sorted(sender.write_roles)})"
                )
            receivers = list(self._routes.get(axon.role, []))
            if not receivers:
                # Black-hole: log + drop. Not an error — see class docstring.
                self._dropped_audit.append(axon)
                return 0
            for r in receivers:
                # Capability check on receive — defence in depth: even
                # if the route table is wrong, a process never gets an
                # axon for a role it can't read.
                receiver = self._processes[r]
                if axon.role not in receiver.read_roles:  # pragma: no cover
                    raise CapabilityError(
                        f"router invariant broken: route table claims "
                        f"{r!r} reads {axon.role!r} but its read_roles "
                        f"are {sorted(receiver.read_roles)}"
                    )
                self._inboxes[r].append(axon)
            return len(receivers)

    def receive(self, name: str) -> Axon | None:
        """Pop the next axon for `name`, or None if the inbox is empty."""
        with self._lock:
            inbox = self._inboxes.get(name)
            if inbox is None:
                raise NotAdmittedError(name)
            if not inbox:
                return None
            return inbox.popleft()

    def drain(self, name: str) -> Iterator[Axon]:
        """Yield all currently-buffered axons for `name`."""
        while True:
            ax = self.receive(name)
            if ax is None:
                return
            yield ax

    # --- introspection (used by tests + observability) ---

    def admitted(self) -> list[str]:
        with self._lock:
            return sorted(self._processes)

    def dropped_count(self) -> int:
        with self._lock:
            return len(self._dropped_audit)

    def inbox_depth(self, name: str) -> int:
        with self._lock:
            inbox = self._inboxes.get(name)
            if inbox is None:
                raise NotAdmittedError(name)
            return len(inbox)
