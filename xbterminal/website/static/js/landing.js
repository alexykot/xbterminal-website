var Landing = (function () {
    'use strict';
    var makeLinkActive = function (sectionId) {
        $('.header .menu-block a').each(function () {
            var link = $(this);
            if (link.attr('href') == '/#' + sectionId) {
                link.addClass('active');
            } else {
                link.removeClass('active');
            }
        });
    };

    var init = function () {
        $('#terminal-subscribe-form').on('submit', function (event) {
            event.preventDefault();
            var form = $(this);
            var formMessage = $('#terminal-subscribe-message');
            $.ajax({
                type: 'POST',
                url: form.attr('action'),
                data: form.serialize(),
                beforeSend: function () {
                    form.find('.loading-image').show();
                }
            }).done(function (data) {
                if (data.errors) {
                    formMessage.text('Error!');
                } else {
                    form.hide();
                    formMessage.text('Thank you for joining our mailing list!');
                }
            }).always(function () {
                form.find('.loading-image').hide();
            });
        });

        $(window).on('scroll', function () {
            var header = $('.header');
            var navHeight = header.height();
            if ($(window).scrollTop() > navHeight) {
                if (!header.hasClass('header-fixed')) {
                    header.hide().addClass('header-fixed').fadeIn();
                }
            } else {
                if (header.hasClass('header-fixed')) {
                    header.removeClass('header-fixed');
                }
            }
        });

        var sections = $('#about-section, #terminal-section, \
                          #mobile-section, #web-section');

        sections.on('scrollSpy:enter', function () {
            makeLinkActive($(this).attr('id'));
        });
        sections.scrollSpy();

        skrollr.init({
            smoothScrolling: false,
            forceHeight: false
        });
    };
    return {init: init};
}());

$(function () {
    Landing.init();
});
