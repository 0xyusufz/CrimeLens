import { getToken, logout } from "./auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export async function apiClient(endpoint, { method = "GET", body, headers = {}, ...customConfig } = {}) {
  const token = getToken();
  
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
  const defaultHeaders = isFormData ? {} : { "Content-Type": "application/json" };

  const config = {
    method,
    headers: {
      ...defaultHeaders,
      ...headers,
    },
    ...customConfig,
  };

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  if (body) {
    config.body = isFormData ? body : JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, config);
  } catch (error) {
    throw new Error("Network error. Please ensure the backend is running.");
  }

  let data;
  try {
    data = await response.json();
  } catch (err) {
    if (!response.ok) {
      throw new ApiError("An unexpected error occurred.", response.status);
    }
    return null;
  }

  if (response.status === 401) {
    if (endpoint === "/api/auth/login") {
      const errorMsg = data?.detail || "Invalid email or password";
      throw new ApiError(errorMsg, 401, data);
    }
    logout();
    throw new ApiError("Session expired. Please log in again.", 401);
  }
  
  if (response.status === 403) {
    throw new ApiError(data?.detail || "You do not have permission to perform this action.", 403, data);
  }

  if (response.ok) {
    return data;
  }

  const errorMessage = data?.detail || data?.message || "An error occurred during the request.";
  throw new ApiError(errorMessage, response.status, data);
}
