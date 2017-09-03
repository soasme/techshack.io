init-env:
	python3 -m venv venv

source-env:
	source venv/bin/activate

install-dependencies:
	pip install -r requirements.txt

deploy:
	bash -ac '. ./.env; fab deploy'
