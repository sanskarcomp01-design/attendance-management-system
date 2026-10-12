import { useEffect, useRef, useState } from "react";
import { api, blobFromCanvas } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function FaceEnroll() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [streaming, setStreaming] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const { user, refreshUser } = useAuth();

  async function startCamera() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
      setStreaming(true);
    } catch (err) {
      setError(err.message || "Could not start the camera. Check browser permissions and try again.");
    }
  }

  async function capture() {
    setError("");
    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video?.videoWidth || !video.videoHeight) {
        throw new Error("The camera is not ready yet. Wait for the video and try again.");
      }
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext("2d").drawImage(video, 0, 0);
      const blob = await blobFromCanvas(canvas);
      if (!blob) throw new Error("Could not capture a photo from the camera.");
      const body = new FormData();
      body.append("image", blob, "face.jpg");
      const data = await api("/api/student/face/enroll", { method: "POST", body });
      setMessage(data.message);
      refreshUser(data.user);
      video.srcObject?.getTracks().forEach((t) => t.stop());
      video.srcObject = null;
      setStreaming(false);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => () => {
    videoRef.current?.srcObject?.getTracks().forEach((track) => track.stop());
  }, []);

  return (
    <article className="card camera-box">
      <h2>Enroll your face</h2>
      <p className="muted">Use even lighting, look at the camera, and keep only your face in the frame. Status: {user.has_face_enrolled ? "enrolled" : "not enrolled"}.</p>
      {error ? <p className="error">{error}</p> : null}
      {message ? <p className="success">{message}</p> : null}
      <video ref={videoRef} playsInline muted />
      <canvas ref={canvasRef} hidden />
      <div className="row-actions" style={{ marginTop: 12 }}>
        {!streaming ? (
          <button className="btn" type="button" onClick={startCamera}>Start camera</button>
        ) : (
          <button className="btn teal" type="button" onClick={capture}>Capture and save</button>
        )}
      </div>
    </article>
  );
}
