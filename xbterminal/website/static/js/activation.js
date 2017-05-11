var Activation = (function () {
    'use strict';

    var interval;

    // checkUrl and redirectUrl are defined in template

    var checkActivation = function () {
        $.ajax({
            url: checkUrl
        }).done(function (data) {
            if (data.status === 'activation_in_progress') {
                $('.activation-in-progress').show();
                $('.activation-error').hide();
                $('.activation-success').hide();
                if (!interval) {
                    interval = setInterval(checkActivation, 2000);
                }
            } else if (data.status === 'activation_error') {
                $('.activation-in-progress').hide();
                $('.activation-error').show();
                $('.activation-success').hide();
                clearInterval(interval);
            } else if (data.status === 'active') {
                $('.activation-in-progress').hide();
                $('.activation-error').hide();
                $('.activation-success').show();
                clearInterval(interval);
            }
        });
    };

    var init = function () {
        checkActivation();
    };

    return {init: init};
}());

$(function () {
    Activation.init();
});
