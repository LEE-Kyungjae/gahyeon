process.stderr.write(
  "RETIRED_RUNTIME: Electron is not the Gahyeon service. "
  + "Use scripts/launch_canonical_macos_runtime.py from the repository root.\n",
)
process.exitCode = 2
