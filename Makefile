
# Testing
# --------------------------------------------------------------------------------

test:
	py.test -m "not slow_test" hoboken/tests

test_all:
	py.test hoboken/tests

test_cov:
	py.test --cov-report term-missing --cov-config .coveragerc --cov hoboken hoboken/tests

test_tox:
	tox

test_deps:
	pip install -r requirements.txt

get_version:
	git tag | tail -n 1

upload:
	python setup.py sdist upload


# Dependencies.
deps: user_agent
	echo 'Dependencies updated!'

user_agent:
	rm hoboken/objects/mixins/ua_regexes.yaml
	curl -o hoboken/objects/mixins/ua_regexes.yaml https://raw.github.com/tobie/ua-parser/master/regexes.yaml
