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
        let recording = new Blob()

        // Start record
        let record = document.getElementById('btnRecord');
        let send = document.getElementById('btnsend');

        // 2nd audio tag for play the audio
        let playAudio = document.getElementById('audioPlay');
        let partnerAudio = document.getElementById('partnerAudio');

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
        
        var wsaddr = "ws://localhost:8000/audiowspaired/" + 1//send.data-id
        var ws = new WebSocket(wsaddr);
        ws.onmessage = function(event) {
            incoming_vm = event.data
            let audioSrc = window.URL.createObjectURL(incoming_vm);
            partnerAudio.src = audioSrc;
        };
        function sendMessage(event) {
            ws.send(recording)
            recording = new Blob()
        }

        // Convert the audio data in to blob 
        // after stopping the recording
        mediaRecorder.onstop = function (ev) {

            // blob of type mp3
            let audioData = new Blob(dataArray,
                { 'type': 'audio/mp3;' });
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

