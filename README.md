# N.O.V.A.L.I.S — Organization `.github` Repository

This repository powers the public organization profile at [github.com/N-O-V-A-L-I-S](https://github.com/N-O-V-A-L-I-S), org-wide community health files, and the automated SVG telemetry engine.

## Repository Structure

```text
.github/
├── profile/
│   └── README.md                         # Public organization homepage (rendered on github.com/N-O-V-A-L-I-S)
├── assets/
│   ├── hero_command_{dark,light}.svg     # Animated command header banner
│   ├── architecture_pillars_{dark,light}.svg  # Three-pillar system blueprint
│   ├── org_telemetry_{dark,light}.svg    # Live GitHub Org engineering console
│   └── intelligence_radar_{dark,light}.svg    # Global market & signal radar HUD
├── .github/
│   ├── scripts/novalis_engine.py         # SVG & GitHub Org telemetry generator
│   └── workflows/novalis_telemetry.yml   # 6-hour scheduled CI/CD auto-refresh
├── ISSUE_TEMPLATE/                       # Default org-wide issue forms
├── PULL_REQUEST_TEMPLATE.md              # Default org-wide PR checklist
├── CONTRIBUTING.md                       # Default org-wide contribution guide
├── SECURITY.md                           # Default org-wide security policy
└── CODE_OF_CONDUCT.md                    # Default org-wide code of conduct
```

## Quick Deployment to GitHub

1. Create a **public** repository named **`.github`** inside the `N-O-V-A-L-I-S` organization (`https://github.com/N-O-V-A-L-I-S/.github`).
2. Push this directory to the `main` branch:
   ```bash
   git init -b main
   git add .
   git commit -m "feat: initialize N.O.V.A.L.I.S organization profile & telemetry engine"
   git remote add origin https://github.com/N-O-V-A-L-I-S/.github.git
   git push -u origin main
   ```
3. *(Optional, Recommended for GraphQL Org Commit History)* Add a repository secret named **`ORG_ACCESS_TOKEN`** (Fine-grained PAT with read-only access to org repositories & metadata) under **Settings → Secrets and variables → Actions**. Without it, the workflow automatically uses `GITHUB_TOKEN` and REST fallback.
4. Trigger **Actions → N.O.V.A.L.I.S Telemetry & SVG Engine → Run workflow** to pull live market and organization telemetry immediately.

## Local Preview & Regeneration

```bash
# Offline / Genesis preview (no network required)
python .github/scripts/novalis_engine.py --offline --force

# Live fetch (uses GITHUB_TOKEN or public REST API + live market feeds)
python .github/scripts/novalis_engine.py --org N-O-V-A-L-I-S --force
```
