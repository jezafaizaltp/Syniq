# Reviewing the Malayalam (and Hindi) wording

All Malayalam and Hindi in SYNiq was written by Claude and has not yet been read by a native-speaking teacher. The
owner speaks Malayalam and reviews it. The review happens in one Excel workbook, and the corrections are read back
into the code automatically.

## Make the workbook

```
cd backend
python -m tools.malayalam_review --out /tmp/syniq-malayalam-review.xlsx                 # Malayalam
python -m tools.malayalam_review --lang hi --out /tmp/syniq-hindi-review.xlsx           # Hindi
python -m tools.malayalam_review --new-since <git ref> --out /tmp/new.xlsx              # newest questions first, in yellow
```

Two sheets:

- **Questions**: every question in a Malayalam (or Hindi) pack: prompt, choices, answer, hints, solution and the
  mistake tips it uses. A hidden column holds each question's id; don't delete it.
- **App words**: every app button, message and page text, with the English next to it.

## Review it

Change the wording right in the cell. For anything you're not sure how to fix, write in the **Note** column instead.
Leave a row alone if it's fine. Don't add or remove rows.

## Read it back

```
cd backend
python -m tools.malayalam_review --apply reviewed.xlsx --dry-run --report /tmp/report.md   # see what would change
python -m tools.malayalam_review --apply reviewed.xlsx --report /tmp/report.md             # change the files
```

Edited cells are written back into the content packs, `frontend/lib/i18n.ts` and `backend/app/i18n.py` /
`i18n_hi.py`. A changed answer must still be one of the choices; a changed choice also renames its mistake tip.
Notes and anything that could not be applied go into the report for a person to handle. Then run the tests
(`tests/test_language_review.py`, `tests/test_content_packs.py`, `tests/test_ui_words.py`).

The last workbook sent to the owner: `/mnt/project-files/malayalam/syniq-malayalam-review-2026-11-11.xlsx`
(266 questions, the 64 newest first in yellow, and 770 app words).
