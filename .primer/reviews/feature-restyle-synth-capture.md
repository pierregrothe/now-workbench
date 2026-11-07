# Review record -- feature/restyle-synth-capture

- Head: effb8290516e956d2d84e534fdd7a84ac6956fd1
- Branch: `feature/restyle-synth-capture`
- Date: 2026-11-07
- Scope: EPIC-018 story 02. Synthesizer and Media Capture are restyled to the ADR-019 measurements and Lux tokens:
  - sibling `*-styles.ts` files, plus a shared `web/src/styles/form-styles.ts` (ADR-024);
  - the 17 inline `style=` attributes became classes;
  - green pill buttons, warm chips, rounded fields, and 40px phone touch targets (ADR-030);
  - no behaviour or API change.
- Process: top-tier implementer; one Sonnet adversarial review.
  - Review: no BLOCKING or MAJOR. MINOR findings:
    - AA contrast on the primary button: 4.44 normal and 3.15 on hover;
    - phone fields at about 39px;
    - a partly vacuous phone test and no populated-state check;
    - an undocumented deviation from ADR-019's objective box;
    - a dead class, and doc counts.
  - Fixed (9e613aa):
    - contrast is now 5.5 normal and 4.57 on hover;
    - fields have `min-height: 40px` on phones;
    - the phone test checks every field and asserts how many it found;
    - a populated-gallery no-sideways-scroll test was added;
    - the deviation is noted in the story, the dead class is removed, and the counts are corrected.

## Verified

- tsc, the web build and the file-size cap pass. The review checked every `var(--...)` against lux-theme.css and grepped the old class names across web/e2e: nothing referenced them.
- The template diff is class-only. Handlers, bindings, text, `role="alert"` and the badge classes are unchanged.
- Playwright and the screenshot pass run in this branch's `pr_gate.py check`.

## Not done (follow-ups)

- Fluent Explorer and the Artifact library cards (story 03).
- The populated-gallery test answers the captures GET with `page.route` (precedent: deepfix-demo-pipeline-controller.spec.ts).
