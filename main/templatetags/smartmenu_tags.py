import re
from django import template

register = template.Library()


@register.filter
def extract_value(string):
    """extract `value out of strings like:
        <input checked="checked" id="id_languages_0" name="languages" type="checkbox" value="1" />
    """
    pat = re.compile('.*value="(\d+)"')
    result = pat.match(string)
    if not result:
        return None
    return result.groups()[0]
