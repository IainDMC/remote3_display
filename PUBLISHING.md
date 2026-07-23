# Publishing updates

## First publication

1. Create a **public** GitHub repository named `remote3_display` under `IainDMC`.
2. Use GitHub Desktop to clone the empty repository.
3. Copy every file and folder from this repository package into the clone.
4. In GitHub Desktop, commit with message `Initial HACS release`.
5. Push the commit.
6. On GitHub, open **Actions**.
7. Select **Publish release**, choose **Run workflow**, then run it.

The workflow reads version `1.7.2` from the integration manifest and creates release
`v1.7.2`.

## Future publications

1. Replace the changed repository files with the next package.
2. Commit and push using GitHub Desktop.
3. Open **Actions → Publish release → Run workflow**.
4. HACS will detect the newly published version.

The version in `custom_components/remote3_display/manifest.json` must be newer than
the previous release. Running the workflow twice without changing the version will
fail because that release tag already exists.
