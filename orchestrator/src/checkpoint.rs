//! YPRC per-process cold-store codec — the next Rust orchestrator unit.
//!
//! Byte-for-byte compatible with Python `kernel/checkpoint.py::serialise_process`:
//! the self-contained blob for one cold-stored process — its manifest, service
//! identity, and queued inbox. It wraps the `YAXE` envelopes from `axon` (unit
//! 2), so this composes the lower units.
//!
//! Layout (little-endian):
//! ```text
//!   0   4    magic b"YPRC"
//!   4   1    version (= 1)
//!   5   3    reserved
//!   8   ...  u32-len-prefixed name (UTF-8)
//!       ...  u32-len-prefixed manifest JSON (UTF-8)
//!       ...  u32-len-prefixed identity JSON (UTF-8)
//!       4    inbox count (u32 LE)
//!            per axon: u32-len-prefixed YAXE envelope
//! ```
//!
//! **JSON is NOT parsed here.** The manifest and identity are returned as
//! BORROWED byte slices. `no_std` without an allocator can't build the maps a
//! JSON parse needs; parsing them is a deferred, separable unit (a hand-rolled
//! `no_std` JSON reader, or `serde_json` once the orchestrator links `std`).
//! Naming that gap plainly — this unit reads the binary framing and hands the
//! JSON through untouched, which is the honest increment, not a faked parse.

use crate::axon::{
    parse_axon_envelope, put_u32_prefixed, read_u32, read_u32_prefixed, AxonEnvelope, ParseError,
    WriteError,
};

/// Magic prefix for a per-process cold-store blob.
pub const PROC_MAGIC: [u8; 4] = *b"YPRC";
/// Cold-store blob version.
pub const PROC_VERSION: u8 = 1;
/// Header size (magic + version + 3 reserved bytes).
pub const PROC_HEADER_SIZE: usize = 8;

/// A parsed per-process cold-store blob. `name` is validated UTF-8; the JSON
/// fields are borrowed, un-parsed bytes (see the module note); the inbox is
/// walked lazily via [`ProcessBlob::inbox`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ProcessBlob<'a> {
    pub name: &'a str,
    pub manifest_json: &'a [u8],
    pub identity_json: &'a [u8],
    inbox_blob: &'a [u8],
    inbox_count: u32,
}

impl<'a> ProcessBlob<'a> {
    /// Number of queued axons in the inbox.
    pub fn inbox_count(&self) -> u32 {
        self.inbox_count
    }

    /// Lazily iterate the inbox axons. Each item is a `Result` because the YAXE
    /// envelope is parsed on access (framing validated at parse time).
    pub fn inbox(&self) -> InboxIter<'a> {
        InboxIter {
            data: self.inbox_blob,
            remaining: self.inbox_count,
        }
    }
}

/// Iterator over a [`ProcessBlob`]'s inbox. See [`ProcessBlob::inbox`].
#[derive(Debug, Clone)]
pub struct InboxIter<'a> {
    data: &'a [u8],
    remaining: u32,
}

impl<'a> Iterator for InboxIter<'a> {
    type Item = Result<AxonEnvelope<'a>, ParseError>;

    fn next(&mut self) -> Option<Self::Item> {
        if self.remaining == 0 {
            return None;
        }
        self.remaining -= 1;
        match read_u32_prefixed(self.data, 0) {
            Ok((env_bytes, end)) => {
                self.data = &self.data[end..];
                Some(parse_axon_envelope(env_bytes))
            }
            Err(e) => {
                self.remaining = 0; // stop after a framing error
                Some(Err(e))
            }
        }
    }
}

/// Parse a `YPRC` per-process cold-store blob.
pub fn parse_process_blob(data: &[u8]) -> Result<ProcessBlob<'_>, ParseError> {
    if data.len() < PROC_HEADER_SIZE {
        return Err(ParseError::TooShort);
    }
    if data[0..4] != PROC_MAGIC {
        return Err(ParseError::BadMagic);
    }
    let version = data[4];
    if version != PROC_VERSION {
        return Err(ParseError::UnsupportedVersion(version));
    }
    // data[5..8] reserved.
    let (name_bytes, off) = read_u32_prefixed(data, PROC_HEADER_SIZE)?;
    let name = core::str::from_utf8(name_bytes).map_err(|_| ParseError::InvalidUtf8)?;
    let (manifest_json, off) = read_u32_prefixed(data, off)?;
    let (identity_json, off) = read_u32_prefixed(data, off)?;

    let inbox_count = read_u32(data, off)?;
    let inbox_start = off + 4;
    let mut walk = inbox_start;
    for _ in 0..inbox_count {
        let (_env, end) = read_u32_prefixed(data, walk)?;
        walk = end;
    }
    let inbox_blob = &data[inbox_start..walk];

    Ok(ProcessBlob {
        name,
        manifest_json,
        identity_json,
        inbox_blob,
        inbox_count,
    })
}

