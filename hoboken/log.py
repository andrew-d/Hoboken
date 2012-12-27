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

