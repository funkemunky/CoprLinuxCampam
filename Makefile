.PHONY: srpm clean

OUTPUT_DIR ?= .
SPEC ?= linuxcampam.spec

srpm:
	scripts/make-srpm.sh --output-dir "$(OUTPUT_DIR)" --spec "$(SPEC)"

clean:
	rm -rf .build build resultdir *.src.rpm

