// Initialize tooltips
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
  return new bootstrap.Tooltip(tooltipTriggerEl)
})
console.log("Executing the Script")

window.addEventListener("load", function () {
    // do things after the DOM loads fully
    console.log("Everything is loaded");

    function sendPing() {
        let arr = new Uint8Array([1]);
        tosend = arr.buffer;
        ws.send(tosend);
    }

    const nIntervID = setInterval(sendPing, 10000);

    let button = document.getElementById('blocked');

    var hostname = window.location.hostname;
    if (window.location.port != 80 && window.location.port != 443) {
        hostname = hostname + ":" + window.location.port;
    }

    var websocketname = "ws";
    if (window.location.protocol == "https:") {
        websocketname = websocketname + "s";
    }

    var wsaddr = websocketname + "://" + hostname + "/pairingws/" + button.dataset.id;
    var ws = new WebSocket(wsaddr);
    ws.onmessage = function(event) {
        connection_success = event.data;
        var arrayPromise = new Promise(function(resolve) {
            var reader = new FileReader();

            reader.onloadend = function() {
                resolve(reader.result);
            };

            reader.readAsArrayBuffer(connection_success);
        });

        arrayPromise.then(function(array) {
            const typedArray = new Uint8Array(array);
            const finalArray = Array.from(typedArray);
            var identifier = finalArray.pop();
            console.log(identifier);

            if (identifier == 1) {
                var myModal = new bootstrap.Modal(document.getElementById('exampleModalLong'), {
                    backdrop: 'static',
                    keyboard: false
                });
                
                myModal.show();

                let cont = document.getElementById('continue');

                cont.addEventListener('click', function (ev) {
                    window.location.replace('/record')
                });

                var timeleft = 10;
                
                function reduce_time() {
                    if (timeleft > 0) {
                        var message = "We've found you a partner! Please click the button below within " + timeleft + " seconds to begin."
                        document.getElementById('modalText').innerHTML = message;
                        timeleft--;
                    } else {
                        // The user didn't click the button fast enough.
                        console.log("Timed Out");
                        window.location.replace('/error/2')
                    }
                }
                
                const connTimeoutIntvl = setInterval(reduce_time, 1000);

                alert("We've found you a partner!");
                
            } else if (identifier == 0) {
                console.log("Timed Out");
                window.location.replace('/no_partner')
            } else {
                console.log("Received a ping. We're still waiting.")
            }
        });
    };
  });

