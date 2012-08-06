Hoboken
=======

[![Build Status](https://secure.travis-ci.org/andrew-d/Hoboken.png?branch=master)](http://travis-ci.org/andrew-d/Hoboken)

Hoboken is a Sinatra-like web framework for Python.  It attempts to make writing simple web applications both easy, but also provide enough power to accomplish more complex things.  Hoboken officially supports Python 2.6, 2.7, and 3.2 (as these are the platforms on which WebOb is supported).  Unofficially, the tests pass on Python 3.0 (but *not* 3.1).

Currently, Hoboken is in alpha.  There are plenty of tests (actually, test coverage is 100%), but documentation is somewhat lacking.  That said, here's a simple "hello world" application:

    from hoboken import HobokenApplication

    app = HobokenApplication(__name__)

    @app.get("/")
    def index():
        return 'Hello world!'

And here's another application that demonstrates a few more of Hoboken's capabilities:

    from hoboken import HobokenApplication

    app = HobokenApplication(__name__)

    @app.get("/greet/:name")
    def greeting(name=None):
        app.response.json_body = {
            "greeting": "Hello {0}!".format(name)
        }

You can then host this using any WSGI server (since Hoboken applications are WSGI applications).  There's also a built-in test server, so if we use this to test our application: `app.test_server(port=8080)`, we can do this:

    $ curl -ik http://localhost:8080/greet/John
    HTTP/1.0 200 OK
    Date: Thu, 19 Jul 2012 00:00:00 GMT
    Server: WSGIServer/0.1 Python/2.7.3
    Content-Type: text/html; charset=UTF-8
    Content-Length: 26

    {"greeting":"Hello John!"}

Finally, here's a longer example:

    from __future__ import print_function
    from hoboken import HobokenApplication

    app = HobokenApplication(__name__)

    @app.before("/admin/*")
    def authenticate(path):
        # This runs before the actual route.  TODO: Do some authentication.
        pass

    @app.get("/")
    def index():
        return "Welcome to the app!"

    @app.get("/books/:author/*")
    def get_book(title, author=None):
        return "Looking for book '{0}' by '{1}'".format(title, author)

    @app.post("/books/:author")
    def add_book(author=None):
        return "Added book for '{0}'".format(author)

And there you go!  Some simple demonstrations of how Hoboken works.


Miscellanea
-----------

Hoboken is licensed under the Apache license, and is created and developed by Andrew Dunham.
