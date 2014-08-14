var Base = (function () {
    'use strict';
    var init = function () {
        $('#cookie-notice button').on('click', function (event) {
            event.preventDefault();
            $.cookie('accept_cookies', 'true', {expires: 365});
            $('#cookie-notice').hide();
        });

        if ($.cookie('accept_cookies') !== 'true') {
            $('#cookie-notice').show();
        }
    };
    return {init: init};
}());

$(function () {
    Base.init();
});
