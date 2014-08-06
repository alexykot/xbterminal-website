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

        $.stellar({
            horizontalScrolling: false,
            verticalOffset: -150
        });

    };
    return {init: init};
}());

$(function () {
    Landing.init();
});
