var PercentWidget = (function () {
    'use strict';
    var init = function () {
        $.fn.percentWidget = function() {
            var select = $(this);
            var slider = $('<div id="percent-slider"></div>')
                .insertAfter(select)
                .slider({
                    min: 1,
                    max: 100,
                    value: select.val(),
                    slide: function(event, ui) {
                        select.val(ui.value);
                    }
                });
            select.change(function() {
                slider.slider('value', select.val());
            });
        };
    };
    return {init: init};
}());