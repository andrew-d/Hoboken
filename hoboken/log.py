from __future__ import absolute_import

import logging
import logging.config
import logging.handlers


if hasattr(logging, 'NullHandler'):
    NullHandler = logging.NullHandler
else:
    from hoboken.packages.logutils import NullHandler


if hasattr(logging.config, 'dictConfig'):
    dictConfig = logging.config.dictConfig
else:
    from hoboken.packages.logutils.dictconfig import dictConfig


if hasattr(logging.handlers, 'QueueHandler'):
    QueueHandler = logging.handlers.QueueHandler
else:
    from hoboken.packages.logutils.queue import QueueHandler


def create_logger(app, name):
    """
    This function creates a logger class for an application.  The created
    class will change the effective logging level based on the application's
    debug setting.
    """
    Logger = logging.getLoggerClass()

    class DebugLogger(Logger):
        def getEffectiveLevel(self):
            if self.level == logging.NOTSET and app.debug:
                return logging.DEBUG
            return Logger.getEffectiveLevel(self)

    log = logging.getLogger(name)
    log.__class__ = DebugLogger

    return log

