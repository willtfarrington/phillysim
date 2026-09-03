# Vendored: MapLibre GL JS 6.7.0

Copied unmodified from the npm package `maplibre-gl@6.7.0`
(`https://registry.npmjs.org/maplibre-gl/-/maplibre-gl-6.7.0.tgz`) on
2026-09-02, so the built site loads its map library from its own origin and
makes no runtime request to any other host (roadmap/architecture.md "Static
site"; ADR-0005). License: BSD-3-Clause (`LICENSE.txt`, unchanged). The three
`.mjs` files must stay side by side: the main module resolves the worker
relative to its own URL and both import the shared chunk.

| File | SHA-256 |
|---|---|
| `maplibre-gl.mjs` | `6d35555718b33843d84af1260e70df7b8c9d23daf0aca2ee30297d237f6f0e55` |
| `maplibre-gl-shared.mjs` | `64e24fd71a28f597891c8b9b5ead9623aee0e20c0ff9e7e8e3fd9b3949c52407` |
| `maplibre-gl-worker.mjs` | `742ce5cfac9eb71015e0893e31b7c2bcffdc6e4bd186007a50eb721d693197b5` |
| `maplibre-gl.css` | `8e2dbbab312dc57656fbb76e9fa5308c75c9d7c7ba5808a7d55bcdb64cc813fa` |
| `LICENSE.txt` | `ee5fc05a0677eaf69601d2c7db0d9ecd6cc27c3abc1d0733bc9ed34707cf8ef2` |

`.gitattributes` marks this directory `-text` so the bytes (and the digests
above, which `tests/test_sitebuild.py` checks) are identical on every
platform. To upgrade: `npm pack maplibre-gl@<version>`, copy the same five
files from the tarball, update the version in this file and in
`phillysim.publish.sitebuild.MAPLIBRE_VERSION`, re-record the digests, and
note the bump in the changelog.
