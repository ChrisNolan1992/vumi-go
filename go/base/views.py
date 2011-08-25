from django.contrib.auth.decorators import login_required
from django.template.context import RequestContext
from django.shortcuts import render_to_response

@login_required
def home(request):
    return render_to_response('home.html', {
    }, context_instance=RequestContext(request))