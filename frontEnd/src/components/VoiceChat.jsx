import React, { useState } from "react";
import useSpeechToText from "../hooks/useSpeechToText";
import useAudioPlayer from "../hooks/useAudioPlayer";
import {
  connectWebSocket,
  sendMessage,
  closeWebSocket,
} from "../services/websocket";

const VoiceChat = () => {
  const [isActive, setIsActive] = useState(false);
  const [transcriptText, setTranscriptText] = useState("");
  const [showPopup, setShowPopup] = useState(false);
  const [username, setUsername] = useState("");
  const [title, setTitle] = useState("Mr");
  const [provider, setProvider] = useState("Azure");
  const [voice, setVoice] = useState("");

  const azureVoices = [
    "hi-IN-AaravNeural", "hi-IN-ArjunNeural", "hi-IN-KunalNeural", "hi-IN-RehaanNeural", "hi-IN-MadhurNeural", "hi-IN-AnanyaNeural", "hi-IN-AartiNeural", 
    "hi-IN-KavyaNeural", "hi-IN-SwaraNeural", "en-IN-Arjun:DragonHDLatestNeural", "en-IN-ArjunIndicNeural", "en-IN-PrabhatIndicNeural", "en-IN-AaravNeural", 
    "en-IN-ArjunNeural", "en-IN-KunalNeural", "en-IN-PrabhatNeural", "en-IN-RehaanNeural", "en-IN-Meera:DragonHDLatestNeural", "en-IN-Aarti:DragonHDLatestNeural",
    "en-IN-AartiIndicNeural", "en-IN-NeerjaIndicNeural", "en-IN-AashiNeural", "en-IN-AartiNeural", "en-IN-AnanyaNeural", "en-IN-KavyaNeural", "en-IN-NeerjaNeural"
  ];

  const amazonVoices = ["Raveena", "Aditi", "Kajal"];

  const onTranscript = (text) => {
    setTranscriptText(text);
    sendMessage(text);
    console.log("Sent to WebSocket:", text);
  };

  const onAudioEnd = () => {
    console.log("Audio ended. Listening again...");
    startListening();
  };

  const { startListening, stopListening } = useSpeechToText(onTranscript);
  const { playAudioFromBlob } = useAudioPlayer(onAudioEnd);

  const handleSocketMessage = async (event) => {
    if (event.data instanceof Blob) {
      console.log("Received audio from server.");
      stopListening();
      await playAudioFromBlob(event.data);
    } else {
      console.log("Text received:", event.data);
    }
  };

  const startConversation = () => {
    setIsActive(true);
    setShowPopup(false);

    const preferences = { username, title, provider, voice };

    connectWebSocket(
      handleSocketMessage,
      () => {
        console.log("WebSocket connected.");
        // Preferences are now sent in connectWebSocket, no need to send here
        setTranscriptText(
          `Preferences set: ${title} ${username}, ${provider}, ${voice}`
        );
      },
      (err) => console.error("WebSocket error:", err),
      () => {
        setIsActive(false);
        console.log("WebSocket closed.");
      },
      preferences // Pass preferences to connectWebSocket
    );
  };

  const stopConversation = () => {
    stopListening();
    sendMessage("conversation has ended");
    closeWebSocket();
    setIsActive(false);
    setTranscriptText("");
  };

  const toggleConversation = () => {
    if (isActive) {
      stopConversation();
    } else {
      setShowPopup(true);
    }
  };

  const handlePopupSubmit = () => {
    if (username && voice) {
      startConversation();
    } else {
      alert("Please enter a username and select a voice.");
    }
  };

  return (
    <div
      className="relative h-screen w-full bg-cover bg-center"
      style={{ backgroundImage: `url("/background.png")` }}
    >
      <div className="relative flex flex-col items-center justify-center h-full text-white">
        <div className="mt-[2rem]">
          <h2 className="text-[4rem] font-roboto font-[500]">
            AI Voice Chat Bot
          </h2>
        </div>

        {/* {transcriptText && (
          <div className="mt-8 px-6 py-3 bg-black bg-opacity-60 rounded text-white max-w-xl text-center text-[1.25rem]">
            <p>
              <strong>You said:</strong> {transcriptText}
            </p>
          </div>
        )} */}

        <div className="flex gap-4 pt-[10rem]">
          <button
            onClick={toggleConversation}
            className={`px-[4rem] py-[1rem] rounded-full font-poppins text-[1.5rem] ${
              isActive ? "bg-white" : "bg-white"
            } text-black`}
          >
            {isActive ? "⛔ Press to stop" : "🎙️ Talk to Eva"}
          </button>
        </div>
      </div>

      {showPopup && (
        <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-60">
          <div className="bg-white p-8 rounded-xl shadow-2xl text-black w-[450px] max-w-full">
            <h3 className="text-2xl font-bold text-gray-800 mb-6 text-center">
              Set Your Preferences
            </h3>

            <div className="mb-5">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Title
              </label>
              <select
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition duration-200"
              >
                <option value="Mr">Mr</option>
                <option value="Ms">Ms</option>
              </select>
            </div>

            <div className="mb-5">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your name"
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition duration-200 placeholder-gray-400"
              />
            </div>

            <div className="mb-5">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Choose Provider
              </label>
              <select
                value={provider}
                onChange={(e) => {
                  setProvider(e.target.value);
                  setVoice("");
                }}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition duration-200"
              >
                <option value="Azure">Azure</option>
                <option value="Amazon">Amazon</option>
              </select>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Choose Voice
              </label>
              <select
                value={voice}
                onChange={(e) => setVoice(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition duration-200"
              >
                <option value="">Select a voice</option>
                {(provider === "Azure" ? azureVoices : amazonVoices).map(
                  (voiceOption) => (
                    <option key={voiceOption} value={voiceOption}>
                      {voiceOption}
                    </option>
                  )
                )}
              </select>
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowPopup(false)}
                className="px-5 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition duration-200 font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handlePopupSubmit}
                className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition duration-200 font-medium"
              >
                Start
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VoiceChat;
