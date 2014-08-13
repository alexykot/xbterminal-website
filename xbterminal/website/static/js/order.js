var Order = (function () {
    'use strict';
    var init = function () {
        setInterval(function () {
            $.ajax({
                url: $('#payment-bitcoin').data('check-url')
            }).done(function (data) {
                if (data.paid === 1) {
                    window.location.href = data.next;
                }
            });
        }, 2000);
    };
    return {init: init};
}());

$(function () {
    Order.init();
});
