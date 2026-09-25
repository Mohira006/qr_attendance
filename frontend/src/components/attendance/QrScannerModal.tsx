import jsQR from "jsqr";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Modal } from "@/components/ui/Modal";

export function QrScannerModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setError(t("qrScanner.notSupported"));
      return;
    }

    let cancelled = false;
    let stream: MediaStream | null = null;
    let rafId: number | null = null;
    let detected = false;

    function stopCamera() {
      if (rafId !== null) cancelAnimationFrame(rafId);
      stream?.getTracks().forEach((track) => track.stop());
    }

    function handleDetected(rawValue: string) {
      detected = true;
      stopCamera();
      try {
        const scanned = new URL(rawValue, window.location.origin);
        if (scanned.origin === window.location.origin && scanned.pathname === "/scan") {
          navigate("/scan");
          return;
        }
      } catch {
        // falls through to the error below - rawValue wasn't a valid URL at all
      }
      setError(t("qrScanner.invalidCode"));
    }

    function tick() {
      if (detected) return;
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (video && canvas && video.readyState === video.HAVE_ENOUGH_DATA) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const context = canvas.getContext("2d");
        if (context) {
          context.drawImage(video, 0, 0, canvas.width, canvas.height);
          const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
          const code = jsQR(imageData.data, imageData.width, imageData.height);
          if (code) {
            handleDetected(code.data);
            return;
          }
        }
      }
      rafId = requestAnimationFrame(tick);
    }

    async function start() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        tick();
      } catch {
        if (!cancelled) setError(t("qrScanner.cameraError"));
      }
    }

    void start();
    return () => {
      cancelled = true;
      stopCamera();
    };
  }, [navigate, t]);

  return (
    <Modal title={t("qrScanner.title")} onClose={onClose}>
      <div className="space-y-3">
        {error ? (
          <p className="rounded-lg bg-status-danger-bg px-3 py-2 text-sm text-status-danger">{error}</p>
        ) : (
          <div className="relative overflow-hidden rounded-xl bg-black">
            <video ref={videoRef} className="aspect-square w-full object-cover" muted playsInline />
            <div className="pointer-events-none absolute inset-10 rounded-2xl border-2 border-white/70" />
          </div>
        )}
        <canvas ref={canvasRef} className="hidden" />
        <p className="text-center text-sm text-ink-muted">{t("qrScanner.instructions")}</p>
      </div>
    </Modal>
  );
}
