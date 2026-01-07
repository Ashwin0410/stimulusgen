/**
 * API client for the Stimulus Generator
 */

const API_BASE = "/api";

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;

  const config = {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  };

  if (
    config.body &&
    typeof config.body === "object" &&
    !(config.body instanceof FormData)
  ) {
    config.body = JSON.stringify(config.body);
  }

  if (config.body instanceof FormData) {
    delete config.headers["Content-Type"];
  }

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    // Handle different response types
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      return await response.json();
    }

    return response;
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

// ========== VOICES ==========

const voices = {
  list: () => request("/voices"),
  get: (voiceId) => request(`/voices/${voiceId}`),
  favorites: () => request("/voices/favorites"),
};

// ========== MUSIC ==========

const music = {
  list: () => request("/music"),
  folders: () => request("/music/folders"),
  getTrack: (trackId) => request(`/music/track/${trackId}`),
  getByPath: (path) =>
    request(`/music/by-path?path=${encodeURIComponent(path)}`),
  
  /**
   * Get duration and target words for a track with voice adjustments.
   * 
   * @param {string} path - Path to the music track
   * @param {number} voiceSpeed - Voice speed multiplier (0.5 to 2.0, default 1.0)
   * @param {number} speechEntryMs - Delay before voice starts in ms (default 0)
   * @param {number} crossfadeMs - Crossfade duration at end in ms (default 2000)
   * @param {number} wpm - Words per minute override (optional)
   * @param {number} safetyFactor - Safety buffer override (optional)
   * @returns {Promise<Object>} Duration and target words info
   */
  getDuration: (
    path,
    voiceSpeed = 1.0,
    speechEntryMs = 0,
    crossfadeMs = 2000,
    wpm = null,
    safetyFactor = null
  ) => {
    let url = `/music/duration?path=${encodeURIComponent(path)}`;
    url += `&voice_speed=${voiceSpeed}`;
    url += `&speech_entry_ms=${speechEntryMs}`;
    url += `&crossfade_ms=${crossfadeMs}`;
    if (wpm !== null) {
      url += `&wpm=${wpm}`;
    }
    if (safetyFactor !== null) {
      url += `&safety_factor=${safetyFactor}`;
    }
    return request(url);
  },
  
  // Upload a new music file
  upload: (file, folder = "") => {
    const formData = new FormData();
    formData.append("file", file);
    if (folder) formData.append("folder", folder);
    return request("/music/upload", { method: "POST", body: formData });
  },
  // Delete a music track (only uploaded tracks)
  delete: (trackId) => request(`/music/track/${trackId}`, { method: "DELETE" }),
  // List only uploaded music tracks
  listUploaded: () => request("/music/uploaded"),
};

// ========== LLM ==========

const llm = {
  generate: (params) =>
    request("/llm/generate", { method: "POST", body: params }),
  models: () => request("/llm/models"),
  styles: () => request("/llm/styles"),
  templates: () => request("/llm/templates"),
  getStyle: (styleId) => request(`/llm/styles/${styleId}`),
  chaplinReference: () => request("/llm/reference/chaplin"),
  
  /**
   * Calculate target words from duration with voice adjustments.
   * 
   * @param {number} durationMs - Duration in milliseconds
   * @param {number} voiceSpeed - Voice speed multiplier (0.5 to 2.0, default 1.0)
   * @param {number} speechEntryMs - Delay before voice starts in ms (default 0)
   * @param {number} crossfadeMs - Crossfade duration at end in ms (default 2000)
   * @param {number} wpm - Words per minute override (optional)
   * @param {number} safetyFactor - Safety buffer override (optional)
   * @returns {Promise<Object>} Target words and calculation details
   */
  calculateWords: (
    durationMs,
    voiceSpeed = 1.0,
    speechEntryMs = 0,
    crossfadeMs = 2000,
    wpm = null,
    safetyFactor = null
  ) => {
    let url = `/llm/calculate-words?duration_ms=${durationMs}`;
    url += `&voice_speed=${voiceSpeed}`;
    url += `&speech_entry_ms=${speechEntryMs}`;
    url += `&crossfade_ms=${crossfadeMs}`;
    if (wpm !== null) {
      url += `&wpm=${wpm}`;
    }
    if (safetyFactor !== null) {
      url += `&safety_factor=${safetyFactor}`;
    }
    return request(url);
  },
};

// ========== STIMULI ==========

const stimuli = {
  list: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/stimuli${query ? "?" + query : ""}`);
  },
  get: (stimulusId) => request(`/stimuli/${stimulusId}`),
  create: (data) => request("/stimuli", { method: "POST", body: data }),
  update: (stimulusId, data) =>
    request(`/stimuli/${stimulusId}`, { method: "PUT", body: data }),
  delete: (stimulusId) =>
    request(`/stimuli/${stimulusId}`, { method: "DELETE" }),
  duplicate: (stimulusId, newId = null) => {
    const query = newId ? `?new_id=${encodeURIComponent(newId)}` : "";
    return request(`/stimuli/${stimulusId}/duplicate${query}`, {
      method: "POST",
    });
  },
  nextId: () => request("/stimuli/next-id"),
};

// ========== GENERATE ==========

const generate = {
  fromStimulus: (stimulusId) =>
    request("/generate", { method: "POST", body: { stimulus_id: stimulusId } }),
  direct: (params) =>
    request("/generate/direct", { method: "POST", body: params }),
  status: (stimulusId) => request(`/generate/status/${stimulusId}`),
};

// ========== EXPORT ==========

const exportApi = {
  csv: () => `${API_BASE}/export/csv`,
  json: () => `${API_BASE}/export/json`,
  stimulus: (stimulusId, includeAudio = true) =>
    `${API_BASE}/export/stimulus/${stimulusId}?include_audio=${includeAudio}`,
  batch: (stimulusIds, includeAudio = true) =>
    `${API_BASE}/export/batch?stimulus_ids=${stimulusIds.join(
      ","
    )}&include_audio=${includeAudio}`,
};

// ========== TEMPLATES ==========

const templates = {
  list: () => request("/templates"),
  defaults: () => request("/templates/defaults"),
  get: (templateId) => request(`/templates/${templateId}`),
  create: (data) => request("/templates", { method: "POST", body: data }),
  delete: (templateId) =>
    request(`/templates/${templateId}`, { method: "DELETE" }),
};

// ========== PROSODY ==========

const prosody = {
  references: () => request("/prosody/references"),
  getProfile: (referenceId) => request(`/prosody/profile/${referenceId}`),
  extract: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return request("/prosody/extract", { method: "POST", body: formData });
  },
  upload: (file, name = "") => {
    const formData = new FormData();
    formData.append("file", file);
    if (name) formData.append("name", name);
    return request("/prosody/upload", { method: "POST", body: formData });
  },
  compare: (file, reference = "great_dictator") => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("reference", reference);
    return request("/prosody/compare", { method: "POST", body: formData });
  },
  delete: (referenceId) =>
    request(`/prosody/reference/${referenceId}`, { method: "DELETE" }),
  preload: () => request("/prosody/preload", { method: "POST" }),
};

// ========== EXPORT API MODULE ==========

window.api = {
  voices,
  music,
  llm,
  stimuli,
  generate,
  export: exportApi,
  templates,
  prosody,
};
