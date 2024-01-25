from django import template
from urllib.parse import urlencode, parse_qs

register = template.Library()

@register.filter
def remove_page_param(request):
    query_params = parse_qs(request.GET.urlencode())
    query_params.pop('page', None)  # Remove 'page' parameter
    return urlencode(query_params, doseq=True)
