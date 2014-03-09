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

    $('.terminal button').on('click', function (event) {
        event.preventDefault();
        alert('Coming soon');
    });
});
