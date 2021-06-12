
all:

sdist:
	python3 setup.py sdist

test:
	python3 -m unittest discover -v test_subpub

clean:
	python3 -Bc "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
	python3 -Bc "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__')]"
	-rm -rf *.egg-info/
	-rm -rf dist/
	cd doc && make clean

.PHONY: all sdist test clean
