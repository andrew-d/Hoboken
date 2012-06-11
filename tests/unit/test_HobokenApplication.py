from .context import hoboken


def test_has_http_methods():
    a = hoboken.HobokenApplication("")
    for x in hoboken.HobokenApplication.SUPPORTED_METHODS:
        assert hasattr(a, x.lower())


def test_is_wsgi_application():
    a = hoboken.HobokenApplication("")
    # TODO: Mock WSGI environ and start_application, and test that they're
    # called properly when we make a WSGI request.  Maybe use WebOb to make
    # the request.
