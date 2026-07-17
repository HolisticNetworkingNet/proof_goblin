# Filesystem Boundaries

Proof Goblin performs a small set of local filesystem operations: it reads
configuration and artifact files, writes prompt and report files, and maintains
the CLI review cache. These operations have explicit same-object, symbolic-link,
permission, and replacement contracts. They do not form a filesystem sandbox
or decide which paths a user or host application is authorized to access.

## Operation inventory

| Operation | Path selection | Principal guarantee |
| --- | --- | --- |
| Configuration read | Caller-supplied `.pgcfg` path | Resolve once, then inspect and read one opened regular file; hash the exact bytes read |
| Artifact read | Caller-supplied path, or standard input | Resolve once, then inspect and read one opened regular file; retain the caller-selected basename |
| Prompt and report write | Caller-supplied `--output` path | Prepare a complete temporary file in the destination directory and atomically replace one directory entry |
| Cache directory | Platform default or `PROOF_GOBLIN_CACHE_DIR` | Reject a symbolic-link final directory and enforce the supported private-directory policy |
| Cache result | Request-derived filename | Read a private regular file without intentionally following a final symbolic link; replace atomically on store |
| Cache reservation | Request-derived lock filename | Create exclusively with private permissions and inspect only regular stale lock files |

Standard input and standard output are process streams rather than
Proof Goblin-owned paths. Their redirection, capture, permissions, and retention
are controlled by the invoking shell or host process.

## Configuration and artifact reads

Proof Goblin resolves a supplied path with strict symbolic-link resolution and
then opens that resolved path once. It obtains the initial size from the open
file descriptor, applies the configured byte limit, reads at most one byte past
the limit, and applies the limit again to the bytes actually read. Directories,
devices, FIFOs, sockets, and other non-regular files are rejected. Use `-` when
an artifact should come from standard input.

Size inspection and reading are therefore bound to the same opened file. A
replacement after the open does not change the bytes Proof Goblin reads. A
symbolic-link or path replacement completed before the open can affect which
object is selected, following ordinary operating-system path semantics. Proof
Goblin does not authenticate that object or authorize the path on the caller's
behalf.

For configuration, `Config.sha256` identifies the exact bytes read and is the
authoritative content provenance. `Config.source_path` is the resolved path name
selected during loading. It is informational: the path may later name another
object, and the digest is not a signature. For an artifact, the name used for
media-type inference and prompt provenance remains the caller-selected final
path component rather than the resolved target's name.

## Prompt and report files

Each file output is first encoded into a temporary file created in the
destination directory. Proof Goblin flushes and synchronizes that file before
using `os.replace()` to replace the destination entry. Readers consequently see
either the earlier file or the complete new file, not a partially written
report. If replacement fails, an existing destination remains in place and the
temporary file is removed when cleanup succeeds.

An existing regular file's POSIX permission bits are copied to its replacement.
An existing final symbolic link is replaced by a regular output file; Proof
Goblin does not follow the link and overwrite its target. The destination's
parent path can itself contain symbolic links, and Proof Goblin does not apply
an allowlist, ownership rule, or sandbox to that caller-selected directory.

Atomic replacement is a single-file visibility guarantee, not a complete crash-
durability promise: Proof Goblin synchronizes the file but does not synchronize
the parent directory. Repeated `--output` values are processed sequentially and
are not one transaction. If a later destination fails, every earlier successful
file remains complete and later files are not attempted. Inspect or remove those
earlier files before retrying if a complete set is required.

## Private review cache

The cache contains model-produced observations that may quote sensitive
artifact text. On POSIX systems, Proof Goblin:

- creates the final cache directory with mode `0700`;
- requires an existing final cache directory to be a real directory owned by
  the current effective user with no group or other permissions;
- creates result and lock files with mode `0600`;
- requires existing result and stale lock files to be regular, current-user-
  owned, and inaccessible to group and other users; and
- rejects a final cache-directory or result-file symbolic link.

Cache result reads use `O_NOFOLLOW` where the platform provides it and validate
the opened descriptor. Platforms without that flag retain a narrow gap between
the symbolic-link check and open. The private final cache directory is part of
that trust boundary; Proof Goblin does not secure its ancestor directories or
protect against another process running as the same operating-system user.

Completed cache records are prepared in the cache directory, synchronized,
assigned private permissions, and atomically replaced. Reservations use
exclusive file creation so two ordinary processes cannot acquire the same lock
simultaneously. The fifteen-minute stale-lock rule is recovery behavior, not a
general guarantee against every concurrent process or filesystem failure.

Windows does not expose its effective file ACL policy through POSIX mode bits.
Proof Goblin uses the platform's per-user cache location, rejects the file types
it can identify portably, and relies on inherited Windows access controls; it
does not audit or rewrite Windows ACLs.

## Host responsibilities

The CLI operator or Python host remains responsible for:

- authorizing configuration, artifact, output, and cache paths;
- choosing directories whose parents and mount behavior are trustworthy;
- isolating users or tenants that must not share files or cache entries;
- deciding whether symbolic links are acceptable before invoking Proof Goblin;
- applying encryption, backup, retention, and deletion policy; and
- handling network filesystems or unusual mounts whose replacement, locking, or
  permission semantics differ from ordinary local filesystems.

See {doc}`data-handling` for sensitivity and retention responsibilities and the
{doc}`Error Reference <errors>` for filesystem-related diagnostics.
