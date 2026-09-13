# 發行 · Releasing YueKey

`main` 的 push 及 pull request 會建置、測試 Ubuntu 套件，再產生 Windows ZIP。開發產物存於 GitHub Actions，版本標籤通過所有檢查後才會建立 GitHub Release。

Pushes to `main` and pull requests build/test Ubuntu packages, then the Windows ZIP. Development artifacts are available in GitHub Actions. A version tag publishes a GitHub Release only after both platform jobs pass.

1. Update `VERSION`, `pyproject.toml`, `src/quick_hk/__init__.py`, `CMakeLists.txt`, the schema/data version and installation examples together. Update `docs/RELEASE.md` with the actual release scope.
2. Run the workflow on `main` and check every job. Do not claim Windows desktop/manual microphone checks were run unless recorded.
3. Commit and push the release version. Create its matching tag, for example:

   ```bash
   git tag -a v0.2.0 -m 'YueKey 0.2.0'
   git push origin v0.2.0
   ```

The release job verifies that the tag matches `VERSION`, merges tested artifacts, generates SHA-256 checksums and uploads the five Ubuntu packages, Windows ZIP and corresponding source archive. Only that job has `contents: write`. Pull requests cannot publish releases.

The repository must be public for anonymous free downloads. A private repository's release remains private. No paid service, release token or external package registry is required beyond GitHub Actions; private-repository runner usage is subject to the account's GitHub plan.

所有發行都必須包含 MIT 原創程式授權及第三方通知。請保留字典對應原始資料與建置程式；不可將第三方資料改標為 MIT。

Every release must retain the original-code MIT license and third-party notices. Keep corresponding dictionary sources and build scripts available; third-party material must not be relabeled MIT.
