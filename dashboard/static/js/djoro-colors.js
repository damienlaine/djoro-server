/* =========================================================
 * djoro-colors.js 
 * =========================================================
 * Copyright 2015 by Thermlabs
 *
 * Defines colors of gauges on dashboard
 * 
 * ========================================================= */
tempStats();

function tempStats(){
	if($('.tempStat')) {		
		$('.tempStat').each(function(){
               var color = $(this).attr("data-color");
						
			if (color == "green") {
				
				$(this).animate({
				            borderColor: "#33ee99"
				        }, 'slow');
				
			} else if (color == "yellow") {
				
				$(this).animate({
				            borderColor: "#eae874"
				        }, 'slow');
				
			} else if (color == "red") {	
				$(this).animate({
				            borderColor: "#ea6666"
				        }, 'slow');
               } else if (color == "blue") {	
				$(this).animate({
				            borderColor: "#9999ff"
				        }, 'slow');
               } 
		});		
	}	
}