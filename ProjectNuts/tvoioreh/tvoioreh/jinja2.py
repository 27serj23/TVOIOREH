"""
Кастомное окружение Jinja2.
Добавляем глобальную функцию url() (reverse) и нужные фильтры.
"""

from jinja2 import Environment
from django.urls import reverse
from django.template.defaultfilters import truncatewords, date


def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'url': reverse,   # теперь в шаблонах можно вызывать url('...')
    })
    env.filters['truncatewords'] = truncatewords
    env.filters['date'] = date
    return env