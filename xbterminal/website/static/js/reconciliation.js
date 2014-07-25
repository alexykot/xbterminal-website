var Reconciliation = (function () {
    'use strict';
    var init = function () {
        $(document).on('click', '.send-all-button', function (event) {
            event.preventDefault();
            var date = $(this).attr('data-date');
            $('#modal input[name=date]').val(date);
            $('#modal').modal();
        });
        
        $(document).on('click', '.rectime-remove', function (event) {
            event.preventDefault();
            var button = $(this);
            var token = $('.rectime-add [name="csrfmiddlewaretoken"]').val();
            $.ajax({
                url: button.attr('href'),
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': token
                }
            }).done(function (data) {
                button.closest('tr').remove();
            });
        });

        $('#id_time').ptTimeSelect();
    };
    return {init: init};
}());

$(function () {
    Reconciliation.init();
});
