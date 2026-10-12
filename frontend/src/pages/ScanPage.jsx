import { useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";
import { api, blobFromCanvas } from "../api.js";

export default function ScanPage() {
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [scanning, setScanning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [livenessStep, setLivenessStep] = useState("");
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const scannerRef = useRef(null);

  async function startScan() {
    setError("");
    try {
      const scanner = new Html5Qrcode("qr-reader");
      scannerRef.current = scanner;
      setScanning(true);
      await scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decoded) => {
          setToken(decoded);
          scanner.stop().catch((err) => setError(err.message));
          setScanning(false);
        }
      );
    } catch (err) {
      setScanning(false);
      setError(err.message || "Could not start QR scanning. Check browser camera permissions.");
    }
  }

  useEffect(() => () => {
    scannerRef.current?.stop().catch(() => {});
    videoRef.current?.srcObject?.getTracks().forEach((track) => track.stop());
  }, []);

  async function startSelfie() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
      videoRef.current.srcObject = stream;
      await videoRef.current.play();
    } catch (err) {
      setError(err.message || "Could not start the selfie camera. Check browser permissions.");
    }
  }

  async function submit() {
    setError("");
    setMessage("");
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!token) {
      setError("Scan a valid teacher QR code first.");
      return;
    }
    if (!video?.videoWidth || !video.videoHeight) {
      setError("Start the selfie camera and wait for the video before submitting.");
      return;
    }
    setSubmitting(true);
    try {
      const challenge = await api("/api/student/attendance/challenge", {
        method: "POST",
        body: JSON.stringify({ token }),
      });

      setLivenessStep("Look straight at the camera and hold still...");
      await new Promise((resolve) => window.setTimeout(resolve, 1200));
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext("2d");
      if (!context) throw new Error("Could not capture a photo from the camera.");
      context.drawImage(video, 0, 0);
      const neutral = await blobFromCanvas(canvas);
      if (!neutral) throw new Error("Could not capture a photo from the camera.");

      setLivenessStep(`Now turn your head so your nose moves toward the ${challenge.direction} side of the frame and hold still...`);
      await new Promise((resolve) => window.setTimeout(resolve, 2000));
      context.drawImage(video, 0, 0);
      const turned = await blobFromCanvas(canvas);
      if (!turned) throw new Error("Could not capture a photo from the camera.");

      const body = new FormData();
      body.append("token", token);
      body.append("challenge_id", challenge.challenge_id);
      body.append("neutral_image", neutral, "neutral.jpg");
      body.append("turned_image", turned, "turned.jpg");
      const data = await api("/api/student/attendance/mark", { method: "POST", body });
      setMessage(`${data.message} Face score: ${data.face_score}`);
      setLivenessStep("");
      video.srcObject?.getTracks().forEach((t) => t.stop());
      video.srcObject = null;
    } catch (err) {
      setError(err.message);
      setLivenessStep("");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="stack">
      <article className="card">
        <h2>1. Scan teacher QR</h2>
        {error ? <p className="error">{error}</p> : null}
        {message ? <p className="success">{message}</p> : null}
        <div id="qr-reader" />
        {!scanning && !token ? (
          <button className="btn" type="button" onClick={startScan}>Start QR scanner</button>
        ) : null}
        {token ? <p className="success">QR captured. Continue with a live selfie.</p> : null}
      </article>
      <article className="card camera-box">
        <h2>2. Live face check</h2>
        <video ref={videoRef} playsInline muted />
        <canvas ref={canvasRef} hidden />
        {livenessStep ? <p className="muted" aria-live="polite">{livenessStep}</p> : null}
        <div className="row-actions" style={{ marginTop: 12 }}>
          <button className="btn light" type="button" onClick={startSelfie} disabled={submitting}>
            Start selfie camera
          </button>
          <button className="btn teal" type="button" onClick={submit} disabled={!token || submitting}>
            {submitting ? "Checking..." : "Verify and mark present"}
          </button>
        </div>
      </article>
    </div>
  );
}
