(function(exports) {
    exports.updateClicks = function(shortUrl) {
        var request = new XMLHttpRequest()
        request.onload = function(data) {
            var numClicks = JSON.parse(data.target.responseText).numClicks;
            var shortUrl = JSON.parse(data.target.responseText).shortUrl;
            document.getElementById("clicks-" + shortUrl).innerHTML = numClicks;
        };
        request.open("GET", "/clicks?short_url=" + shortUrl, true);
        request.send();
    };
    window.onload = function() {
        setInterval(function() {
            var shortUrls = document.getElementsByClassName("short_url");
            for (var i = 0; i < shortUrls.length; i++) {
            exports.updateClicks(shortUrls[i].id);
            }
        }, 1000);
    };
})(this);
