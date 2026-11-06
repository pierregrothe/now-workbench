# ADR-022: Deploying a demo's Fluent app

**Status:** accepted
**Date:** 2026-11-06

## Context

The demo pipeline's deploy step never worked. The problems found while testing on a live
Australia instance (Alectri) were:
- the SDK runner passed credential variables `now-sdk` does not read;
- demo bundles carry Fluent sources but are not SDK projects (no `package.json`);
- one shipped sample's Fluent code was invalid;
- table names did not belong to any application scope.

The owner chose, on 2026-11-06, to generate and deploy a real app rather than keep the step
skipped.

## Decision

- **Credentials** use the SDK's documented non-interactive mode, read from the
  @servicenow/sdk 4.14 sources: `SN_SDK_NODE_ENV=SN_SDK_CI_INSTALL`, `SN_SDK_INSTANCE_URL`,
  `SN_SDK_USER`, `SN_SDK_USER_PWD`. They are passed in the child's environment, never in its
  arguments.
- **One generated project per bundle and vendor.** The scope is `x_<vendor>_<6 hex of the
  bundle id>`. It is unique, at most 18 characters, and the vendor comes from the instance's
  `glide.appcreator.company.code`. The project is created with `now-sdk init` (base template)
  under `<workspace>/sdk-projects/`. Each run regenerates its `src/fluent/` from the bundle.
- **Tables move into the scope.** Every table declared in the bundle's Fluent sources is
  renamed `<scope>_<name without its old x_<vendor>_ prefix>`. The same map is applied to
  the seed records and to the runbook stages' target tables. The bundle itself is never
  rewritten, so the same demo can be deployed to instances with different vendors.
- **Shared toolchain.** `npm install` of the SDK is about 350 MB, so it is installed once in
  `<workspace>/sdk-toolchain`, and each project links its `node_modules` to it.
- **Order and failure.** The steps are build (`now-sdk build`), then `now-sdk install`, then
  seed. A build or install error stops the pipeline with the SDK's message. A bundle that
  already contains `package.json` is installed as it is. A bundle without Fluent sources
  skips deploy. Simulated instances simulate it.

## Consequences

- Deploying installs a scoped application on the instance. Removing it is a manual step on
  the instance (System Applications).
- Property names that embed an old table name are not renamed; they are only names.
