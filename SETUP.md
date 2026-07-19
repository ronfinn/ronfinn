# Setup guide

This starter is designed for the public `ronfinn/ronfinn` profile repository.

## 1. Copy the files

Copy the contents of this package into the root of the profile repository:

```text
ronfinn/
├── .github/
│   └── workflows/
│       └── update-profile-assets.yml
├── assets/
│   ├── activity-dark.svg
│   ├── activity-light.svg
│   ├── capability-map-dark.svg
│   ├── capability-map-light.svg
│   ├── hero-dark.svg
│   ├── hero-light.svg
│   ├── profile-stats-dark.svg
│   └── profile-stats-light.svg
├── scripts/
│   └── generate_profile_assets.py
└── README.md
```

## 2. Commit and push

```bash
git add .
git commit -m "feat: redesign GitHub profile"
git push
```

## 3. Run the profile workflow

Open the repository on GitHub:

1. Select **Actions**.
2. Select **Update profile assets**.
3. Select **Run workflow**.

The workflow requests only `contents: write`, generates local SVG files and
commits them to the profile repository.

## 4. Troubleshooting workflow permissions

The workflow declares:

```yaml
permissions:
  contents: write
```

If GitHub still refuses the automated commit:

1. Open **Settings**.
2. Open **Actions → General**.
3. Review **Workflow permissions**.
4. Permit the workflow to write repository contents.

## 5. Customise the design

Edit the following files:

- `assets/hero-dark.svg` and `assets/hero-light.svg` for the banner.
- `assets/capability-map-dark.svg` and `assets/capability-map-light.svg`
  for the capability panel.
- `FLAGSHIP_REPOSITORIES` in `scripts/generate_profile_assets.py` to change
  which projects are included in the live portfolio metrics.
- `README.md` for text and project descriptions.

## 6. Optional contribution snake

A contribution-snake example is included under `optional/`. It is not enabled
by default because the main design uses locally generated, professional
activity charts instead.
