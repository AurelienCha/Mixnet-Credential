
.PHONY: main.pdf

all: main.pdf

main.pdf:
	latexmk -pdf main.tex

spelling:
	ispell -t -b -d american -p ./index.dict *.tex Texts/*.tex

clean:
	latexmk -c -pdf main.tex

distclean:
	latexmk -C -pdf main.tex


