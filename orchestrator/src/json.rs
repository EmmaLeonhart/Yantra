//! Minimal `no_std` JSON reader for the FLAT objects the Python kernel emits in
//! checkpoints — the `manifest` and service-`identity` JSON carried (un-parsed)
//! inside `YPRC`/`YKST` blobs by the `checkpoint` codecs.
//!
//! This is **not** a general JSON parser. It reads a flat object whose values
//! are JSON strings, non-negative integers, or arrays of strings — exactly the
//! schema `kernel/checkpoint.py` writes (`_manifest_to_json` /
//! `_service_identity`). That bounded scope is what lets it stay `no_std` /
//! no-alloc: every accessor returns a BORROWED slice into the input.
//!
//! It is a *structural* scanner, not a substring search: to find a key it reads
//! each `"key": value` pair and skips over the value, so it never false-matches
//! a key name that appears inside some other value. `read_string` skips `\X`
//! escape pairs, so an escaped quote (`\"`) inside a string does not end it
//! early.
//!
//! **Escapes are left raw.** A returned string is the bytes between the quotes
//! verbatim — `"a\\b"` comes back as `a\\b`, not `a\b`. The only escaped field
//! the kernel emits is a Windows `source_path`'s `\\`; a caller that needs the
//! un-escaped form does it itself (un-escaping needs an output buffer, deferred).

fn skip_ws(b: &[u8], mut i: usize) -> usize {
    while i < b.len() && matches!(b[i], b' ' | b'\t' | b'\n' | b'\r') {
        i += 1;
    }
    i
}

/// At `b[i] == '"'`, read a JSON string. Returns `(content_start, content_end,
/// after)` — the raw bytes between the quotes (escapes left literal) and the
/// index just past the closing quote. `None` if not a well-formed string.
fn read_string(b: &[u8], i: usize) -> Option<(usize, usize, usize)> {
    if i >= b.len() || b[i] != b'"' {
        return None;
    }
    let start = i + 1;
    let mut j = start;
    while j < b.len() {
        match b[j] {
            b'\\' => j += 2, // skip the escape pair (\" \\ \n …) without interpreting it
            b'"' => return Some((start, j, j + 1)),
            _ => j += 1,
        }
    }
    None
}

/// Skip one JSON value starting at `b[i]` (after leading ws); return the index
/// just past it. Handles strings, arrays, nested objects, and bare tokens
/// (numbers / true / false / null).
fn skip_value(b: &[u8], i: usize) -> Option<usize> {
    let i = skip_ws(b, i);
    if i >= b.len() {
        return None;
    }
    match b[i] {
        b'"' => {
            let (_, _, after) = read_string(b, i)?;
            Some(after)
        }
        b'[' => {
            let mut j = i + 1;
            loop {
                j = skip_ws(b, j);
                if j >= b.len() {
                    return None;
                }
                if b[j] == b']' {
                    return Some(j + 1);
                }
                j = skip_value(b, j)?;
                j = skip_ws(b, j);
                if j < b.len() && b[j] == b',' {
                    j += 1;
                }
            }
        }
        b'{' => {
            let mut j = i + 1;
            loop {
                j = skip_ws(b, j);
                if j >= b.len() {
                    return None;
                }
                if b[j] == b'}' {
                    return Some(j + 1);
                }
                let (_, _, after) = read_string(b, j)?;
                j = skip_ws(b, after);
                if j >= b.len() || b[j] != b':' {
                    return None;
                }
                j = skip_value(b, j + 1)?;
                j = skip_ws(b, j);
                if j < b.len() && b[j] == b',' {
                    j += 1;
                }
            }
        }
        _ => {
            // bare token: read until a structural delimiter or whitespace.
            let mut j = i;
            while j < b.len() && !matches!(b[j], b',' | b'}' | b']' | b' ' | b'\t' | b'\n' | b'\r') {
                j += 1;
            }
            if j == i {
                None
            } else {
                Some(j)
            }
        }
    }
}

/// Walk a flat top-level object and return the index of `key`'s value (after
/// the `:` and any whitespace), or `None` if the key is absent / the object is
/// malformed. Key comparison is against the raw key bytes (kernel keys have no
/// escapes, so raw == literal).
fn seek_key(b: &[u8], key: &str) -> Option<usize> {
    let mut i = skip_ws(b, 0);
    if i >= b.len() || b[i] != b'{' {
        return None;
    }
    i = skip_ws(b, i + 1);
    while i < b.len() && b[i] != b'}' {
        let (ks, ke, after) = read_string(b, i)?;
        i = skip_ws(b, after);
        if i >= b.len() || b[i] != b':' {
            return None;
        }
        i = skip_ws(b, i + 1); // i now at the value
        if &b[ks..ke] == key.as_bytes() {
            return Some(i);
        }
        i = skip_value(b, i)?;
        i = skip_ws(b, i);
        if i < b.len() && b[i] == b',' {
            i = skip_ws(b, i + 1);
        }
    }
    None
}

