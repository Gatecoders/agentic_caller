// // src/hooks/useAudioPlayer.js

// const useAudioPlayer = (onEnd) => {
//   const playAudioFromBlob = async (blob) => {
//     try {
//       const arrayBuffer = await blob.arrayBuffer();
//       const float32Array = new Float32Array(arrayBuffer);

//       const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
//       const audioBuffer = audioCtx.createBuffer(1, float32Array.length, 22050);
//       audioBuffer.copyToChannel(float32Array, 0);

//       const source = audioCtx.createBufferSource();
//       source.buffer = audioBuffer;
//       source.connect(audioCtx.destination);

//       source.onended = () => {
//         audioCtx.close();
//         onEnd?.();
//       };

//       source.start();
//     } catch (error) {
//       console.error("Audio playback error:", error);
//     }
//   };

//   return { playAudioFromBlob };
// };

// export default useAudioPlayer;

// src/hooks/useAudioPlayer.js

const useAudioPlayer = (onEnd) => {
  const playAudioFromBlob = async (blob) => {
    try {
      const arrayBuffer = await blob.arrayBuffer();

      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

      audioCtx.decodeAudioData(
        arrayBuffer,
        (decodedData) => {
          const source = audioCtx.createBufferSource();
          source.buffer = decodedData;
          source.connect(audioCtx.destination);

          source.onended = () => {
            audioCtx.close();
            onEnd?.();
          };

          source.start();
        },
        (error) => {
          console.error("Error decoding audio data:", error);
        }
      );
    } catch (error) {
      console.error("Audio playback error:", error);
    }
  };

  return { playAudioFromBlob };
};

export default useAudioPlayer;
