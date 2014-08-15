var Device = (function () {
    'use strict';
    var init = function () {
        var paymentProcessing = $('[name="payment_processing"]');
        var percent = $('[name="percent"]');
        var bitcoinAddress = $('[name="bitcoin_address"]');

        percent.percentWidget();

        paymentProcessing.on('change', function () {
            var percentSlider = $('#percent-slider');
            if ($(this).val() == 'keep') {
                percent.attr('disabled', true).val('');
                percentSlider.slider('disable').slider('value', 1);
                bitcoinAddress.attr('disabled', false);
            } else if ($(this).val() == 'partially') {
                percent.attr('disabled', false);
                percentSlider.slider('enable');
                bitcoinAddress.attr('disabled', false);
            } else if ($(this).val() == 'full') {
                percent.attr('disabled', true).val('100');
                percentSlider.slider('disable').slider('value', 100);
                bitcoinAddress.attr('disabled', true);
            }
        });
        paymentProcessing.filter(':checked').trigger('change');

        percent.on('change', function () {
            if ($(this).val() == '100') {
                paymentProcessing.filter('[value="full"]').click();
            }
        });

        $('#device-key-select').on('click', function (event) {
            $('#device-key').select();
        });
    };
    return {init: init};
}());

$(function () {
    PercentWidget.init();
    Device.init();
});
