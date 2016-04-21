var Device = (function () {
    'use strict';
    var init = function () {
        var paymentProcessing = $('[name="payment_processing"]');
        var percent = $('[name="percent"]');
        var bitcoinAddress = $('[name="bitcoin_address"]');

        paymentProcessing.on('change', function () {
            var ppValue = $(this).val();
            if (ppValue == 'keep') {
                percent.val('0');
                bitcoinAddress.attr('disabled', false);
            } else if (ppValue == 'full') {
                percent.val('100');
                bitcoinAddress.attr('disabled', true);
            }
        });
        paymentProcessing.filter(':checked').trigger('change');

        $('#device-key-select').on('click', function (event) {
            $('#device-key').select();
        });
    };
    return {init: init};
}());

$(function () {
    Device.init();
});
