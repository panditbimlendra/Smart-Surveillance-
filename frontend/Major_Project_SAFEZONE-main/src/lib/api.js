const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

async function readErrorMessage(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    const data = await response.json();

    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) {
      return data.detail
        .map((item) => item?.msg || JSON.stringify(item))
        .join(", ");
    }
    if (typeof data?.message === "string") return data.message;

    return JSON.stringify(data);
  }

  const text = await response.text();
  return text || `Request failed with ${response.status}`;
}

export function getHealth() {
  return request("/health");
}

export function getRecentAlerts(limit = 20) {
  return request(`/alerts/recent?limit=${limit}`);
}

export function getRecentLogs(limit = 50) {
  return request(`/logs/recent?limit=${limit}`);
}

export function getStreamStatus() {
  return request("/stream/status");
}

export function startStream(payload) {
  return request("/stream/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function stopStream() {
  return request("/stream/stop", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getWebcamStatus() {
  return request("/stream/webcam-status");
}

export function startWebcam(payload) {
  return request("/stream/start-webcam", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function stopWebcam() {
  return request("/stream/stop-webcam", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function analyzeFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json();
}

export function getStreamFrameUrl(cacheBust = "") {
  const suffix = cacheBust ? `?t=${encodeURIComponent(cacheBust)}` : "";
  return `${API_BASE_URL}/stream/frame${suffix}`;
}

export { API_BASE_URL };
