var backspaceKey = 8;
var escapeKey = 27;
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

var paymentInitUrl = location.protocol + '//' + location.host + '/api/v2/payments/';
var getPaymentCheckUrl = function (paymentUid) {
    return paymentInitUrl + paymentUid + '/';
};
var getPaymentReceiptUrl = function (paymentUid) {
    return paymentInitUrl + paymentUid + '/receipt/';
};

var paymentInit = function (form) {
    var amountField = form.find('[name="amount"]');
    var submitButton = form.find('[type="submit"]');
    var amount = parseFloat(amountField.val());
    if (isNaN(amount) || amount < 0.01) {
        showErrorMessage(gettext('invalid amount'));
        return false;
    }
    hideErrorMessage();
    amountField.attr('disabled', true);
    submitButton.prop('disabled', true);
    $.ajax({
        url: paymentInitUrl,
        method: 'POST',
        data: {
            account: form.data('account-id'),
            amount: amount
        }
    }).done(function (data) {
        amountField.attr('disabled', false);
        submitButton.prop('disabled', false);
        form.hide();
        $('.payment-init').show();
        $('.fiat-amount').text(
            parseFloat(data.fiat_amount).toFixed(2));
        $('.mbtc-amount').text(
            (parseFloat(data.btc_amount) * 1000).toFixed(2));
        $('.exchange-rate').text(
            (parseFloat(data.exchange_rate) / 1000).toFixed(3));
        $('.payment-request').
            attr('alt', data.payment_uri).
            qrcode({render: 'div', 'size': 230, 'background': 'white', 'text': data.payment_uri});
        $('.payment-reset').text(gettext('Cancel'));
        paymentCheck(data.uid);
    }).fail(function () {
        showErrorMessage(gettext('server error'));
    });
};

var showErrorMessage = function (errorMessage) {
    $('.error-message').text(errorMessage).show();
    $('.enter-amount [name="amount"]')
        .attr('disabled', false)
        .addClass('error')
        .focus();
    $('.enter-amount [type="submit"]').attr('disabled', false);
};
var hideErrorMessage = function () {
    $('.error-message').hide();
    $('.enter-amount [name="amount"]').removeClass('error');
};

var currentCheck;
var paymentCheck = function (paymentUid) {
    var checkUrl = getPaymentCheckUrl(paymentUid);
    var receiptUrl = getPaymentReceiptUrl(paymentUid);
    currentCheck = setInterval(function () {
        $.ajax({
            url: checkUrl,
        }).done(function (data) {
            if (data.status === 'notified' || data.status == 'confirmed') {
                clearInterval(currentCheck);
                currentCheck = undefined;
                $('.payment-init').hide();
                $('.payment-success').show();
                $('.payment-receipt')
                    .attr('href', receiptUrl)
                    .qrcode({render: 'div', 'size': 150, 'background': 'white', 'text': receiptUrl});
                $('.payment-reset').text('Clear');
            } else if (data.status === 'timeout' || data.status === 'failed') {
                paymentReset();
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
    $('.payment-reset').text('Reset');
    $('.payment-init, .payment-success').hide();
    $('.enter-amount').show();
    $('.enter-amount [name="amount"]')
        .val('0.00')
        .attr('disabled', false)
        .focus();
    $('.payment-request').empty();
    $('.payment-receipt').empty();
};

var lastActivity = new Date().getTime();

$(function () {

    $('.enter-amount [name="amount"]').on('keydown', function (event) {
        var currentAmount = parseFloat($(this).val());
        if (isNaN(currentAmount)) {
            currentAmount = 0;
        }
        var amount;
        if (event.which === backspaceKey) {
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

    $(document).on('keydown', function (event) {
        if (event.which === escapeKey) {
            paymentReset();
        }
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

    if ($('.enter-amount [name="amount"]').val() == '0.00') {
        $('.enter-amount [name="amount"]').focus();
    } else {
        paymentInit($('.enter-amount'));
    }
});