/// Get a string field's value (raw content, escapes left literal). `None` if
/// the key is absent or its value is not a string.
pub fn get_str<'a>(obj: &'a [u8], key: &str) -> Option<&'a str> {
    let i = seek_key(obj, key)?;
    if i >= obj.len() || obj[i] != b'"' {
        return None;
    }
    let (cs, ce, _) = read_string(obj, i)?;
    core::str::from_utf8(&obj[cs..ce]).ok()
}

/// Get a non-negative integer field's value. `None` if the key is absent or its
/// value is not a non-negative integer that fits in `u32`.
pub fn get_u32(obj: &[u8], key: &str) -> Option<u32> {
    let i = seek_key(obj, key)?;
    let end = skip_value(obj, i)?;
    let tok = core::str::from_utf8(&obj[i..end]).ok()?.trim();
    if tok.is_empty() || !tok.bytes().all(|c| c.is_ascii_digit()) {
        return None;
    }
    tok.parse::<u32>().ok()
}

/// Iterate a string-array field's elements (each raw, escapes literal). `None`
/// if the key is absent or its value is not an array.
pub fn get_str_array<'a>(obj: &'a [u8], key: &str) -> Option<StrArrayIter<'a>> {
    let i = seek_key(obj, key)?;
    let i = skip_ws(obj, i);
    if i >= obj.len() || obj[i] != b'[' {
        return None;
    }
    Some(StrArrayIter { b: obj, i: i + 1 })
}

/// Iterator over a JSON string array's elements (see [`get_str_array`]).
#[derive(Debug, Clone)]
pub struct StrArrayIter<'a> {
    b: &'a [u8],
    i: usize,
}

impl<'a> Iterator for StrArrayIter<'a> {
    type Item = &'a str;

    fn next(&mut self) -> Option<&'a str> {
        self.i = skip_ws(self.b, self.i);
        if self.i >= self.b.len() || self.b[self.i] != b'"' {
            return None; // ']' or malformed → done
        }
        let (cs, ce, after) = read_string(self.b, self.i)?;
        self.i = skip_ws(self.b, after);
        if self.i < self.b.len() && self.b[self.i] == b',' {
            self.i += 1;
        }
        core::str::from_utf8(&self.b[cs..ce]).ok()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // The exact manifest JSON kernel/checkpoint.py::_manifest_to_json emits for
    // echo (sort_keys=True, ", "/": " separators).
    const MANIFEST: &[u8] = b"{\"axon_keys\": [\"stdin_text\"], \"axon_width\": 768, \
\"compute_units\": 1, \"name\": \"echo\", \"read_roles\": [\"R_stdin\"], \
\"source\": \"echo.su\", \"write_roles\": [\"R_stdout\"]}";

    #[test]
    fn manifest_string_fields() {
        assert_eq!(get_str(MANIFEST, "name"), Some("echo"));
        assert_eq!(get_str(MANIFEST, "source"), Some("echo.su"));
    }

    #[test]
    fn manifest_int_fields() {
        assert_eq!(get_u32(MANIFEST, "axon_width"), Some(768));
        assert_eq!(get_u32(MANIFEST, "compute_units"), Some(1));
    }

    #[test]
    fn manifest_string_arrays() {
        let read: Vec<&str> = get_str_array(MANIFEST, "read_roles").unwrap().collect();
        assert_eq!(read, vec!["R_stdin"]);
        let write: Vec<&str> = get_str_array(MANIFEST, "write_roles").unwrap().collect();
        assert_eq!(write, vec!["R_stdout"]);
        let keys: Vec<&str> = get_str_array(MANIFEST, "axon_keys").unwrap().collect();
        assert_eq!(keys, vec!["stdin_text"]);
    }

    #[test]
    fn absent_and_wrong_type() {
        assert_eq!(get_str(MANIFEST, "nope"), None);
        assert_eq!(get_u32(MANIFEST, "name"), None); // value is a string, not an int
        assert!(get_str_array(MANIFEST, "axon_width").is_none()); // not an array
        assert_eq!(get_str(MANIFEST, "axon_width"), None); // not a string
    }

    #[test]
    fn escaped_quote_does_not_end_string_early() {
        // JSON: {"a": "x\"y", "b": "z"} — the \" must not terminate "a"'s value,
        // and "b" must still be found after it.
        let obj: &[u8] = b"{\"a\": \"x\\\"y\", \"b\": \"z\"}";
        assert_eq!(get_str(obj, "a"), Some("x\\\"y")); // raw content, escapes literal
        assert_eq!(get_str(obj, "b"), Some("z"));
    }

    #[test]
    fn escaped_backslash_path_returns_raw() {
        // JSON: {"source_path": "..\\apps\\echo.su"} — two literal backslashes
        // per separator (Python escaped the Windows path). Returned raw.
        let obj: &[u8] = b"{\"source_path\": \"..\\\\apps\\\\echo.su\"}";
        assert_eq!(get_str(obj, "source_path"), Some("..\\\\apps\\\\echo.su"));
    }

    #[test]
    fn array_value_does_not_confuse_later_keys() {
        // A later scalar key must be found past an array value.
        assert_eq!(get_str(MANIFEST, "source"), Some("echo.su"));
        assert_eq!(get_u32(MANIFEST, "compute_units"), Some(1));
    }
}
