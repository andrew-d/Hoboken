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
	@git tag | tail -n 1

set_version:
	@echo __version__ = \'$(VER)\' > hoboken/_version.py

upload:
	python setup.py sdist upload


# Dependencies.
# --------------------------------------------------------------------------------
deps: user_agent submodules
	@echo 'Dependencies updated!'

TEST_FILES := additional_os_tests.yaml firefox_user_agent_strings.yaml pgts_browser_list-orig.yaml pgts_browser_list.yaml test_device.yaml test_user_agent_parser.yaml test_user_agent_parser_os.yaml
TEST_RAW_DIR := https://raw.github.com/tobie/ua-parser/master/test_resources/

user_agent:
	@for f in $(TEST_FILES); do curl -o hoboken/tests/objects/ua_tests/$$f $(TEST_RAW_DIR)$$f; done
	curl -o hoboken/objects/mixins/ua_regexes.yaml https://raw.github.com/tobie/ua-parser/master/regexes.yaml

submodules:
	git submodule sync
	git submodule update


