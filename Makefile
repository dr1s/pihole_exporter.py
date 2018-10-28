build:
	python3 setup.py sdist bdist_wheel --universal
clean:
	rm -rf build dist *.egg-info
env:
	pipenv install
upload:
	twine upload dist/*
install:
	python3 setup.py install
release: clean build upload
