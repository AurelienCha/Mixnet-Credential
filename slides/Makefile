# Makefile for LaTeX Beamer slides compilation

# Main source file
SOURCE := main.tex
PDF := main.pdf

# LaTeX compiler
LATEXMK := latexmk
PDFLATEX := pdflatex

# Compilation flags
LATEXMK_FLAGS := -pdf -interaction=nonstopmode

# Clean file patterns
CLEAN_PATTERNS := *.aux *.log *.out *.nav *.snm *.toc *.fdb_latexmk *.fls *.synctex.gz text/*.aux

.PHONY: all clean distclean compile view help

# Default target
all: compile

# Compile the slides
compile: $(PDF)

$(PDF): $(SOURCE) text/*.tex tikz-preamble.tex schema/*.tex
	$(LATEXMK) $(LATEXMK_FLAGS) $(SOURCE)

# View the PDF (requires xdg-open or similar)
view: $(PDF)
	@command -v xdg-open >/dev/null 2>&1 && xdg-open $(PDF) || open $(PDF) || echo "Please open $(PDF) manually"

# Clean auxiliary files
clean:
	rm -f $(CLEAN_PATTERNS)

# Deep clean - remove everything including PDFs
distclean: clean
	rm -f $(PDF) "main copy.pdf"

# Help target
help:
	@echo "Available targets:"
	@echo "  make compile       - Compile LaTeX to PDF"
	@echo "  make view          - Compile and open PDF"
	@echo "  make clean         - Remove auxiliary files"
	@echo "  make distclean     - Remove all generated files including PDFs"
	@echo "  make all           - Compile slides (default)"
	@echo "  make help          - Show this help message"
