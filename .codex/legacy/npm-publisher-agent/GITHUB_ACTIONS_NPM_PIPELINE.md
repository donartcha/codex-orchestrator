# GitHub Actions npm Publishing Pipeline

This guide documents the recommended Node.js package publication pipeline from GitHub Actions using npm Trusted Publisher.

The goal is to publish reproducible npm releases without storing long-lived npm write tokens in GitHub secrets and without local OTP prompts.

## Recommended Model

Use npm Trusted Publisher with GitHub Actions and OpenID Connect (OIDC).

Benefits:

- No `NPM_TOKEN` is required for publishing.
- npm grants a short-lived publish credential only to the configured workflow.
- npm automatically creates provenance for public packages published from public GitHub repositories.
- Local developer machines do not need npm publish access for normal releases.

## npm Package Setup

Configure Trusted Publisher in the npm package settings.

For a GitHub Actions publisher, npm requires:

- Publisher: `GitHub Actions`
- Organization or user: the GitHub owner, for example `donartcha`
- Repository: the GitHub repository name, for example `OpenLAG`
- Workflow filename: the workflow filename only, for example `publish-npm.yml`
- Environment name: optional; leave blank unless the workflow uses a GitHub deployment environment
- Allowed actions: enable `npm publish`

Important details:

- The workflow filename must include `.yml` or `.yaml`.
- The workflow file must exist under `.github/workflows/`.
- The fields are case-sensitive.
- npm does not fully validate this configuration when it is saved; mistakes usually appear only when publishing.

## GitHub Workflow Requirements

The workflow needs OIDC permissions:

```yaml
permissions:
  contents: read
  id-token: write
```

Trusted Publisher requires npm CLI `11.5.1` or newer and Node.js `22.14.0` or newer. Use Node.js 24 in publishing workflows to avoid runner/npm drift:

```yaml
- uses: actions/checkout@v6

- uses: actions/setup-node@v6
  with:
    node-version: 24
    package-manager-cache: false
    registry-url: https://registry.npmjs.org
```

Disable package-manager cache in release publishing. A release job should favor predictable fresh installs over speed.

## Example Workflow

```yaml
name: Publish npm

on:
  push:
    tags:
      - "v*.*.*"
  workflow_dispatch:
    inputs:
      expected_version:
        description: "Package version to publish, for example 0.4.0"
        required: true

permissions:
  contents: read
  id-token: write

jobs:
  publish:
    name: Publish npm package
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v6

      - uses: actions/setup-node@v6
        with:
          node-version: 24
          package-manager-cache: false
          registry-url: https://registry.npmjs.org

      - name: Check publish runtime
        run: |
          node --version
          npm --version

      - name: Resolve package version
        id: package
        shell: bash
        run: |
          version="$(node -p "require('./package.json').version")"
          echo "version=$version" >> "$GITHUB_OUTPUT"

      - name: Validate requested version
        shell: bash
        run: |
          expected="${{ github.event.inputs.expected_version }}"
          if [ -z "$expected" ] && [[ "${GITHUB_REF_TYPE}" == "tag" ]]; then
            expected="${GITHUB_REF_NAME#v}"
          fi

          if [ -z "$expected" ]; then
            echo "No expected version was provided." >&2
            exit 1
          fi

          if [ "$expected" != "${{ steps.package.outputs.version }}" ]; then
            echo "Expected version $expected but package.json is ${{ steps.package.outputs.version }}." >&2
            exit 1
          fi

      - name: Check npm version availability
        shell: bash
        run: |
          if npm view "$(node -p "require('./package.json').name")@${{ steps.package.outputs.version }}" version --registry=https://registry.npmjs.org >/dev/null 2>&1; then
            echo "Version ${{ steps.package.outputs.version }} is already published." >&2
            exit 1
          fi

      - run: npm ci
      - run: npm run check
      - run: npm pack --dry-run

      - name: Publish to npm
        run: npm publish --access public --registry=https://registry.npmjs.org/
```

