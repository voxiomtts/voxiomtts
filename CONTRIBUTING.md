# How to Contribute

## Development Setup
1. Fork the repository
2. Install requirements:
```bash
pip install -r requirements-dev.txt

Code Style

    Follow PEP 8

    Use type hints for new code

    Document public methods with NumPy-style docstrings

Pull Requests

    Reference related issues

    Include screenshots for UI changes


    #### **B. `requirements-dev.txt`**

pytest>=7.0.0
black>=23.0.0
mypy>=1.0.0
pre-commit>=2.20.0


---

### **3. Smart Local → GitHub Sync**
```bash
# Commit your changes with semantic messages
git add .github/ CONTRIBUTING.md requirements-dev.txt
git commit -m "build: add GitHub workflows and docs"

# Push with proper branch protection
git push origin main --follow-tags

# Set branch rules (run these in GitHub UI or CLI):
gh api repos/{owner}/{repo}/branches/main/protection \
  --input - <<EOF
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["Python CI"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "restrictions": null
}
EOF
```

4. Release Checklist

    1. Pre-release Testing
    # Run these locally before tagging
```
    pytest src/
    pre-commit run --all-files


    2. Version Bumping
    Update `__version__` in `src/__init__.py`:

    3. Create Release
    gh release create v1.0.0 --generate-notes
