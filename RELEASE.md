# Releasing PASE

PASE is published to PyPI as **`pase-agrivoltaics`** (the import package stays
`pase`). Releases are **semi-automated**: a maintainer drives the changelog,
merge, and tag; CI builds and publishes.

The version is derived from the git tag by **setuptools-scm** — there is no
version string to bump by hand. A clean checkout sitting exactly on tag
`vX.Y.Z` builds as `X.Y.Z`; anything else builds as a `.devN+g<hash>`
pre-release (which PyPI refuses, so dev builds can never be published by
accident).

---

## One-time setup (project Owner, in the GitLab UI)

Do this once before the first release. It cannot be done from the repo.

1. **PyPI + TestPyPI accounts.** Create accounts on <https://pypi.org> and
   <https://test.pypi.org>. The first upload of `pase-agrivoltaics` claims the
   name for the lab.
2. **API tokens as CI/CD variables** (Settings → CI/CD → Variables). Add both as
   **Protected** and **Masked**:
   - `PYPI_API_TOKEN` — a PyPI API token (scope it to the project once it exists).
   - `TESTPYPI_API_TOKEN` — a TestPyPI API token.
   > Trusted Publishing (OIDC) is **not** available: PyPI only trusts the
   > `gitlab.com` issuer, and PASE is on self-hosted `gitlab.uliege.be`. Hence
   > token auth.
3. **Protect the release tags** (Settings → Repository → Protected tags): add the
   wildcard `v*` so only maintainers can create release tags and the protected
   tokens are exposed to those pipelines.

---

## What CI does

On a pushed tag matching `vX.Y.Z`:

1. `test_release` — runs the suite with `-m "not network"` (skips the live-PVGIS
   tests so a network hiccup can't block a release).
2. `build` — builds the sdist + wheel and runs `twine check`.
3. `publish_testpypi` — **manual** (click ▶ in the pipeline) dry-run upload to
   TestPyPI. Non-blocking.
4. `publish_pypi` — uploads to PyPI. **Only on final tags** (`vX.Y.Z` with no
   suffix); `rc`/pre-release tags stop at TestPyPI.

`build` also runs on the default branch so packaging breakage is caught early.

---

## Release checklist

1. **Land all changes on `develop`** and make sure its pipeline is green.
2. **Finalize the changelog.** In `CHANGELOG.md`, retitle `## [Unreleased]` to
   `## [X.Y.Z] - YYYY-MM-DD`, resolve any "Needs human triage" items, and add a
   fresh empty `## [Unreleased]` above it. Commit on `develop` (via MR).
3. **Cut the release branch** off `develop` and open an MR into `main`:
   ```bash
   git switch develop && git pull
   git switch -c release-vX.Y.Z
   # push, open MR release-vX.Y.Z -> main, get one Owner approval, merge
   ```
4. **Tag on `main`** (the merge commit) and push the tag:
   ```bash
   git switch main && git pull
   git tag vX.Y.Z          # annotated is fine: git tag -a vX.Y.Z -m "vX.Y.Z"
   git push <remote> vX.Y.Z
   ```
   Build from a clean tree so setuptools-scm emits `X.Y.Z` (no `.dev`/`+`).
5. **Dry-run to TestPyPI.** In the tag pipeline, run the manual `publish_testpypi`
   job. Optionally verify:
   ```bash
   pip install -i https://test.pypi.org/simple/ \
       --extra-index-url https://pypi.org/simple/ pase-agrivoltaics
   ```
6. **Publish.** `publish_pypi` runs automatically on the final tag. Confirm the
   release at <https://pypi.org/project/pase-agrivoltaics/> and in a clean venv:
   ```bash
   pip install pase-agrivoltaics
   python -c "import pase; print(pase.__version__)"
   ```
7. **Publish the GitLab Release** for the tag, pasting the changelog section as
   the release notes.
8. **Back-merge `main` into `develop`** if the release branch received fixes, so
   the two branches don't diverge.

---

## First release — v1.4.0 (catch-up)

`v1.4.0` is the first release on this pipeline and clears the `v1.3.0..develop`
backlog (see the `[Unreleased]` entry in `CHANGELOG.md`). `main` is far behind
`develop`; we do **not** reconstruct the intermediate releases — a single
`release-v1.4.0 -> main -> tag v1.4.0` brings `main` current in one clean,
auditable step and proves the pipeline end to end.

Before tagging `v1.4.0`, smoke-test the pipeline with a throwaway pre-release
tag (goes to TestPyPI only, never PyPI):

```bash
git tag v0.0.0rc1 && git push <remote> v0.0.0rc1
# run the manual publish_testpypi job; then delete the throwaway tag:
git push <remote> :refs/tags/v0.0.0rc1 && git tag -d v0.0.0rc1
```
