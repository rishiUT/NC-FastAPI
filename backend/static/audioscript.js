// Initialize tooltips
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
  return new bootstrap.Tooltip(tooltipTriggerEl)
})


var connected = false;
let audioIN = { audio: true };
//  audio is true, for recording

// Access the permission for use
// the microphone
navigator.mediaDevices.getUserMedia(audioIN)

    // 'then()' method returns a Promise
    .then(function (mediaStreamObj) {

        // Connect the media stream to the first audio element
        let audio = document.querySelector('audio');
        //returns the recorded audio via 'audio' tag
        
        

        // 'srcObject' is a property which takes the media object
        // This is supported in the newer browsers
        if ("srcObject" in audio) {
            audio.srcObject = mediaStreamObj;
        }
        else {   // Old version
            audio.src = window.URL
                .createObjectURL(mediaStreamObj);
        }

        // It will play the audio
        audio.onloadedmetadata = function (ev) {
            // Play the audio in the 2nd audio element what is being recorded
            audio.play();
        };
        let recording = null;
        let prevAudioLength = 0;

        // Start record
        let record = document.getElementById('btnRecord');
        let send = document.getElementById('btnsend');
        let submit = document.getElementById('btnSubmit');
        let offer = document.getElementById('offerVal');
        let accept = document.getElementById('accept');
        let decline = document.getElementById('decline');
        let prtnrRcdMsg = document.getElementById('partnerRecordingMsg');

        let minutesLeft = 10;
        let secondsLeft = 0;

        let offerSent = false;

        let role = send.dataset.role;
        let is_buyer = (role == "Buyer");
        let is_your_turn = is_buyer;
        let num_messages_sent = 0;
                
        function increase_message_count() {
            num_messages_sent++;
        }
        
        var OfferConfirmModal = new bootstrap.Modal(document.getElementById('OfferConfirmModal'), {
            backdrop: 'static',
            keyboard: false
        })

        var ConnectingModal = new bootstrap.Modal(document.getElementById('ConnectingModal'), {
            backdrop: 'static',
            keyboard: false
        })

        ConnectingModal.show();

        let selfID = "Self";
        let partnerID = "Partner";

        // 2nd audio tag for play the audio
        let playAudio = document.getElementById('audioPlay');
        //let partnerAudio = document.getElementById('partnerAudio');

        // This is the main thing to record
        // the audio 'MediaRecorder' API
        let mediaRecorder = new MediaRecorder(mediaStreamObj);
        // Pass the audio stream 

        let task_descript_toggle = document.getElementById("tdToggle")

        task_descript_toggle.onclick = function() {
            var div = document.getElementById('taskDescription');
            if (div.style.display !== 'none') {
                div.style.display = 'none';
            }
            else {
                div.style.display = 'block';
            }
        };
        
        // Start event
        record.onmousedown = function (ev) {
            console.log(is_your_turn)
            record.classList.remove('btn-primary');
            record.classList.add('btn-success');
            mediaRecorder.start(1000);
            // console.log(mediaRecorder.state);
            let arr = new Uint8Array([9]);
            var tosend = arr.buffer;
            ws.send(tosend);
            pressSound = document.getElementById('pressAudio')
            pressSound.play()
        }

        // Stop event
        record.addEventListener('mouseup', function (ev) {
            record.classList.remove('btn-success');
            record.classList.add('btn-primary');
            send.classList.remove('disabled');
            mediaRecorder.stop();
            // console.log(mediaRecorder.state);
            let arr = new Uint8Array([10]);
            var tosend = arr.buffer;
            ws.send(tosend);
            releaseSound = document.getElementById('releaseAudio')
            releaseSound.play()
        });

        // Send event
        send.addEventListener('click', function (ev) {
            sendMessage()
            send.classList.add('disabled');
            // console.log(mediaRecorder.state);
        });
        // If audio data available then push 
        // it to the chunk array
        mediaRecorder.ondataavailable = function (ev) {
            dataArray.push(ev.data);
            audioLength += 1;
        }

        // Chunk array to store the audio data 
        let dataArray = [];
        let audioLength = 0;
        
        var hostname = window.location.hostname;
        if (window.location.port != 80 && window.location.port != 443) {
            hostname = hostname + ":" + window.location.port;
        }

        var websocketname = "ws";
        if (window.location.protocol == "https:") {
            websocketname = websocketname + "s";
        }

        //Found on StackOverflow
        function Utf8ArrayToStr(array) {
            var out, i, len, c;
            var char2, char3;
        
            out = "";
            len = array.length;
            i = 0;
            while(i < len) {
                c = array[i++];
                switch(c >> 4)
                { 
                case 0: case 1: case 2: case 3: case 4: case 5: case 6: case 7:
                    // 0xxxxxxx
                    out += String.fromCharCode(c);
                    break;
                case 12: case 13:
                    // 110x xxxx   10xx xxxx
                    char2 = array[i++];
                    out += String.fromCharCode(((c & 0x1F) << 6) | (char2 & 0x3F));
                    break;
                case 14:
                    // 1110 xxxx  10xx xxxx  10xx xxxx
                    char2 = array[i++];
                    char3 = array[i++];
                    out += String.fromCharCode(((c & 0x0F) << 12) |
                                ((char2 & 0x3F) << 6) |
                                ((char3 & 0x3F) << 0));
                    break;
                }
            }
        
            return out;
        }

        var wsaddr = websocketname + "://" + hostname + "/audiowspaired/" + send.dataset.id;
        var ws = new WebSocket(wsaddr);

        ws.onopen = function(event) {
            console.log("Opening Websocket")
        }

        ws.onmessage = function(event) {
            incoming_vm = event.data;

            var blob = incoming_vm;

            var arrayPromise = new Promise(function(resolve) {
                var reader = new FileReader();

                reader.onloadend = function() {
                    resolve(reader.result);
                };

                reader.readAsArrayBuffer(blob);
            });

            arrayPromise.then(function(array) {
                const typedArray = new Uint8Array(array);
                const finalArray = Array.from(typedArray);
                var identifier = finalArray.pop();
                console.log(identifier);
                if (identifier == 6) {
                    add_message(partnerID, window.URL.createObjectURL(incoming_vm), finalArray.pop());
                    is_your_turn = true;
                    increase_message_count()
                    alertSound = document.getElementById('alertAudio')
                    alertSound.play()
                    record.classList.remove('disabled');
                } else if (identifier == 7) {
                    self_is_sender = finalArray.pop()
                    if (self_is_sender) {
                        senderID = "Self";
                        is_your_turn = false;
                        record.classList.add('disabled');
                    } else {
                        senderID = "Partner";
                        is_your_turn = true;
                        record.classList.remove('disabled');
                    }
                    increase_message_count()
                    add_message(senderID, window.URL.createObjectURL(incoming_vm), 0)
                } else if (identifier == 8) {
                    var resultstring = Utf8ArrayToStr(finalArray);
                    var amount = parseInt(resultstring);
                    timeleft = 30;
                    offerSent = true;
                    handle_offer(amount, timeleft);
                } else if (identifier == 9) {
                    prtnrRcdMsg.innerHTML = "Your partner is recording...";
                    console.log("The partner is recording...");
                } else if (identifier == 10) {
                    prtnrRcdMsg.innerHTML = "";
                    console.log("The partner has finished recording");
                } else if (identifier == 11) {
                    // This is the time elapsed since the conversation started
                    var resultstring = Utf8ArrayToStr(finalArray);
                    var time_elapsed = parseInt(resultstring);
                    if (time_elapsed > 300) {
                        //The conversation has run too long. Time to time out
                        window.location.replace('/error/2'); //2 = user disconnect error code
                    }
                    
                    while (time_elapsed > 60) {
                        minutesLeft--;
                        time_elapsed -= 60;
                    }

                    if (time_elapsed > secondsLeft) {
                        minutesLeft--;
                        secondsLeft += 60;
                    }

                    secondsLeft -= time_elapsed;

                    let timeRemainingText = "Time Remaining: " + minutesLeft + ":" + formatTimeChunk(secondsLeft);
                    document.getElementById("TimeRemaining").innerHTML = timeRemainingText;
                } else if (identifier == 51) {
                    timeleft = 60
                    var resultstring = Utf8ArrayToStr(finalArray);
                    var amount = parseInt(resultstring);
                    handle_offer(amount, timeleft)
                } else if (identifier == 52) {
                    console.log("Received a response!");
                    OfferConfirmModal.hide();
                    var resultstring = Utf8ArrayToStr(finalArray);
                    var result = parseInt(resultstring);
                    console.log(result);
                    if (result == 0) {
                        document.getElementById('modalText').innerHTML = "Your partner declined the offer.";
                    } else if (result == 1) {
                        document.getElementById('modalText').innerHTML = "Your partner accepted the offer!";
                    }
                    var myModal = new bootstrap.Modal(document.getElementById('exampleModalLong'), {
                        backdrop: 'static',
                        keyboard: false
                    })
                    myModal.show();
                    alertSound = document.getElementById('alertAudio')
                    alertSound.play()
                } else if (identifier == 1) {
                    console.log("Partner connection message received")
                    // This tells us the situation is normal. Make sure the user can send messages.
                    if (is_your_turn) {
                        record.classList.remove('disabled');
                    }
                    submit.classList.remove('disabled');
                    send.dataset.connected = true;
                    document.getElementById('connectingModalText').innerHTML = "Your partner has connected!";
                    document.getElementById('connectionComplete').style.visibility = 'visible';
                    const otherInterval = setInterval(dropCountdown, 1000);
                }else if (identifier > 1 && identifier < 5) {
                    // This is an error code.
                    window.location.replace('/error/' + identifier)
                } else {
                    console.log("Unexpected input");
                }
            });           
        };
        function sendMessage(event) {
            ws.send(recording);
            is_your_turn = false;
            increase_message_count()
            record.classList.add('disabled');
            
            senderID = selfID;
            audioSrc = playAudio.src;
            length = prevAudioLength;
            add_message(senderID, audioSrc, length);
        }

        document.getElementById('connectionComplete').addEventListener('click', function (ev) {
            ConnectingModal.hide();
        });

        // Submit event
        submit.addEventListener('click', function (ev) {
            console.log("Confirming the offer.");
            let val = offer.value;
            console.log(val);

            var closeWindow = function(ev){
                OfferConfirmModal.hide();
            };

            var confirm = document.getElementById("confirmYes");
            var deny = document.getElementById("confirmNo");
        
            var confirmAction = closeWindow;
            var denyAction = closeWindow;

            var confirmListener = function(ev) {
                confirmAction(); //external function call
            };

            var denyListener = function(ev) {
                denyAction(); //external function call
            };

            confirm.addEventListener('click', confirmListener);
            deny.addEventListener('click', denyListener);
            
            // Tests if a value is an integer (source: https://stackoverflow.com/a/14794066)
            // Does so using short-circuiting, and saving a parse operation
            function isInt(value) {
              var x;
              if (isNaN(value)) {
                return false;
              }
              x = parseFloat(value);
              return (x | 0) === x;
            }

            console.log(isInt(val));
            if (num_messages_sent >= 4 && isInt(val)) {
                console.log(val);

                var confirmOffer = function(ev) {
                    console.log("Offer confirmed!");
                    let val = offer.value;
                    val = [val, 3];
                    let data = new Blob(val);
                    ws.send(data);

                    var confirm = document.getElementById('confirmYes');
                    confirm.remove();
                    var deny = document.getElementById('confirmNo');
                    deny.remove();

                    var timeleft = 90
                    document.getElementById('OfferConfirmText').innerHTML = "Offer sent! Waiting for a response...\n";
                    document.getElementById('OfferConfirmText').innerHTML += "Time Remaining: " + timeleft + " seconds";
                    offerSent = true;

                    function handleTimeout() {
                        // Get the number of seconds remaining until timeout
                        timeleft--;
                        if (timeleft < 0) {
                            window.location.replace('/error/3') //3 = partner disconnect error code
                        }
                        timerSound = document.getElementById('timerAudio')
                        timerSound.play()
                        document.getElementById('OfferConfirmText').innerHTML = "Offer sent! Waiting for a response...\n";
                        document.getElementById('OfferConfirmText').innerHTML += "Time Remaining: " + timeleft + " seconds";
                    }

                    const offertimeout = setInterval(handleTimeout, 1000);
                };

                confirmAction = confirmOffer;
                denyAction = closeWindow;

                document.getElementById('OfferConfirmText').innerHTML = "WARNING: You can only send your partner a single offer. Are you sure you want to offer $" + val + "?";
                OfferConfirmModal.show();
            } else if (num_messages_sent < 4) {
                confirmAction = closeWindow;
                denyAction = closeWindow;
                document.getElementById('OfferConfirmText').innerHTML = "WARNING: You can only send an offer once you and your partner have each sent two messages.";
                OfferConfirmModal.show();
            } else {
                confirmAction = closeWindow;
                denyAction = closeWindow;
                document.getElementById('OfferConfirmText').innerHTML = "WARNING: You can only send whole number values. Please enter a whole number.";
                OfferConfirmModal.show();
            }
            
        });

        // Accept event
        accept.addEventListener('click', function (ev) {
            console.log("Offer Accepted!")
            let val = 1;
            val = [val, 4];
            console.log(val);
            let data = new Blob(val);
            if (role == "Seller") {
                ws.send(data)
            }
            window.location.replace('/finish')
        });
        
        // Decline event
        decline.addEventListener('click', function (ev) {
            console.log("Offer Declined.")
            let val = 0;
            val = [val, 4];
            console.log(val);
            let data = new Blob(val);
            ws.send(data)
            window.location.replace('/finish')
        });


        // Convert the audio data in to blob 
        // after stopping the recording
        mediaRecorder.onstop = function (ev) {
            let tosend = new Uint8Array([audioLength, 6]);
            tosend = dataArray.concat(tosend);
            // blob of type mp3
            let audioData = new Blob(tosend,
                { 'type': 'audio/mpeg;' });
            // Save the latest blob to send (if requested)
            recording = audioData

            // Refresh the data array
            dataArray = [];
            prevAudioLength = audioLength;
            audioLength = 0;

            // Creating audio url with reference of created blob named 'audioData'
            let audioSrc = window.URL
                .createObjectURL(audioData);

            // Pass the audio url to the 2nd video tag
            playAudio.src = audioSrc;
        }

        function sendPing() {
            let arr = new Uint8Array([1]);
            tosend = arr.buffer;
            ws.send(tosend);
            if (send.dataset.connected == true) {
                ConnectingModal.hide();
            }
        }

        const nIntervID = setInterval(sendPing, 10000);

        function dropCountdown() {
            if (offerSent == false) {
                if (secondsLeft == 0) {
                    if (minutesLeft == 0) {
                        window.location.replace('/error/2'); //2 = user disconnect error code; not perfect but good enough
                    } else {
                        secondsLeft = 59;
                        minutesLeft--;
                    }
                } else {
                    secondsLeft--;
                }
    
                let timeRemainingText = "Time Remaining: " + minutesLeft + ":" + formatTimeChunk(secondsLeft);
                document.getElementById("TimeRemaining").innerHTML = timeRemainingText;
            }
        }

    })

    // Print any errors 
    .catch(function (err) {
        console.log(err.name, err.message);
    });

