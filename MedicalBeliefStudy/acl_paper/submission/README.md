# ACL manuscript package

**Do Language Models Have Medical Beliefs? Tracing Evidence, Internal Disease Information, and Diagnostic Choice**

This is a complete manuscript draft with existing empirical results, not a claim that outstanding generalization and natural-mediation experiments have been completed. Nothing has been submitted or published.

- `main.tex`: full English manuscript; official ACL review style.
- `main.pdf`: compiled manuscript, references, methods, and complete case appendix.
- `paper.pdf`: main manuscript including limitations, ethics, and references.
- `supplement.pdf`: methods and case appendices.
- `references.bib`: 12 cited primary works, with source URLs.
- `sections/appendix.tex`: implementation, robustness, exact instructions, and ten contrasting examples.
- `sections/all_cases.tex`: all 24 preselected patient trajectories and source evidence.
- `figures/`: vector PDF and PNG figures.
- `data/`: endpoint/trajectory tables and post-hoc synthesis; repeated observations are not independent patients.
- `qa/validation.json`: artifact, citation, numerical, page, and layout checks.

## Build

From this directory, run `tectonic -k --keep-logs main.tex`, or use `latexmk -pdf main.tex`. The project-local compiler is `../../.tools/tectonic`. TeX Live/Overleaf can use the included official `acl.sty` and `acl_natbib.bst`. No model inference is needed to compile the manuscript.

The case synthesis is reproducible with `MedicalBeliefStudy/src/phase22_paper_cases.py` using the study's existing frozen records. The opening figure uses `src/build_acl_opening.py`. Run these with the project's analysis Python environment, then compile. Complete experiment reproduction remains in [the study reproduction protocol](../../protocol/BELIEF_V2_REPRODUCE.md); this link is valid in the full project checkout.

## Format and status

Official style: https://github.com/acl-org/acl-style-files

Length guidance checked 2026-11-19: https://aclrollingreview.org/cfp (eight pages of main content for long papers; limitations/ethics/references follow).

The final paper length is recorded in `qa/validation.json`. The review PDF has anonymous authors. Author/service metadata and a specific submission cycle have not been selected. The paper does not state that its materials are already publicly released.

The current scope is synthetic DDxPlus cases, two Qwen3 configurations, and explicit thinking disabled. The 1.7B/4B comparison changes precision as well as size. Natural-evidence causal mediation and alternative clinical data sources remain untested. These limitations are part of the paper rather than missing prose.
