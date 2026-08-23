# Contributing

phillysim is a solo-maintained public-interest project developed in bounded
work packets ([roadmap/](roadmap/)). Outside contributions are welcome in a
narrow form; the governance documents bind everyone, including the
maintainer.

## Ways to contribute

- **Data corrections** (wrong location, hours, closure, miscategorization):
  open a GitHub Issue — see [docs/policies.md](docs/policies.md). This is the
  most valuable kind of contribution.
- **Delisting requests** from listed sites/organizations: same channel,
  expedited handling per [docs/policies.md](docs/policies.md).
- **Bug reports and methods questions:** GitHub Issues. Methods critiques are
  welcome; every published metric has (or will have) a method card to critique
  against.
- **Pull requests:** open an issue first. Small fixes are welcome; new
  features must fit the accepted scope ([roadmap/scope.md](roadmap/scope.md))
  and the claims discipline ([docs/CLAIMS.md](docs/CLAIMS.md)) — PRs that add
  scores, rankings, predictions, or nutrition-quality labels will be declined
  on governance grounds regardless of code quality.

## Hard rules for any change

- **Never commit source datasets.** Only `data/public/` outputs, with
  validated license labels, ever enter the repository — and only via the
  publish gate. See [docs/DATA-LICENSES.md](docs/DATA-LICENSES.md).
- No secrets, credentials, machine identifiers, or absolute local paths in
  tracked files.
- No PHI, ever, in any form.
- Wording in public-facing text must comply with the claims matrix
  ([docs/CLAIMS.md](docs/CLAIMS.md)).
- The vendored `source material/` tree is reference material and is not
  modified.

## Development setup

Pipeline code does not exist yet; environment and test instructions will land
with the first scaffold packet (EP-2) and be documented here. The stack is
locked in [roadmap/architecture.md](roadmap/architecture.md) (Python 3.12+ /
uv on native Windows, GeoPandas with pyogrio, DuckDB, r5py).

## Licensing of contributions

Code and text contributions are accepted under the repository's MIT license.
