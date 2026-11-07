# Review record -- feature/restyle-fluent-artifacts

- Head: 14ceb35f6eb854fee9ddf7645d0655e108172f59
- Branch: `feature/restyle-fluent-artifacts`
- Date: 2026-11-07
- Scope: EPIC-018 story 03. Fluent Explorer and the Artifact library cards are restyled to ADR-019 and the Lux tokens, reusing `styles/form-styles.ts`.
  - The 38 inline `style=` attributes became classes.
  - Five contrast failures are fixed.
  - Touch targets on phones are 40px.
  - The modal and proofs styles moved to `now-demo-catalog-modal-styles.ts`.
  - There is no behaviour or API change.
- Process: top-tier implementer; one Sonnet adversarial review.
  - No BLOCKING. 1 MAJOR: the new no-sideways-scroll assertion only checked the document, while both screens scroll internally, so overflow inside them could never be detected.
  - MINOR:
    - the deploy and clone dialog buttons became 36x40 through `formStyles`;
    - two hover states fell below AA (3.58 and 4.41);
    - the proof links were under 40px on phones;
    - the copy button covered code;
    - the "every screen is restyled" claims overreached.
  - Fixed (d5a9627):
    - `expectNoSidewaysScrollIn` walks the host and its shadow trees, excluding the frames meant to scroll sideways by selector;
    - the dialog icon and close buttons are 40x40 on phones, with a shared `modal-close` class;
    - the two hover states are now 5.79 and 6.0;
    - the proof links have `min-height`, and a top row is reserved for the copy button;
    - ADR-019 and PRD-002 name the screens that are done and the ones still to restyle.

## Verified

- tsc, the build and file sizes pass; the explorer styles file is 499 lines.
- Every `var(--...)` is defined in lux-theme.css.
- Template diffs only swap classes (reviewed line by line), and the e2e selectors still match.
- Playwright and the screenshot pass run in this branch's gate.

## Not done (follow-ups)

- Still to restyle: the Settings Instances buttons (`admin-shared-styles`), the admin panel canvas, and the share, clone and deploy dialogs (inline styles, 6px inputs).
