var Verification = (function () {
    'use strict';
    var init = function () {
        $('input[type="file"]').fileupload({
            url: $(this).closest('form').attr('action'),
            dataType: 'json',
            dropZone: $(this).closest('.file-dd'),
            done: function (e, data) {
                var fileList = $('#' + data.fileInput.attr('id'))
                    .closest('.file-widget')
                    .find('.file-uploaded').empty();
                var icon = $('<a/>').addClass('glyphicon glyphicon-remove file-remove');
                $('<li/>').text(data.result.file)
                    .append(icon).appendTo(fileList);
            }
        });
        $(document).on('click', '.file-remove', function () {
            $(this).closest('li').remove();
        });
    };
    return {init: init};
}());

$(function () {
    Verification.init();
});
