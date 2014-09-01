var Verification = (function () {
    'use strict';

    var init = function () {
        $('input[type="file"]').fileupload({
            url: $(this).closest('form').attr('action'),
            dataType: 'json',
            dropZone: $(this).closest('.file-dd'),
            submit: function (e, data) {
                Base.clearFormErrors();
                $(this).closest('.file-widget')
                    .find('.progress-bar').css('width', '0px')
                    .closest('.progress').slideDown();
            },
            progress: function (e, data) {
                var progress = parseInt(data.loaded / data.total * 100, 10);
                $(this).closest('.file-widget')
                    .find('.progress-bar').css('width', progress + '%');
            },
            done: function (e, data) {
                if (data.result.errors) {
                    Base.showFormErrors(data.result.errors);
                } else {
                    var fileList = $(this).closest('.file-widget')
                        .find('.file-uploaded').empty();
                    var icon = $('<a/>', {
                        'class': 'glyphicon glyphicon-remove file-remove',
                        'data-path': data.result.path,
                    })
                    $('<li/>').text(data.result.filename)
                        .append(icon).appendTo(fileList);
                }
            }
        });

        $(document).on('click', '.file-remove', function (event) {
            event.preventDefault();
            var button = $(this);
            var form = button.closest('form');
            form.find('.progress').hide();
            var token = form.find('[name="csrfmiddlewaretoken"]').val();
            $.ajax({
                type: 'DELETE',
                url: form.attr('action') + button.data('path') + '/',
                headers: {
                    'X-CSRFToken': token
                }
            }).done(function (data) {
                button.closest('li').remove();
            });
        });

        $('#verification-form').on('submit', function (event) {
            event.preventDefault();
            var form = $(this);
            form.find('[name="submit"]').val(true);
            form.find('.progress').hide();
            $.ajax({
                type: 'POST',
                url: form.attr('action'),
                data: form.serialize(),
                beforeSend: function () {
                    form.find('[name="submit"]').val(false);
                }
            }).done(function (data) {
                if (data.errors) {
                    Base.showFormErrors(data.errors);
                } else {
                    window.location.href = data.next;
                }
            });
        });
    };
    return {init: init};
}());

$(function () {
    Verification.init();
});
