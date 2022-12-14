var Verification = (function () {
    'use strict';

    var init = function () {
        $('input[type="file"]').fileupload({
            url: $(this).closest('form').attr('action'),
            dataType: 'json',
            dropZone: $(this).closest('.file-dd'),
            submit: function (e, data) {
                Base.clearFormErrors($(this).closest('form'));
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
                    Base.showFormErrors($(this).closest('form'), data.result.errors);
                } else {
                    var fileList = $(this).closest('.file-widget')
                        .find('.file-uploaded').empty();
                    var icon = $('<a/>', {
                        'class': 'glyphicon glyphicon-remove file-remove',
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
                url: form.attr('action'),
                headers: {
                    'X-CSRFToken': token
                }
            }).done(function (data) {
                button.closest('li').remove();
            });
        });

        $('#verification-form').on('submit', function (event) {
            event.preventDefault();
            $('.upload-form .progress').hide();
            $.ajax({
                type: 'POST',
                data: $(this).serialize(),
                beforeSend: function () {
                    $('#loading-image').show();
                }
            }).done(function (data) {
                if (data.error) {
                    alert(data.error);
                } else {
                    window.location.href = data.next;
                }
            }).always(function () {
                $('#loading-image').hide();
            });
        });
    };
    return {init: init};
}());

$(function () {
    Verification.init();
});
