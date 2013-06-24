from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages

from go.channel.forms import CampaignConfigurationForm


@login_required
def index(request):
    raise NotImplementedError("TODO: List channels")


@login_required
def new_channel(request):
    """
    TODO: Clean this thing up and figure out exactly what we need to do here.
    """

    if request.method == 'POST':
        form = CampaignConfigurationForm(request.user_api, request.POST)
        if form.is_valid():
            # TODO: Better validation?
            pool, tag = form.cleaned_data['channel'].split(':')
            if tag:
                got_tag = request.user_api.acquire_specific_tag((pool, tag))
            else:
                got_tag = request.user_api.acquire_tag(pool)
            # TODO: Acquire tag, etc.
            messages.info(request, 'Acquired tag: %r.' % (got_tag,))

            # TODO save and go to next step.
            return redirect('conversations:index')
        else:
            raise ValueError(repr('Error: %s' % (form.errors,)))

    form_config_new = CampaignConfigurationForm(request.user_api)
    return render(request, 'channel/new.html', {
        'form_config_new': form_config_new,
    })