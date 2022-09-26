// Initialize tooltips
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
  return new bootstrap.Tooltip(tooltipTriggerEl)
})

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

        // Start record
        let record = document.getElementById('btnRecord');
        let send = document.getElementById('btnsend');
        let submit = document.getElementById('btnSubmit');
        let offer = document.getElementById('offerVal');
        let accept = document.getElementById('accept');
        let decline = document.getElementById('decline');

        let selfID = "Self";
        let partnerID = "Partner";

        // 2nd audio tag for play the audio
        let playAudio = document.getElementById('audioPlay');
        //let partnerAudio = document.getElementById('partnerAudio');

        // This is the main thing to record
        // the audio 'MediaRecorder' API
        let mediaRecorder = new MediaRecorder(mediaStreamObj);
        // Pass the audio stream 

        // Start event
        record.onmousedown = function (ev) {
            mediaRecorder.start(ev);
            // console.log(mediaRecorder.state);
        }

        // Stop event
        record.addEventListener('mouseup', function (ev) {
            mediaRecorder.stop();
            // console.log(mediaRecorder.state);
        });

        // Send event
        send.addEventListener('click', function (ev) {
            sendMessage()
            // console.log(mediaRecorder.state);
        });
        // If audio data available then push 
        // it to the chunk array
        mediaRecorder.ondataavailable = function (ev) {
            dataArray.push(ev.data);
        }

        // Chunk array to store the audio data 
        let dataArray = [];
        
        var hostname = window.location.hostname;
        if (window.location.port != 80 && window.location.port != 443) {
            hostname = hostname + ":" + window.location.port;
        }

        var websocketname = "ws";
        if (window.location.protocol == "https:") {
            websocketname = websocketname + "s";
        }

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
                if (identifier == 49) {
                    var row = document.createElement("tr");
                    var numChild = document.createElement("th");
                    numChild.className += "scope=\"row\"";
                    numChild.innerHTML += "0";
                    row.appendChild(numChild)

                    var senderChild = document.createElement("td");
                    senderChild.innerHTML += partnerID;
                    row.appendChild(senderChild);

                    var buttonChild = document.createElement("td");
                    var button = document.createElement("button");
                    button.innerHTML = "Play";
                    let audioSrc = window.URL.createObjectURL(incoming_vm);
                    button.dataset.audioLink = audioSrc
                    button.addEventListener('click', function(ev) {
                        console.log("Play audio");
                        var audioElement = document.getElementById("partnerAudio");
                        audioElement.src = this.dataset.audioLink;
                        audioElement.play();
                    })
                    buttonChild.appendChild(button);
                    row.appendChild(buttonChild);

                    document.getElementById('msgbody').appendChild(row);
                } else if (identifier == 50) {
                    console.log("Received an offer!");
                    var resultstring = Utf8ArrayToStr(finalArray);
                    var amount = parseInt(resultstring);
                    //jQuery('#exampleModalLong').modal('show')
                    document.getElementById('modalText').innerHTML = "Your partner offered $" + amount + "! Will you accept the offer?";
                    console.log(finalArray);
                    console.log(resultstring);
                    var myModal = new bootstrap.Modal(document.getElementById('exampleModalLong'), {
                        keyboard: false
                    })
                    myModal.show();
                } else if(identifier == 51) {
                    console.log("Received a response!")
                    var resultstring = Utf8ArrayToStr(finalArray);
                    var result = parseInt(resultstring);
                    console.log(result);
                    if (result == 0) {
                        document.getElementById('modalText').innerHTML = "Your partner declined the offer.";
                    } else if (result == 1) {
                        document.getElementById('modalText').innerHTML = "Your partner accepted the offer!";
                    }
                    var myModal = new bootstrap.Modal(document.getElementById('exampleModalLong'), {
                        keyboard: false
                    })
                    myModal.show();
                }
            });           
        };
        function sendMessage(event) {
            ws.send(recording)

            var row = document.createElement("tr");
            var numChild = document.createElement("th");
            numChild.className += "scope=\"row\"";
            numChild.innerHTML += "1";
            row.appendChild(numChild)

            var senderChild = document.createElement("td");
            senderChild.innerHTML += selfID;
            row.appendChild(senderChild);

            var buttonChild = document.createElement("td");
            var button = document.createElement("button");
            button.innerHTML = "Play";
            let audioSrc = playAudio.src;
            button.dataset.audioLink = audioSrc
            button.addEventListener('click', function(ev) {
                console.log("Play audio");
                var audioElement = document.getElementById("partnerAudio");
                audioElement.src = this.dataset.audioLink;
                audioElement.play();
            })
            buttonChild.appendChild(button);
            row.appendChild(buttonChild);

            document.getElementById('msgbody').appendChild(row);
        }

        // Submit event
        submit.addEventListener('click', function (ev) {
            console.log("Submitting offer or response!")
            let val = offer.value;
            console.log(val);
            val = [val, 2];
            console.log(val);
            let data = new Blob(val);
            ws.send(data)
        });

        // Accept event
        accept.addEventListener('click', function (ev) {
            console.log("Offer Accepted!")
            let val = 1;
            val = [val, 3];
            console.log(val);
            let data = new Blob(val);
            ws.send(data)
            window.location.replace('/finish')
        });
        
        // Decline event
        decline.addEventListener('click', function (ev) {
            console.log("Offer Declined.")
            let val = 0;
            val = [val, 3];
            console.log(val);
            let data = new Blob(val);
            ws.send(data)
            window.location.replace('/finish')
        });


        // Convert the audio data in to blob 
        // after stopping the recording
        mediaRecorder.onstop = function (ev) {

            let tosend = [1];
            tosend = dataArray.concat(tosend);
            // blob of type mp3
            let audioData = new Blob(tosend,
                { 'type': 'audio/mpeg;' });
            // Save the latest blob to send (if requested)
            recording = audioData

            // Refresh the data array
            dataArray = [];

            // Creating audio url with reference of created blob named 'audioData'
            let audioSrc = window.URL
                .createObjectURL(audioData);

            // Pass the audio url to the 2nd video tag
            playAudio.src = audioSrc;
        }
    })

    // Print any errors 
    .catch(function (err) {
        console.log(err.name, err.message);
    });

