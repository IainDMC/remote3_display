# Publishing updates

## First publication

1. Create a **public** GitHub repository named `remote3_display` under `IainDMC`.
2. Use GitHub Desktop to clone the empty repository.
3. Copy every file and folder from this repository package into the clone.
4. In GitHub Desktop, commit with message `Initial HACS release`.
5. Push the commit.
6. On GitHub, open **Actions**.
7. Select **Publish release**, choose **Run workflow**, then run it.

The workflow reads the current version from the integration manifest and creates
the matching `vX.Y.Z` release.

## One-time observer signing setup

Android requires every update to use the same signing key. Keep the signing key
private and backed up; losing it means users must uninstall the observer before
installing a later version.

Before running **Publish release**, add these GitHub repository secrets under
**Settings → Secrets and variables → Actions**:

- `OBSERVER_KEYSTORE_BASE64`: the release keystore encoded as one Base64 string
- `OBSERVER_KEYSTORE_PASSWORD`: the keystore password
- `OBSERVER_KEY_ALIAS`: the key alias
- `OBSERVER_KEY_PASSWORD`: the key password

On Windows, run the included helper from the repository root:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\tools\create-observer-signing-key.ps1
```

It creates the key locally and prints the four GitHub secret values. It does not
upload or commit the key.

Never commit the keystore or these values. The release workflow restores the key
temporarily, builds a signed observer APK, attaches it to the GitHub release, and
then the GitHub runner is discarded.

## Future publications

1. Replace the changed repository files with the next package.
2. Commit and push using GitHub Desktop.
3. Open **Actions → Publish release → Run workflow**.
4. HACS will detect the newly published version.

The version in `custom_components/remote3_display/manifest.json` must be newer than
the previous release. Running the workflow twice without changing the version will
fail because that release tag already exists.
