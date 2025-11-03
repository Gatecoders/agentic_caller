// src/hooks/useSpeechToText.js

// const useSpeechToText = (onResult) => {
//   let recognition;

//   const setupRecognition = () => {
//     const SpeechRecognition =
//       window.SpeechRecognition || window.webkitSpeechRecognition;
//     if (!SpeechRecognition) {
//       alert("Speech Recognition not supported in this browser.");
//       return;
//     }

//     recognition = new SpeechRecognition();
//     recognition.continuous = true;
//     recognition.interimResults = false;
//     recognition.lang = "en-US";

//     recognition.onresult = (event) => {
//       const transcript = event.results[0][0].transcript;
//       console.log("Recognized:", transcript);
//       onResult(transcript);
//     };

//     recognition.onerror = (err) => {
//       console.error("Speech recognition error:", err);
//     };
//   };

//   const startListening = () => {
//     setupRecognition();
//     recognition?.start();
//   };

//   const stopListening = () => {
//     recognition?.stop();
//   };

//   return { startListening, stopListening };
// };

// export default useSpeechToText;

const useSpeechToText = (onResult) => {
  let recognition;

  const setupRecognition = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech Recognition not supported in this browser.");
      return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      console.log("Recognized:", transcript);
      onResult(transcript);
    };

    recognition.onerror = (err) => {
      console.error("Speech recognition error:", err);
      // Restart listening after an error occurs
      if (recognition) {
        console.log("Restarting speech recognition after error...");
        recognition.stop();
        setTimeout(() => {
          recognition.start();
        }, 100);
      }
    };

    // Also handle the end event to restart if it stops unexpectedly
    recognition.onend = () => {
      console.log("Speech recognition ended");
      // If we're still meant to be listening, restart
      if (recognition && recognition._isListening) {
        console.log("Restarting speech recognition...");
        recognition.start();
      }
    };
  };

  const startListening = () => {
    setupRecognition();
    if (recognition) {
      recognition._isListening = true;
      recognition.start();
    }
  };

  const stopListening = () => {
    if (recognition) {
      recognition._isListening = false;
      recognition.stop();
    }
  };

  return { startListening, stopListening };
};

export default useSpeechToText;
