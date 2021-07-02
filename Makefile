checkfiles = main.py manage.py tests/ fastpost/ common/ db/ apps/
black_opts = -l 120 -t py38
py_warn = PYTHONDEVMODE=1
flake8config = .flake8

help:
	@echo "partner development makefile"
	@echo
	@echo  "usage: make <target>"
	@echo  "Targets:"
	@echo  "    up			Updates dependencies"
	@echo  "    deps		Ensure dependencies are installed"
	@echo  "    style		Auto-formats the code"
	@echo  "    check		Checks that build is sane"
	@echo  "    scheck		Style & Checks"
	@echo  "    test		Runs all tests"
	@echo  "    init_mi		init migrations"

up:
	@poetry update

deps:
	@poetry install --no-root

style:
	@poetry run isort --length-sort -src $(checkfiles)
	@poetry run black $(black_opts) $(checkfiles)

check: deps
	@poetry run flake8 --max-line-length=120 --ignore=E131,W503,E203 $(checkfiles)
	@poetry run black --check $(black_opts) $(checkfiles)

scheck: style check

test: deps
	@poetry run py.test -s

init_mi:
	@poetry run alembic init -t async ./migration