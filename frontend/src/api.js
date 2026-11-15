const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

export async function apiFetch(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      ...(options.headers || {}),
    },
  });
  return response;
}

export async function apiJson(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  const response = await apiFetch(path, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    let errorMessage = `Request failed (${response.status})`;
    try {
      const errData = await response.json();
      if (errData.detail) {
        if (typeof errData.detail === "string") {
          errorMessage = errData.detail;
        } else if (Array.isArray(errData.detail)) {
          errorMessage = errData.detail.map((e) => e.msg || JSON.stringify(e)).join(", ");
        } else if (typeof errData.detail === "object" && errData.detail.errors) {
          errorMessage = errData.detail.errors.join(", ");
        }
      }
    } catch {
      // ignore json parse error
    }
    const err = new Error(errorMessage);
    err.status = response.status;
    throw err;
  }
  
  if (response.status === 204) {
    return null;
  }
  return response.json();
}
