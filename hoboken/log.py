from __future__ import absolute_import

import logging
import logging.config
import logging.handlers


if hasattr(logging, 'NullHandler'):             # pragma: no cover
    NullHandler = logging.NullHandler
else:                                           # pragma: no cover
    from hoboken.packages.logutils import NullHandler


if hasattr(logging.config, 'dictConfig'):       # pragma: no cover
    dictConfig = logging.config.dictConfig
else:                                           # pragma: no cover
    from hoboken.packages.logutils.dictconfig import dictConfig


if hasattr(logging.handlers, 'QueueHandler'):   # pragma: no cover
    QueueHandler = logging.handlers.QueueHandler
else:                                           # pragma: no cover
    from hoboken.packages.logutils.queue import QueueHandler


Logger = logging.getLoggerClass()


class DebugLogger(Logger):
    app = None

    def getEffectiveLevel(self):
        if self.level == logging.NOTSET and self.app and self.app.debug:
            return logging.DEBUG
        return Logger.getEffectiveLevel(self)


class InjectingFilter(logging.Filter):
    def __init__(self, app):
        self.app = app

    def filter(self, record):
        record.app_name = self.app.name

        request = self.app.request
        if request:
            record.request = request
            record.method = request.method
            # TODO: set more here?

        response = self.app.response
        if response:
            record.response = response

        return True
