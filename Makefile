# sourcebook. Standard library only; there is nothing to install.
PY ?= python3

.PHONY: help test lint demo demo-tamper install skill clean

help:
	@echo "make test          the 22 acceptance tests, hermetic, no network"
	@echo "make lint          every shipped template through the rule registry"
	@echo "make demo          rebuild examples/demo/answer.html from the local sources"
	@echo "make demo-tamper   build, then break one quote and watch the gate refuse"
	@echo "make install       refresh the checked-in .claude/.agents/.hermes adapters"
	@echo "make clean         drop __pycache__ and the demo scratch workspace"

test:
	$(PY) tests/run.py

lint:
	@for f in templates/*.html; do \
	  printf '%-34s' "$$f"; $(PY) scripts/sb.py lint "$$f" | tail -1; \
	done

demo:
	$(PY) examples/demo/build.py

demo-tamper:
	$(PY) examples/demo/build.py --tamper

skill:
	cp skills/sourcebook/SKILL.md SKILL.md

install: skill
	$(PY) scripts/install.py --harness claude --dest .
	$(PY) scripts/install.py --harness agents --dest .
	$(PY) scripts/install.py --harness hermes --dest .
	rm -rf .sourcebook

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf examples/demo/workspace
