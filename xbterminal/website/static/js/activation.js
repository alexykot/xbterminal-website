var Activation = (function () {
    'use strict';

    // checkUrl and redirectUrl are defined in template

    var checkActivation = function () {
        setInterval(function () {
            $.ajax({
                url: checkUrl
            }).done(function (data) {
                if (data.status === 'active') {
                    window.location = redirectUrl;
                }
            });
        }, 2000);
    };

    var init = function () {
        checkActivation();
    };

    return {init: init};
}());

$(function () {
    Activation.init();
});
