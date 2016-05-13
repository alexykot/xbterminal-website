var Registration = (function () {
    'use strict';

    var validateOnServer = function (fieldName, value) {
        var isValid;
        $.ajax({
            type: 'GET',
            url: '/registration/validate/',
            data: {
                field_name: fieldName,
                value: value
            },
            beforeSend: function () {
                $('#loading-image').show();
            },
            success: function (data) {
                isValid = data.is_valid;
            },
            complete: function () {
                $('#loading-image').hide();
            },
            async: false
        });
        return isValid;
    };

    var validator;
    var setUpValidator = function () {
        $.validator.addMethod('emailUnique', function (value, element) {
            return this.optional(element) || validateOnServer('contact_email', value);
        }, gettext('Merchant account with this contact email already exists. Please <a href="/login/">login</a> or <a href="/reset_password/">reset your password</a>.'));

        $.validator.addMethod('companyNameUnique', function (value, element) {
            return this.optional(element) || validateOnServer('company_name', value);
        }, gettext('This company is already registered.'));

        $.validator.addMethod('phone', function (value, element) {
            return this.optional(element) || /^[0-9\s-+().]{5,20}$/.test(value);
        }, gettext('Please enter a valid phone number.'));

        $.validator.addMethod('postCode', function (value, element) {
            return this.optional(element) || /^[a-zA-Z0-9\s-+]{2,10}$/.test(value);
        }, gettext('Please enter a valid post code.'));

        validator = $('#merchant-form').validate({
            showErrors: function (errorMap, errorList) {
                var formErrors = {};
                for (var fieldName in errorMap) {
                    formErrors[fieldName] = [errorMap[fieldName]];
                }
                Base.showFormErrors($('#merchant-form'), formErrors);
            },
            rules: {
                company_name_copy: {
                    required: true,
                    companyNameUnique: true
                },
                company_name: 'companyNameUnique',
                contact_email: 'emailUnique',
                contact_phone: 'phone',
                post_code: 'postCode',
                terms: 'required',
            },
            messages: {
                terms: gettext('Please accept terms & conditions.')
            },
            onsubmit: false,
            onfocusout: false,
            onkeyup: false,
            onclick: false
        });
    };

    var init = function () {
        $('#continue-step-2').on('click', function (event) {
            event.preventDefault();
            if (validator.form()) {
                Base.clearFormErrors($('#merchant-form'));
                $('#registration-step-1').hide();
                $('#registration-step-2').show();
                $('#step span').text('2');
                $('[name="company_name"]').val($('[name="company_name_copy"]').val());
            }
        });
        $('#back-step-1').on('click', function (event) {
            event.preventDefault();
            $('#registration-step-2').hide();
            $('#registration-step-1').show();
            $('#step span').text('1');
        });

        $('#registration-step-1:visible').keypress(function (event) {
            var ENTER_KEY = 13;
            if (event.which === ENTER_KEY) {
                event.preventDefault();
                $('#continue-step-2').click();
            }
        });

        $('#merchant-form').on('submit', function (event) {
            event.preventDefault();
            if (!validator.form()) {
                return false;
            }
            Base.clearFormErrors($('#merchant-form'));
            var form = $(this);
            $.ajax({
                type: 'POST',
                url: form.attr('action'),
                data: form.serialize(),
                beforeSend: function () {
                    $('#loading-image').show();
                }
            }).done(function (data) {
                if (data.result === 'ok') {
                    window.location.href = data.next;
                } else {
                    var minStep = 2;
                    for (var fieldName in data.errors) {
                        var step = form.find('[name="' + fieldName + '"]')
                            .closest('[id^="registration-step"]')
                            .attr('id').slice(-1);
                        if (step < minStep) {
                            minStep = step;
                        }
                    }
                    $('#back-step-' + minStep).click();
                    Base.showFormErrors($('#merchant-form'), data.errors);
                }
            }).fail(function () {
                alert(gettext('Server error!'));
            }).always(function () {
                $('#loading-image').hide();
            });
        });

        setUpValidator();
    };
    return {init: init};
}());

$(function () {
    Registration.init();
});