For CLI packages, add a smoke test before publish:

```yaml
- run: node bin/<binary>.js --version
```

The `--provenance` flag is optional when Trusted Publisher is active; npm generates provenance automatically. Keeping it is acceptable for clarity, but the OIDC setup is the part that matters.

## Release Flow

1. Prepare the release on a release branch.
2. Update `package.json` version.
3. Update public docs such as `CHANGELOG.md`, `README.md`, `SECURITY.md`, and `CONTRIBUTING.md` when relevant.
4. Run local validation:

```powershell
npm.cmd run check
node bin/<binary>.js --version
npm.cmd pack --dry-run
```

5. Merge the release to the protected stable branch, usually `main`.
6. Create and push the release tag, for example `v0.4.0`, or manually run the workflow with `expected_version=0.4.0`.
7. Let GitHub Actions publish through Trusted Publisher.

Manual workflow trigger:

```powershell
gh workflow run publish-npm.yml --repo <owner>/<repo> --ref main -f expected_version=<version>
```

Tag-based trigger:

```powershell
git tag -a v<version> -m "Release v<version>"
git push origin v<version>
```

## Verification After Publish

Verify the registry:

```powershell
npm.cmd view <package-name> version --registry=https://registry.npmjs.org/
```

For CLI packages, verify an isolated execution:

```powershell
npm.cmd exec --yes --package <package-name>@<version> -- <binary> --version
```

For global CLI tools, also verify a clean global install:

```powershell
npm.cmd uninstall -g <package-name>
npm.cmd install -g <package-name>@<version>
<binary> --version
Get-Command <binary> | Format-List Source,CommandType,Definition
```

If `npm exec` returns an older version, re-test from a clean temporary directory and inspect the published tarball. The package may be reading a cached/global binary or the CLI may be resolving `package.json` incorrectly.

## Troubleshooting

### `EOTP`

The workflow is probably using a classic npm login/session token, or a token without automation permissions.

Preferred fix:

- Use npm Trusted Publisher.
- Remove `NODE_AUTH_TOKEN` and `NPM_TOKEN` from the publish step.

Fallback fix:

- Use an npm automation token through an ephemeral `.npmrc`.
- Never print or commit the token.

### `E404 Not Found - PUT https://registry.npmjs.org/...`

This can mean authentication failed even though the message looks like a missing package.

Check:

- Trusted Publisher is configured on the exact npm package.
- GitHub owner, repository and workflow filename match exactly.
- The workflow has `id-token: write`.
- The runner is GitHub-hosted, not self-hosted.
- Node/npm meet the minimum versions. Use Node.js 24 and npm CLI `11.5.1+`.
- The package `repository.url` in `package.json` points to the same GitHub repository.
- No `NODE_AUTH_TOKEN` from an old secret-based setup is overriding OIDC.

### Package Already Exists

npm versions are immutable. If the workflow says the exact version is already published:

- Do not retry with the same version unless the previous run failed before publish.
- Verify the registry with `npm view`.
- Bump to the next semver version if a new artifact is needed.

### Provenance Was Not Created

Check:

- The repository is public.
- The package is public.
- The publish came from a supported hosted GitHub Actions runner.
- OIDC was used instead of a classic npm token.

## Security Rules

- Do not store npm publish tokens unless Trusted Publisher is unavailable.
- Do not print tokens in logs.
- Do not commit `.npmrc`, `.env`, generated credentials, cache directories, or local troubleshooting artifacts.
- Keep release jobs narrow: validate, pack, publish, verify.
- Prefer protected branches and tags for release triggers.

## Agent Notes

When operating this pipeline as `npm-publisher-agent`:

- Inspect `package.json`, git branch state, remotes, and npm registry state before publishing.
- Run package validation before any publish attempt.
- Prefer GitHub Actions Trusted Publisher over local `npm publish`.
- If a publish fails, verify the registry before retrying.
- Record durable lessons without storing secrets.
