$(function () {
    $("a.demo-video").on('click', function () {
        $.fancybox({
            'padding': 0,
            'autoScale': false,
            'transitionIn': 'none',
            'transitionOut': 'none',
            'title': this.title,
            'width': 900,
            'height': 700,
            'href': $(this).data('href').replace(new RegExp('watch\\?v=', 'i'), 'v/'),
            'type': 'swf',
            'swf': {
                'wmode': 'transparent',
                'allowfullscreen': 'true'
            }
        });
        return false;
    });

    $('.front-terminal-image').fractionSlider({
        'transitionIn': 'fade',
        'transitionOut': 'fade',
    });

    $('.terminal button').on('click', function (event) {
        event.preventDefault();
        $.fancybox({
            modal: true,
            content: '<div class="fancy-alert">\
                <p>Coming at the end of May 2014, check back soon!</p>\
                <button class="btn btn-primary" onclick="$.fancybox.close();">OK</button>\
                </div>'
        });
    });

    // ShareThis
    stLight.options({
        publisher: '6ea95e06-4966-45e6-a369-cd0503255bf3',
    });

    $('.subscribe-form').on('submit', function (event) {
        event.preventDefault();
        var form_data = {};
        $(this).find('input').each(function () {
            form_data[$(this).attr('name')] = $(this).val();
        });
        $.ajax({
            type: 'POST',
            url: $(this).attr('action'),
            data: form_data
        }).done(function (data) {
            $.fancybox({
                modal: true,
                content: '<div class="fancy-alert">\
                    <p>Thank you for registering your interest!</p>\
                    <button class="btn btn-primary" onclick="$.fancybox.close();">OK</button>\
                    </div>'
            });
        });
    });
});
