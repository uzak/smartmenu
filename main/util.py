from django.shortcuts import redirect


def get_next_page(request):
    """check session for next argument and if present, redirect to it
    """
    next = request.session.get("next")
    if next:
        del request.session["next"]
        return redirect(next)
