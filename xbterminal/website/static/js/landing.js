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
                    form.css('visibility', 'hidden');
                    formMessage.text(gettext('Thank you for joining our mailing list!'));
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
