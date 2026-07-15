"""
Кастомное окружение Jinja2.
Добавляем глобальную функцию url() (reverse), фильтры и now().
"""
from jinja2 import Environment
from django.urls import reverse
from django.template.defaultfilters import truncatewords, date
from datetime import datetime


def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'url': reverse,          # чтобы работал url('имя_маршрута', аргументы)
        'now': datetime.now,     # чтобы работал now().year и т.д.
    })
    env.filters['truncatewords'] = truncatewords
    env.filters['date'] = date
    return env
