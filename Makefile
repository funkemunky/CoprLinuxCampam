.PHONY: srpm clean

OUTPUT_DIR ?= .

srpm:
	python3 scripts/make-srpm.py --output-dir "$(OUTPUT_DIR)"

clean:
	rm -rf .build build resultdir *.src.rpm

