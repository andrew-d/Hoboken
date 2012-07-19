Hoboken
=======

[![Build Status](https://secure.travis-ci.org/andrew-d/Hoboken.png?branch=master)](http://travis-ci.org/andrew-d/Hoboken)

Hoboken is a Sinatra-like web framework for Python.  It attempts to make writing simple web applications both easy, but also provide enough power to accomplish more complex things.

Currently, Hoboken is in alpha.  Ther are plenty of tests, but documentation is sorely lacking, and there are currently no real "examples" of how to use it.

That said, here's a simple "hello world" application:

    from hoboken import HobokenApplication

    app = HobokenApplication(__name__)

    @app.get("/")
    def index(request, response):
        return 'Hello world!'

And here's another application that demonstrates a few more of Hoboken's capabilities:

    from hoboken import HobokenApplication

    app = HobokenApplication(__name__)

    @app.get("/greet/:name")
    def greeting(request, response):
        name = request.urlvars['name']
        response.json_body = {
            "greeting": "Hello {0}!".format(name)
        }

You can then host this using any WSGI server (since Hoboken applications are WSGI applications).  There's also a built-in test server, so if we use this to test our application: `app.test_server(port=8080)`, we can do this:

    $ curl -ik http://localhost:8080/greet/John
    HTTP/1.0 200 OK
    Date: Thu, 19 Jul 2012 09:59:23 GMT
    Server: WSGIServer/0.1 Python/2.7.3
    Content-Type: text/html; charset=UTF-8
    Content-Length: 26

    {"greeting":"Hello John!"}


And there you go!  Some simple demonstrations of how Hoboken works.


Miscellanea
-----------

Hoboken is licensed under the Apache license, and is created and developed by Andrew Dunham.
