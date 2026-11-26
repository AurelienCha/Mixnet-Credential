.DEFAULT_GOAL := all

.PHONY: all setup rm_tmp_files clean help

# Files required for the trusted setup
SETUP_FILES := pot10_beacon.ptau circuit_final.zkey

# Files required to generate a proof
PROVER_FILES := circuit_js circuit.r1cs

# Files required to verify a proof
VERIFIER_FILES := verification_key.json public.json proof.json

# Temporary files
TMP_FILES = $(filter-out $(SETUP_FILES),$(wildcard *.ptau *.zkey))
TMP_FILES += input.json witness.wtns


all: 
	clean
	run 
	@$(MAKE) --no-print-directory rm_tmp_files

run: ## Run the trusted setup
	./run.sh

rm_tmp_files: ## Remove temporary files while preserving setup files
	@echo "Removing temporary files..."
	@rm -f -- $(TMP_FILES)

clean: rm_tmp_files ## Remove all generated files and directories
	@echo "Removing generated files..."
	@rm -rf -- $(SETUP_FILES) $(PROVER_FILES) $(VERIFIER_FILES)

help: ## Display available targets
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_]+:.*## / \
		{printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)