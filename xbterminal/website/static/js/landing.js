var Landing = (function () {
    'use strict';
    var endsWith = function (string, suffix) {
        return string.indexOf(suffix, string.length - suffix.length) !== -1;
    };

    var makeLinkActive = function (sectionId) {
        $('.header .navbar-nav a').each(function () {
            var link = $(this);
            if (endsWith(link.attr('href'), '#' + sectionId)) {
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

        var sections = $('#about-section, #mobile-section');

        sections.on('scrollSpy:enter', function () {
            makeLinkActive($(this).attr('id'));
        });
        sections.scrollSpy();

        if ($(window).width() > 767) {
            skrollr.init({
                smoothScrolling: false,
                forceHeight: false,
                mobileCheck: function () {
                    return false;
                }
            });
        }

        $(window).on('resize', function () {
            if ($(window).width() <= 767) {
                skrollr.init().destroy();
            }
        });
    };
    return {init: init};
}());

$(function () {
    Landing.init();
});
