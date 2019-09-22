# -*- coding: utf-8 -*-

import datetime

##
# Our own implementation on datetime.datetime.now, in order to override it when we do unit tests
#
def now(timezone):
    return datetime.datetime.now(timezone)