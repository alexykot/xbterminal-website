var Base = (function () {
    'use strict';

    var htmlEscape = function (str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    };

    var clearFormErrors = function (form) {
        form.find('.form-group')
            .removeClass('has-error')
            .removeClass('has-success')
            .find('.help-block').remove();
    };
    var showFormErrors = function (form, errors) {
        clearFormErrors(form);
        form.find('.form-group').addClass('has-success');
        for (var fieldName in errors) {
            var formGroup = form.find('[name="' + fieldName + '"]')
                .closest('.form-group');
            formGroup.removeClass('has-success').addClass('has-error');
            $('<div/>', {
                class: 'help-block',
                html: errors[fieldName].join('<br>')
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
        htmlEscape: htmlEscape,
        clearFormErrors: clearFormErrors,
        showFormErrors: showFormErrors,
        init: init
    };
}());

$(function () {
    Base.init();
});
