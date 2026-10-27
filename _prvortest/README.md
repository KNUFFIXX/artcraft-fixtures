# _prvortest

Pre-test of open pull requests in the ArtCraft projects against the fixtures in this repository.
Copy of the scripts from the private testing setup (`ac/prvortest/`); run by the workflow
[`.github/workflows/prvortest.yml`](../.github/workflows/prvortest.yml) on a GitHub-hosted runner.

- Started only by hand (`workflow_dispatch`, needs write access to this repository); never by a pull request.
- The workflow has no token permissions (`permissions: {}`) and no secrets. The pull request is cloned anonymously,
  built with `cargo build --release -p <app>-cli` and checked with `checks/<app>.py`.
- The result (`<app>-pr<n>-<sha7>.json` and a comment draft) is uploaded as a workflow artifact. Nothing is posted.

Usage: `pr_vortest.sh <app> <pr-number|main> [--head <sha>] [--repo <owner/name>] [--fixtures <dir>] [--issue <n>]... [--baseline] [--results <dir>] [--jobs <n>]`
