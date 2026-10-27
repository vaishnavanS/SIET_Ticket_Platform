from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs):
    """
    Returns the current URL query string with updated key-value parameters.
    Preserves all existing filters and parameters while overriding specified ones (e.g., page).
    Usage: {% query_transform page=page_obj.next_page_number %}
    """
    request = context.get('request')
    if not request:
        return ""
    query = request.GET.copy()
    for k, v in kwargs.items():
        query[k] = v
    return query.urlencode()
