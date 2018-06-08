.PHONY: check-code-style check-pylint check-bandit

check-code-style: check-pylint check-bandit

check-pylint:
	pylint tool || true

check-bandit:
	bandit . -r || true

