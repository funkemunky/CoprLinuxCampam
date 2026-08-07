.PHONY: srpm

outdir ?= .
spec ?= linuxcampam.spec

srpm:
	if command -v rpkg >/dev/null 2>&1; then \
		rpkg srpm --outdir "$(outdir)"; \
	else \
		./scripts/make-srpm.sh --output-dir "$(outdir)" --spec "$(spec)"; \
	fi


