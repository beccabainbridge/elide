(function(exports) {
    exports.updateClicks = function(shortUrl) {
        var request = new XMLHttpRequest()
        request.onload = function(data) {
            var numClicks = JSON.parse(data.target.responseText).numClicks;
            document.getElementById("clicks").innerHTML = numClicks;
        };
        request.open("GET", "/clicks?short_url=" + shortUrl, true);
        request.send();
    };
    window.onload = function() {
        setInterval(function() {
            var shortUrl = document.getElementById("short_url").innerHTML;
            exports.updateClicks(shortUrl);
        }, 1000);
    };
})(this);
