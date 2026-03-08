# Testing Guide

End-to-end test plan covering every layer of the stack: unit → manifest → container → Trivy scan → CI/CD → k8s rollout.

---

## Quick Reference

| Layer | Tool | Command |
|-------|------|---------|
| 1. Unit tests | pytest | `pytest tests/ -v` |
| 2. Manifest validation | kubectl | `kubectl apply -f k8s/ --dry-run=client` |
| 3. Trivy scan (local) | trivy | `trivy image --severity CRITICAL,HIGH --ignore-unfixed ghcr.io/shenyiqinxin/hugging-face-demo:main` |
| 4. Docker smoke test | docker + curl | see Layer 4 below |
| 5. CI/CD end-to-end | GitHub Actions | push to `main` |
| 6. K8s rollout | kubectl | `kubectl -n hf-demo rollout status deploy/hugging-face-demo` |

---

## Layer 1 — Unit Tests (`pytest`)

Tests live in `tests/`. `conftest.py` stubs `transformers`, `gradio`, and `torch` so the BART model never loads and Gradio never launches.

### Setup

```sh
pip install pytest
# or add pytest to requirements.txt and pip install -r requirements.txt
```

### Run

```sh
pytest tests/ -v
```

### What is tested (`tests/test_app.py`)

| Class | Tests |
|-------|-------|
| `TestPredictOutput` | returns `str`, returns correct `summary_text`, handles empty model output |
| `TestPredictCallsModel` | passes input text, `truncation=True`, `max/min_new_tokens`, `no_repeat_ngram_size` |
| `TestPredictEdgeCases` | empty input, 2000-word input, single sentence |

### Expected output

```
tests/test_app.py::TestPredictOutput::test_returns_string PASSED
tests/test_app.py::TestPredictOutput::test_returns_summary_text_field PASSED
tests/test_app.py::TestPredictOutput::test_returns_empty_string_when_model_returns_empty PASSED
tests/test_app.py::TestPredictCallsModel::test_passes_input_text_to_summarizer PASSED
tests/test_app.py::TestPredictCallsModel::test_passes_truncation_flag PASSED
tests/test_app.py::TestPredictCallsModel::test_passes_token_limits PASSED
tests/test_app.py::TestPredictCallsModel::test_passes_no_repeat_ngram_size PASSED
tests/test_app.py::TestPredictEdgeCases::test_empty_string_input PASSED
tests/test_app.py::TestPredictEdgeCases::test_long_input_does_not_raise PASSED
tests/test_app.py::TestPredictEdgeCases::test_single_sentence_input PASSED
10 passed in ...s
```

---

## Layer 2 — Manifest Validation

Validates k8s YAML schema without a live cluster.

```sh
# Basic dry-run (requires kubectl, no cluster needed)
kubectl apply -f k8s/ --dry-run=client
```

```sh
# Stricter schema validation (catches API deprecations)
brew install kubeconform
kubeconform -strict -summary k8s/
```

Expected: no errors, all 4 resources validated.

---

## Layer 3 — Trivy Scan (Local)

### Test A: Happy path — image should be clean

```sh
trivy image \
  --severity CRITICAL,HIGH \
  --ignore-unfixed \
  --exit-code 1 \
  ghcr.io/shenyiqinxin/hugging-face-demo:main
echo "Exit: $?"   # 0 = clean
```

### Test B: Prove the gate blocks a vulnerable image

```sh
trivy image \
  --severity CRITICAL,HIGH \
  --exit-code 1 \
  python:3.8-slim
echo "Exit: $?"   # expect 1 (CVEs found)
```

---

## Layer 4 — Docker Smoke Test

```sh
# Build
docker build -t hf-demo:test .

# Run detached
docker run -d -p 8080:8080 --name hf-demo-test hf-demo:test

# Wait for Gradio startup (~15s for model load)
sleep 15

# Health check
curl -sf http://localhost:8080/ | grep -i gradio && echo "PASS" || echo "FAIL"

# Security check: must not run as root
docker exec hf-demo-test whoami   # must NOT print "root"

# Cleanup
docker stop hf-demo-test && docker rm hf-demo-test
```

---

## Layer 5 — CI/CD End-to-End

### Happy path (scan passes → deploy runs)

```sh
git add .
git commit -m "test: added test and trivy"
git push origin main
```

Watch GitHub → Actions. Expected job sequence:

```
build ✅ → scan ✅ → deploy-selfhosted ✅
```

SARIF results appear under: repo → Security → Code scanning alerts.

### Gate test (scan fails → deploy is skipped)

```sh
git checkout -b test/trivy-gate
# Temporarily edit Dockerfile: change base image to python:3.8-slim
git commit -am "test: vulnerable base to verify Trivy gate"
git push origin test/trivy-gate
# Open a PR against main
```

Expected:

```
build ✅ → scan ❌ → deploy-selfhosted SKIPPED
```

Revert and close the PR after confirming.

---

## Layer 6 — K8s Rollout (kind / local cluster)

```sh
# Deploy
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/

# Wait for rollout
kubectl -n hf-demo rollout status deploy/hugging-face-demo --timeout=3m

# Verify pod is Running with no restarts
kubectl -n hf-demo get pods   # STATUS=Running, READY=1/1
kubectl -n hf-demo get pods \
  -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}'
# expect: 0

# Add DNS entry if not already present
echo "127.0.0.1   hf-demo.local" | sudo tee -a /etc/hosts

# Test via Ingress
curl -sf http://hf-demo.local/ | grep -i gradio && echo "PASS"
```

---

## Recommended Run Order

```
Layer 1 (unit)        ← run on every code change
Layer 2 (manifests)   ← run after editing k8s/
Layer 3 (trivy local) ← run before pushing
Layer 4 (docker)      ← run after Dockerfile changes
Layer 5 (CI/CD)       ← run on push to main / PR
Layer 6 (k8s rollout) ← run after deploy-selfhosted succeeds
```
