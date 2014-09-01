var Base = (function () {
    'use strict';

    var clearFormErrors = function () {
        $('.form-group')
            .removeClass('has-error')
            .removeClass('has-success')
            .find('.help-block').remove();
    };
    var showFormErrors = function (formErrors) {
        clearFormErrors();
        $('.form-group').addClass('has-success');
        for (var fieldName in formErrors) {
            var formGroup = $('[name="' + fieldName + '"]').closest('.form-group');
            formGroup.removeClass('has-success').addClass('has-error');
            $('<div/>', {
                class: 'help-block',
                html: formErrors[fieldName].join('<br>')
            }).appendTo(formGroup);
        }
    };

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
    return {
        clearFormErrors: clearFormErrors,
        showFormErrors: showFormErrors,
        init: init
    };
}());

$(function () {
    Base.init();
});
