var Device = (function () {
    'use strict';
    var init = function () {
        var account = $('[name="account"]');
        var bitcoinAddress = $('[name="bitcoin_address"]');

        account.on('change', function () {
            var accountName = $(this).find('option:selected').text();
            if (accountName.indexOf('BTC') !== -1) {
                bitcoinAddress.attr('disabled', false);
            } else {
                bitcoinAddress.attr('disabled', true);
                bitcoinAddress.val('');
            }
        });

        $('#device-key-select').on('click', function (event) {
            $('#device-key').select();
        });
    };
    return {init: init};
}());

$(function () {
    Device.init();
});
