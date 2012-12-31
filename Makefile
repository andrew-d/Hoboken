
# Testing
# --------------------------------------------------------------------------------
$(phony test):
	py.test -m "not slow_test" hoboken/tests

$(phony test_all):
	py.test hoboken/tests

$(phony test_cov):
	py.test --cov-report term-missing --cov-config .coveragerc --cov hoboken hoboken/tests

$(phony test_tox):
	tox