/// Write a `YPRC` blob into `out`, returning the bytes written. `manifest_json`
/// and `identity_json` are written through as opaque bytes (this unit does not
/// produce JSON — the caller supplies it); `inbox_envelopes` are each a full
/// `YAXE` blob (e.g. from `axon::write_axon_envelope`). No allocation.
pub fn write_process_blob(
    name: &str,
    manifest_json: &[u8],
    identity_json: &[u8],
    inbox_envelopes: &[&[u8]],
    out: &mut [u8],
) -> Result<usize, WriteError> {
    let u32_max = u32::MAX as usize;
    if name.len() > u32_max
        || manifest_json.len() > u32_max
        || identity_json.len() > u32_max
        || inbox_envelopes.len() > u32_max
        || inbox_envelopes.iter().any(|e| e.len() > u32_max)
    {
        return Err(WriteError::FieldTooLong);
    }
    let mut total =
        PROC_HEADER_SIZE + 4 + name.len() + 4 + manifest_json.len() + 4 + identity_json.len() + 4;
    for e in inbox_envelopes {
        total += 4 + e.len();
    }
    if out.len() < total {
        return Err(WriteError::BufferTooSmall {
            needed: total,
            got: out.len(),
        });
    }

    out[0..4].copy_from_slice(&PROC_MAGIC);
    out[4] = PROC_VERSION;
    out[5] = 0;
    out[6] = 0;
    out[7] = 0;
    let mut off = PROC_HEADER_SIZE;
    off = put_u32_prefixed(name.as_bytes(), out, off);
    off = put_u32_prefixed(manifest_json, out, off);
    off = put_u32_prefixed(identity_json, out, off);
    out[off..off + 4].copy_from_slice(&(inbox_envelopes.len() as u32).to_le_bytes());
    off += 4;
    for e in inbox_envelopes {
        off = put_u32_prefixed(e, out, off);
    }
    Ok(off)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::axon::{write_axon_envelope, write_axon_payload, DType, HEADER_SIZE};

    /// Build a small YAXE envelope (payload f32[1,2]) into `buf`, return its len.
    fn make_envelope(role: &str, from_proc: &str, keys: &[&str], buf: &mut [u8]) -> usize {
        let mut body = [0u8; 8];
        body[0..4].copy_from_slice(&1.0f32.to_le_bytes());
        body[4..8].copy_from_slice(&2.0f32.to_le_bytes());
        let mut yaxn = [0u8; HEADER_SIZE + 8];
        let pn = write_axon_payload(DType::Float32, &body, &mut yaxn).unwrap();
        write_axon_envelope(role, from_proc, keys, &yaxn[..pn], buf).unwrap()
    }

    #[test]
    fn write_then_parse_round_trips() {
        let mut env = [0u8; 128];
        let en = make_envelope("R_in", "proc1", &["k"], &mut env);
        let mut out = [0u8; 512];
        let n = write_process_blob(
            "p1",
            b"{\"m\":1}",
            b"{\"kind\":\"sutra\"}",
            &[&env[..en]],
            &mut out,
        )
        .unwrap();

        let pb = parse_process_blob(&out[..n]).unwrap();
        assert_eq!(pb.name, "p1");
        assert_eq!(pb.manifest_json, b"{\"m\":1}");
        assert_eq!(pb.identity_json, b"{\"kind\":\"sutra\"}");
        assert_eq!(pb.inbox_count(), 1);
        let envs: Result<Vec<_>, _> = pb.inbox().collect();
        let envs = envs.unwrap();
        assert_eq!(envs.len(), 1);
        assert_eq!(envs[0].role, "R_in");
        assert_eq!(envs[0].from_proc, "proc1");
        assert_eq!(envs[0].payload.width, 2);
    }

    #[test]
    fn write_then_parse_empty_inbox() {
        let mut out = [0u8; 64];
        let n = write_process_blob("p", b"{}", b"{}", &[], &mut out).unwrap();
        let pb = parse_process_blob(&out[..n]).unwrap();
        assert_eq!(pb.name, "p");
        assert_eq!(pb.inbox_count(), 0);
        assert_eq!(pb.inbox().count(), 0);
    }

    // The exact bytes Python `kernel/checkpoint.py::serialise_process` emits for
    // the echo process with one queued axon (payload f32[1,2,3]). Captured
    // 2026-05-25 as a fixed test vector (regenerate: admit echo, push an Axon
    // with that payload, serialise_process). The identity JSON carries a
    // machine-relative source_path, so the test asserts FRAMING (name + manifest
    // bytes + the parsed envelope), not the path content.
    const PY_YPRC: &[u8] = include_bytes!("../tests/fixtures/echo_process.yprc");

    #[test]
    fn parse_python_process_blob() {
        let pb = parse_process_blob(PY_YPRC).unwrap();
        assert_eq!(pb.name, "echo");

        // manifest JSON slice — exact ends pin the slice boundaries.
        assert_eq!(pb.manifest_json.len(), 161);
        assert!(pb.manifest_json.starts_with(b"{\"axon_keys\": [\"stdin_text\"]"));
        assert!(pb.manifest_json.ends_with(b"\"write_roles\": [\"R_stdout\"]}"));

        // identity JSON slice (path content is machine-relative; check framing).
        assert_eq!(pb.identity_json.len(), 173);
        assert!(pb.identity_json.starts_with(b"{\"entry_point\": \"on_axon\""));
        assert_eq!(pb.identity_json.last(), Some(&b'}'));

        // inbox: one YAXE envelope, parsed by unit 2.
        assert_eq!(pb.inbox_count(), 1);
        let envs: Result<Vec<_>, _> = pb.inbox().collect();
        let envs = envs.unwrap();
        assert_eq!(envs.len(), 1);
        let e = &envs[0];
        assert_eq!(e.role, "R_stdin");
        assert_eq!(e.from_proc, "external");
        let keys: Result<Vec<_>, _> = e.keys().collect();
        assert_eq!(keys.unwrap(), vec!["stdin_text"]);
        assert_eq!(e.payload.width, 3);
        let b = e.payload.body;
        let vals = [
            f32::from_le_bytes([b[0], b[1], b[2], b[3]]),
            f32::from_le_bytes([b[4], b[5], b[6], b[7]]),
            f32::from_le_bytes([b[8], b[9], b[10], b[11]]),
        ];
        assert_eq!(vals, [1.0f32, 2.0, 3.0]);
    }

    #[test]
    fn rust_write_reproduces_python_framing() {
        // Re-wrap the SAME pieces Python emitted and confirm the bytes match,
        // proving the writer is byte-compatible with serialise_process.
        let pb = parse_process_blob(PY_YPRC).unwrap();
        // Pull the single inbox envelope's raw bytes back out. Compute the
        // length-prefix offset from the parsed field lengths (no magic numbers):
        // header + each u32-prefixed section + the inbox-count u32.
        let env_prefix_off = PROC_HEADER_SIZE
            + 4
            + pb.name.len()
            + 4
            + pb.manifest_json.len()
            + 4
            + pb.identity_json.len()
            + 4;
        let env_len = u32::from_le_bytes(
            PY_YPRC[env_prefix_off..env_prefix_off + 4].try_into().unwrap(),
        ) as usize;
        let env_bytes = &PY_YPRC[env_prefix_off + 4..env_prefix_off + 4 + env_len];
        let mut out = vec![0u8; PY_YPRC.len()];
        let n = write_process_blob(
            pb.name,
            pb.manifest_json,
            pb.identity_json,
            &[env_bytes],
            &mut out,
        )
        .unwrap();
        assert_eq!(n, PY_YPRC.len());
        assert_eq!(&out[..n], PY_YPRC);
    }

    #[test]
    fn parse_rejects_bad_magic() {
        let mut b = PY_YPRC.to_vec();
        b[0] = b'X';
        assert_eq!(parse_process_blob(&b), Err(ParseError::BadMagic));
    }

    #[test]
    fn parse_rejects_short() {
        assert_eq!(parse_process_blob(&[89, 80, 82]), Err(ParseError::TooShort));
    }
}
