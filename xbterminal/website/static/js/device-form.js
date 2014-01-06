$(document).ready(function(){
    var paymentProcessing = $('[name=payment_processing]');
    var paymentProcessor = $('[name=payment_processor]');
    var percent = $('[name=percent]');
    var apiKey = $('[name=api_key]');
    var bitcoinAddress = $('[name=bitcoin_address]');

    paymentProcessing.change(function(){
        if ($(this).val() == 'keep'){
            paymentProcessor.val('');
            paymentProcessor.attr('disabled', true);
            paymentProcessor.parent().addClass('disabled').removeClass('active');
            percent.attr('disabled', true).val('');
            apiKey.attr('disabled', true);
            bitcoinAddress.attr('disabled', false);
        }
        if ($(this).val() == 'partially'){
            paymentProcessor.attr('disabled', false);
            paymentProcessor.parent().removeClass('disabled');
            percent.attr('disabled', false);
            apiKey.attr('disabled', false);
            bitcoinAddress.attr('disabled', false);
        }
        if ($(this).val() == 'full'){
            paymentProcessor.attr('disabled', false);
            percent.attr('disabled', true).val('100');
            paymentProcessor.parent().removeClass('disabled');
            apiKey.attr('disabled', false);
            bitcoinAddress.attr('disabled', true);
        }
    });
    paymentProcessing.filter(':checked').trigger('change');
});