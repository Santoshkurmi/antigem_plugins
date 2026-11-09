# Native code: .so libraries and other binaries

Extract the library first (native libs of Play Store installs are in the ABI split):

```sh
mkdir -p ~/re/<package> && cd ~/re/<package>
unzip -l <split_config.arm64_v8a.apk or base.apk> | grep '\.so$'
unzip -o -q <apk> 'lib/arm64-v8a/*' -d .
```

## Static facts without a decompiler (group `native`)

- `inspect_elf_notes {path}`: build-id, Android NDK note (NDK version), other ELF notes.
- `inspect_native_exports {path}`: exported symbols. `Java_<package>_<class>_<method>` names are JNI functions
  called from Java (`native` methods in JADX output); `JNI_OnLoad` registers others dynamically.
- `inspect_with_objdump {path, operation}`: `file_headers`, `section_headers`, `symbols`, `relocations`,
  `dwarf`, `disassemble` (add `symbol` to disassemble one function), `disassemble_all`. Prefer `symbol`:
  whole-library disassembly is huge.
- `execute_rizin_command {path, command}`: one rizin command per call, for example
  - `iI` binary info, `iE` exports, `ii` imports, `iz` / `izz` strings (data / whole file), `iS` sections
  - `aa; afl` find and list functions (slow on big libraries; prefer `aa` over `aaa`)
  - `pdf @ sym.Java_com_example_Native_check` disassemble one function
  - `axt @ <address>` cross references to an address (after `aa`)
  - `/ <text>` search a string
  rizin commands can read and write files: only run analysis commands.
- `inspect_rust_binary`, `inspect_go_binary`: toolchain facts of Rust/Go binaries.

## Unity IL2CPP games (group `unity`)

`global-metadata.dat` (in `assets/bin/Data/Managed/Metadata/`) plus `libil2cpp.so`:
`inspect_il2cpp_metadata {path: "<global-metadata.dat>", binary_path: "<libil2cpp.so>"}` gives type, method and
field names, string literals and, with the binary, method addresses. Page results with `inspect_analysis_view`
(`source: {kind: "retained-evidence", evidence_id: <parent_evidence_id>}`, view `kind: "il2cpp-metadata"`). Use the addresses with rizin `pdf @ <address>`.

## Pseudo-C decompiling

The `decompiler` group (open_binary, procedure_pseudo_code…) needs Ghidra, IDA, Hopper or Kuna, which this setup
does not install. Without them, use rizin disassembly and explain the code from assembly. Do not promise
pseudo-C.

## Debugging (group `debug`)

gdb works inside the container (`bash <setup>/rea-setup.sh debug`). It can only debug programs you start in the
container; attaching to Android apps needs root. Prefer static analysis.
