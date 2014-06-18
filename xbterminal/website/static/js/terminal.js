var backspace = 8;
var enter = 13;
var numKeys = {
    48: 0,
    49: 1,
    50: 2,
    51: 3,
    52: 4,
    53: 5,
    54: 6,
    55: 7,
    56: 8,
    57: 9,
    96: 0,
    97: 1,
    98: 2,
    99: 3,
    100: 4,
    101: 5,
    102: 6,
    103: 7,
    104: 8,
    105: 9
};

var paymentCheck = function (checkURL, successURL) {
    setInterval(function () {
        $.ajax({
            url: checkURL
        }).done(function (data) {
            if (data.paid === 1) {
                window.location.href = successURL;
            }
        });
    }, 2000);
};

$(function () {

    $('.enter-amount [name="amount"]').on('keydown', function (event) {
        event.preventDefault();
        var currentAmount = parseFloat($(this).val());
        var amount;
        if (event.which === enter) {
            $(this).closest('form').submit();
        } else if (event.which === backspace) {
            amount = Math.floor(currentAmount * 10) / 100;
            $(this).val(amount.toFixed(2));
        } else if (event.which in numKeys) {
            amount = currentAmount * 10 + 0.01 * numKeys[event.which];
            $(this).val(amount.toFixed(2));
        }
    });

    $('.enter-amount [name="amount"]').val('0.00').focus();

    if ($('.payment-request').length !== 0) {
        var checkURL = $('.payment-request').data('check-url');
        var successURL = $('.payment-request').data('success-url');
        paymentCheck(checkURL, successURL);
    }
});
