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
            var navHeight = $('.header').height();
            if ($(window).scrollTop() > navHeight) {
                $('.header').addClass('fixed');
            } else {
                $('.header').removeClass('fixed');
            }
        });

        var sections = $('#about-section, #terminal-section, \
                          #mobile-section, #web-section');

        sections.on('scrollSpy:enter', function () {
            makeLinkActive($(this).attr('id'));
        });
        sections.scrollSpy();

    };
    return {init: init};
}());

$(function () {
    Landing.init();
});
