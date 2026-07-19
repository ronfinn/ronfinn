# Optional contribution snake

This feature is intentionally excluded from the default profile because the
locally generated activity chart is more aligned with a senior scientific
and data-strategy portfolio.

To enable the snake:

1. Copy `contribution-snake.yml` into `.github/workflows/`.
2. Commit and push.
3. Run the workflow manually once.
4. Add this to `README.md`:

```html
<picture>
  <source
    media="(prefers-color-scheme: dark)"
    srcset="https://raw.githubusercontent.com/ronfinn/ronfinn/output/github-contribution-grid-snake-dark.svg"
  >
  <source
    media="(prefers-color-scheme: light)"
    srcset="https://raw.githubusercontent.com/ronfinn/ronfinn/output/github-contribution-grid-snake.svg"
  >
  <img
    alt="Contribution graph animation"
    src="https://raw.githubusercontent.com/ronfinn/ronfinn/output/github-contribution-grid-snake.svg"
    width="100%"
  >
</picture>
```
