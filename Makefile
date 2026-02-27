install:
	pip install --upgrade pip &&\
		pip install -r requirements.txt

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

test:
	python -m pytest -vv

format:
	black *.py

run:
	python main.py

run-uvicorn:
	uvicorn main:app

killweb:
	sudo killall uvicorn

lint:
	pylint --disable=R,C main.py hello.py

all: install lint test
