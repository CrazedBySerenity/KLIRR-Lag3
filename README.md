# Klirr PoC PWAs

This repo includes a minimal two-PWA demo for QR exchange between a user and vendor.

## PWA demo paths

- User PWA: `PWA/user/index.html`
- Vendor PWA: `PWA/vendor/index.html`

## Local demo (HTTPS required for camera)

Camera access requires a secure context (HTTPS). For phone demos, host the repo on GitHub Pages:

1. Push this repo to GitHub.
2. Enable GitHub Pages for the `main` branch (root).
3. Visit:
   - `https://<org-or-user>.github.io/<repo>/PWA/user/`
   - `https://<org-or-user>.github.io/<repo>/PWA/vendor/`
4. Install each PWA on the corresponding phone from the browser menu.

## Demo flow

1. On the user phone, add a transaction and generate a QR.
2. On the vendor phone, scan the user QR, add vendor transactions, generate a response QR.
3. On the user phone, scan the vendor QR to update the quota summary.

## Notes

- Data is stored locally in the browser via `localStorage`.
- Payloads are plain JSON for PoC speed; no encryption is applied.