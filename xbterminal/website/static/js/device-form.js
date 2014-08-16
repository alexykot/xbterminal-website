var Device = (function () {
    'use strict';
    var init = function () {
        var paymentProcessing = $('[name="payment_processing"]');
        var percent = $('[name="percent"]');
        var bitcoinAddress = $('[name="bitcoin_address"]');

        percent.percentWidget();

        paymentProcessing.on('change', function () {
            var percentSlider = $('#percent-slider');
            var ppValue = $(this).val();
            if (ppValue == 'keep') {
                percent.val('0');
                percentSlider.slider('value', 0);
                bitcoinAddress.attr('disabled', false);
            } else if (ppValue == 'partially') {
                if (percent.val() == '0' || percent.val() == '100') {
                    percent.val('50');
                    percentSlider.slider('value', 50);
                }
                bitcoinAddress.attr('disabled', false);
            } else if (ppValue == 'full') {
                percent.val('100');
                percentSlider.slider('value', 100);
                bitcoinAddress.attr('disabled', true);
            }
        });
        paymentProcessing.filter(':checked').trigger('change');

        percent.on('change', function () {
            var percentValue = $(this).val();
            var ppValue;
            if (percentValue == '0') {
                ppValue = 'keep';
            } else if (percentValue == '100') {
                ppValue = 'full';
            } else {
                ppValue = 'partially';
            }
            if (paymentProcessing.filter(':checked').val() != ppValue) {
                paymentProcessing.filter('[value="' + ppValue + '"]').click();
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
