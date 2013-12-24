jQuery(document).ready(function() {

	$("button.order-terminal, a.demo-video").click(function() {
		$.fancybox({
			'padding'		: 0,
			'autoScale'		: true,
			'transitionIn'	: 'none',
			'transitionOut'	: 'none',
			'title'			: this.title,
			'href'			: $(this).data('href').replace(new RegExp("watch\\?v=", "i"), 'v/'),
			'type'			: 'swf',
			'swf'			: {
			'wmode'				: 'transparent',
			'allowfullscreen'	: 'true'
			}
		});

		return false;
	});



});
