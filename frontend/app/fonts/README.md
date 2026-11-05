Font files for the app, loaded with `next/font/local` in `app/layout.tsx`. Keeping them in the repo means
builds never need to reach Google Fonts (a failing download there used to break CI) and the fonts work offline.

All are the Latin subsets from Google Fonts, under the SIL Open Font License 1.1:

- `atkinson-hyperlegible-400.woff2`, `atkinson-hyperlegible-700.woff2`: Atkinson Hyperlegible (body text)
- `fraunces.woff2`, `fraunces-italic.woff2`: Fraunces, variable weight 500-700 (headings)
- `lexend.woff2`: Lexend, variable weight 100-900 (easy-read mode)
