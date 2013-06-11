// go.campaign.routing.testHelpers
// ===============================

(function(exports) {
  var routing = go.campaign.routing,
      CampaignRoutingModel = routing.CampaignRoutingModel,
      RoutingScreenView = routing.RoutingScreenView;

  var modelData = {
    campaign_id: 'campaign1',
    channels: [{
      uuid: 'channel1',
      tag: ['apposit_sms', '*121#'],
      name: '*121#',
      description: 'Apposit Sms: *121#',
      endpoints: [{uuid: 'endpoint1', name: 'default'}]
    }, {
      uuid: 'channel2',
      tag: ['sigh_sms', '*131#'],
      name: '*131#',
      description: 'Sigh Sms: *131#',
      endpoints: [{uuid: 'endpoint2', name: 'default'}]
    }, {
      uuid: 'channel3',
      tag: ['larp_sms', '*141#'],
      name: '*141#',
      description: 'Larp Sms: *141#',
      endpoints: [{uuid: 'endpoint3', name: 'default'}]
    }],
    routing_blocks: [{
      uuid: 'routing-block1',
      type: 'keyword',
      name: 'keyword-routing-block',
      description: 'Keyword',
      channel_endpoints: [{uuid: 'endpoint4', name: 'default'}],
      conversation_endpoints: [{uuid: 'endpoint5', name: 'default'}]
    }, {
      uuid: 'routing-block2',
      type: 'keyword',
      name: 'keyword-routing-block',
      description: 'Keyword',
      channel_endpoints: [{uuid: 'endpoint6', name: 'default'}],
      conversation_endpoints: [{uuid: 'endpoint7', name: 'default'}]
    }],
    conversations: [{
      uuid: 'conversation1',
      type: 'bulk-message',
      name: 'bulk-message1',
      description: 'Some Bulk Message App',
      endpoints: [{uuid: 'endpoint8', name: 'default'}]
    }, {
      uuid: 'conversation2',
      type: 'bulk-message',
      name: 'bulk-message2',
      description: 'Some Other Bulk Message App',
      endpoints: [{uuid: 'endpoint9', name: 'default'}]
    }],
    routing_entries: [{
      id: 'endpoint1-endpoint4',
      source: {uuid: 'endpoint1'},
      target: {uuid: 'endpoint4'}
    }]
  };

  var newRoutingScreen = function() {
    return new RoutingScreenView({
      el: '#routing-screen',
      model: new CampaignRoutingModel(modelData)
    });
  };

  // Helper methods
  // --------------

  var setUp = function() {
    $('body').append([
      "<div id='routing-screen'>",
        "<div class='column' id='channels'></div>",
        "<div class='column' id='routing-blocks'></div>",
        "<div class='column' id='conversations'></div>",
      "</div>"
    ].join(''));
  };

  var tearDown = function() {
    Backbone.Relational.store.reset();
    jsPlumb.unbind();
    jsPlumb.detachEveryConnection();
    jsPlumb.deleteEveryEndpoint();
    $('#routing-screen').remove();
  };

  _.extend(exports, {
    setUp: setUp,
    tearDown: tearDown,
    modelData: modelData,
    newRoutingScreen: newRoutingScreen
  });
})(go.campaign.routing.testHelpers = {});