# Local (offline) model runtime: what the agent needs from a coding model

The MakeMyFigure Developer is a set of documents, scripts and templates. Any runtime that can do
the following can drive it. No vendor is mandatory; this file states requirements, not products.

## Minimum capabilities

| capability | needed for | notes |
|---|---|---|
| read files (whole or ranges) and list directories | every step | the references cite paths, not code |
| write new files and apply edits/patches | implementation | text insertion into `registry.py` and `ui_hints.py` dict tables (or use `scaffold_plot.py --wire`) |
| execute approved shell commands and read stdout/stderr | scripts, pytest, builds | Python 3.11+, the project's dependencies (`pip install -e ".[desktop]"` when a GUI is needed), no CUDA/GPU |
| iterate on test output | validation loop | tests print `FAILED path::name`; the scripts exit non-zero on failure |
| view images (optional) | mode C references, visual QC of `render_plot_matrix.py` sheets | without vision use the written description in `new-plot-workflow.md` 2.1 and ask the author to look at the sheet |
| read PDFs / extract text and images (optional) | mode D | local tools: `pdftotext` (poppler), PyMuPDF (`fitz`), `pdfimages`; no web access required |
| long context or a scratchpad | keeping the grammar worksheet and plan in view | keep AGENT.md + one reference file + the files being edited open at a time |

Reasoning is the model's job; MakeMyFigure knowledge is the repository's job. A model that has
never seen MakeMyFigure can follow AGENT.md because every step names the file that answers it.

## Environment

- CPU/RAM machine is enough: the full test suite runs headless (`MPLBACKEND=Agg`); typical runtime
  is recorded in `references/testing.md`. Qt GUI tests need PySide6 and a display (Windows/macOS).
- Cross-platform: the scripts are Python; shell examples are given for PowerShell, macOS and Linux
  in `references/packaging.md`. Paths in the scripts are computed, never hard-coded.
- Offline: nothing in the lifecycle needs the network. Release steps that talk to GitHub are
  explicitly marked in `references/release-workflow.md` and only run in RELEASE mode.

## Adapter pattern (optional, add later, never required)

If a runtime needs a thin adapter, keep it OUTSIDE the agent (e.g. `tools/adapters/<runtime>/`)
and limit it to: (1) how the runtime is pointed at `AGENT.md` as its instruction file, (2) how it
runs shell commands and reads results, (3) how images are passed when supported. The agent itself
must not import or mention a runtime. Candidate runtimes users have asked about include local
servers exposing an OpenAI-compatible API (Ollama, LM Studio, llama.cpp) and cloud coding agents;
all of them fit the pattern above.

## Honesty rules for limited runtimes

- No vision: say so, use the description fallback, ask the author to review the render matrix.
- No PDF tooling: ask for the figure exported as PNG plus the legend text.
- No source data: implement the general plot with synthetic seeded example data; never type in
  published values.
- Cannot build a binary (missing PySide6/PyInstaller): report it and give the from-source launch
  (`build_local_test_app.py --source`); never claim an artifact exists.
