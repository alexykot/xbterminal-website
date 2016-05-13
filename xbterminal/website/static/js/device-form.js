var Device = (function () {
    'use strict';
    var init = function () {
        $('#device-key-select').on('click', function (event) {
            $('#device-key').select();
        });
    };
    return {init: init};
}());

$(function () {
    Device.init();
});
