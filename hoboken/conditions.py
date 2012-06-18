from __future__ import absolute_import
from functools import wraps


def condition(condition_callable):
    def conditional_decorator(func):
        if func.func_dict.get('hoboken.wrapped', False):
            func.func_dict['hoboken.add_condition'](condition_callable)
        else:
            if 'hoboken.conditions' in func.func_dict:
                func.func_dict['hoboken.conditions'].append(condition_callable)
            else:
                func.func_dict['hoboken.conditions'] = [condition_callable]

        @wraps(func)
        def internal(req, resp):
            return func(req, resp)

        return internal

    return conditional_decorator


def hoboken_wrapper(func):
    def add_condition(condition):
        print "Adding condition: %r" % (condition,)

    if 'hoboken.conditions' in func.func_dict:
        for c in func.func_dict['hoboken.conditions']:
            add_condition(c)

        del func.func_dict['hoboken.conditions']

    func.func_dict['hoboken.add_condition'] = add_condition
    func.func_dict['hoboken.wrapped'] = True

    @wraps(func)
    def internal(req, resp):
        return func(req, resp)

    return internal
