var Activation = (function () {
    'use strict';

    // checkUrl and redirectUrl are defined in template

    var checkActivation = function () {
        $.ajax({
            url: checkUrl
        }).done(function (data) {
            if (data.status === 'activation_in_progress') {
                $('.activation-in-progress').show();
                $('.activation-error').hide();
            } else if (data.status === 'activation_error') {
                $('.activation-in-progress').hide();
                $('.activation-error').show();
            } else if (data.status === 'active') {
                window.location = redirectUrl;
            }
        });
    };

    var init = function () {
        checkActivation();
        setInterval(checkActivation, 2000);
    };

    return {init: init};
}());

$(function () {
    Activation.init();
});
