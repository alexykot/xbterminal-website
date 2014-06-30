var backspace = 8;
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
var maxDigits = 9;

var paymentInit = function (form) {
    var amountField = form.find('[name="amount"]');
    var amount = parseFloat(amountField.val());
    if (isNaN(amount) || amount < 0.01) {
        showErrorMessage('invalid amount');
        return false;
    }
    hideErrorMessage();
    amountField.attr('disabled', true);
    $.ajax({
        url: form.attr('action'),
        method: 'POST',
        data: {
            device_key: form.data('device-key'),
            amount: amount
        }
    }).done(function (data) {
        amountField.attr('disabled', false);
        form.hide();
        $('.payment-init').show();
        $('.fiat-amount').text(data.fiat_amount.toFixed(2));
        $('.mbtc-amount').text((data.btc_amount * 1000).toFixed(2));
        $('.exchange-rate').text((data.exchange_rate / 1000).toFixed(3));
        $('.payment-request').
            attr('alt', data.payment_uri).
            attr('src', data.qr_code_src);
        $('.payment-reset').text('Cancel');
        paymentCheck(data.check_url);
    }).fail(function () {
        showErrorMessage('server error');
    });
};

var showErrorMessage = function (errorMessage) {
    $('.error-message').html(errorMessage).show();
    $('.enter-amount [name="amount"]')
        .attr('disabled', false)
        .addClass('error')
        .focus();
};
var hideErrorMessage = function () {
    $('.error-message').hide();
    $('.enter-amount [name="amount"]').removeClass('error');
};

var currentCheck;
var paymentCheck = function (checkURL) {
    currentCheck = setInterval(function () {
        $.ajax({
            url: checkURL
        }).done(function (data) {
            if (data.paid === 1) {
                clearInterval(currentCheck);
                currentCheck = undefined;
                $('.payment-init').hide();
                $('.payment-success').show();
                $('.payment-receipt').
                    attr('alt', data.receipt_url).
                    attr('src', data.qr_code_src);
            }
        });
    }, 2000);
};

var paymentReset = function () {
    if (currentCheck) {
        clearInterval(currentCheck);
        currentCheck = undefined;
    }
    hideErrorMessage();
    $('.enter-amount [name="amount"]')
        .val('0.00')
        .attr('disabled', false)
        .focus();
    $('.payment-reset').text('Reset');
    $('.payment-init, .payment-success').hide();
    $('.enter-amount').show();
};

var lastActivity = new Date().getTime();

$(function () {

    $('.enter-amount [name="amount"]').on('keydown', function (event) {
        var currentAmount = parseFloat($(this).val());
        if (isNaN(currentAmount)) {
            currentAmount = 0;
        }
        var amount;
        if (event.which === backspace) {
            event.preventDefault();
            amount = Math.floor(currentAmount * 10) / 100;
            $(this).val(amount.toFixed(2));
        } else if (event.which in numKeys) {
            event.preventDefault();
            if (currentAmount.toFixed(2).length <= maxDigits) {
                amount = currentAmount * 10 + 0.01 * numKeys[event.which];
                $(this).val(amount.toFixed(2));
            }
        }
    });

    $('.enter-amount').on('submit', function (event) {
        event.preventDefault();
        var form = $(this);
        paymentInit(form);
    });

    $('.payment-reset').on('click', function (event) {
        event.preventDefault();
        paymentReset();
    });

    $(document).on('keydown click', function (event) {
        lastActivity = new Date().getTime();
    });

    // Change amount field type for Android/Apple devices
    if (/android|iphone|ipad|ipod/i.test(navigator.userAgent.toLowerCase())) {
        $('.enter-amount [name="amount"]')
            .attr('type', 'number')
            .attr('min', '0.00')
            .attr('max', '9999999.99')
            .attr('step', '0.01')
            .attr('pattern', '[0-9]*');
    }

    // Reset after 15 minutes of inactivity
    setInterval(function () {
        var now = new Date().getTime();
        if (now - lastActivity > 15 * 60 * 1000) {
            paymentReset();
        }
    }, 5000);
});