function add_message(senderID, audioSrc, length) {
    var currentDate = new Date();
    var row = document.createElement("tr");
    var numChild = document.createElement("th");
    numChild.className += "scope=\"row\"";
    numChild.innerHTML += formatTimeChunk(currentDate.getHours()) + ":" + formatTimeChunk(currentDate.getMinutes()) + ":" + formatTimeChunk(currentDate.getSeconds());
    row.appendChild(numChild)

    var senderChild = document.createElement("td");
    senderChild.innerHTML += senderID;
    row.appendChild(senderChild);

    var buttonChild = document.createElement("td");
    var button = document.createElement('audio');
    button.src = audioSrc;
    button.controls = 'controls';
    button.style.width = '100px';
    button.style.display = 'block';
    buttonChild.appendChild(button);
    row.appendChild(buttonChild);

    var lengthChild = document.createElement("td");
    // Calculate the length of the message in seconds
    lengthMinutes = Math.floor(length/60);
    lengthSeconds = length % 60;
    lengthChild.innerHTML += '' + formatTimeChunk(lengthMinutes) + ":" + formatTimeChunk(lengthSeconds);
    row.appendChild(lengthChild);

    document.getElementById('msgbody').appendChild(row);
}

function formatTimeChunk(timeChunk) {
    if (timeChunk >= 10) {
        return timeChunk;
    }

    return "0" + timeChunk;
}


function handle_offer(amount, timeleft) {
    console.log("Received an offer!");
    offerSent = true;
    document.getElementById('modalText').innerHTML = "Your partner offered $" + amount + "! Will you accept the offer?\n";
    document.getElementById('modalText').innerHTML += "Time Remaining: " + timeleft + " seconds";
    
    var myModal = new bootstrap.Modal(document.getElementById('exampleModalLong'), {
        keyboard: false
    })
    myModal.show();

    function handleTimeout() {
        // Get the number of seconds remaining until timeout
        timeleft--;
        if (timeleft < 0) {
            window.location.replace('/error/2') //2 = user disconnect error code
        }
        timerSound = document.getElementById('timerAudio')
        timerSound.play()
        document.getElementById('modalText').innerHTML = "Your partner offered $" + amount + "! Will you accept the offer?\n";
        document.getElementById('modalText').innerHTML += "Time Remaining: " + timeleft + " seconds";
    }

    const offertimeout = setInterval(handleTimeout, 1000);
}