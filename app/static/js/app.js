/**
 * Main application initialization
 */

document.addEventListener("DOMContentLoaded", () => {
  // Mark active nav link
  const currentPath = window.location.pathname;
  document.querySelectorAll(".app-nav a").forEach((link) => {
    if (link.getAttribute("href") === currentPath) {
      link.classList.add("active");
    }
  });

  // Initialize common components
  utils.initCollapsibleCards();
  utils.initModals();

  // Initialize page-specific code
  const page = document.body.dataset.page;

  switch (page) {
    case "index":
      initDashboard();
      break;
    case "generator":
      initGenerator();
      break;
    case "library":
      initLibrary();
      break;
    case "settings":
      initSettings();
      break;
  }
});

// ========== DASHBOARD ==========

async function initDashboard() {
  try {
    // Load stats
    const [stimuliData, voicesData, musicData] = await Promise.all([
      api.stimuli.list(),
      api.voices.list(),
      api.music.list(),
    ]);

    // Update stat cards
    const totalStimuli = stimuliData.total || 0;
    const generatedCount = stimuliData.stimuli.filter(
      (s) => s.status === "generated"
    ).length;
    const totalVoices = voicesData.total || 0;
    const totalTracks = musicData.total || 0;

    updateStat("total-stimuli", totalStimuli);
    updateStat("generated-count", generatedCount);
    updateStat("total-voices", totalVoices);
    updateStat("total-tracks", totalTracks);

    // Load recent stimuli
    const recentList = document.getElementById("recent-stimuli");
    if (recentList && stimuliData.stimuli.length > 0) {
      recentList.innerHTML = "";
      stimuliData.stimuli.slice(0, 5).forEach((stimulus) => {
        recentList.appendChild(createStimulusRow(stimulus));
      });
    } else if (recentList) {
      recentList.innerHTML =
        '<div class="empty-state"><p>No stimuli yet. Create your first one!</p></div>';
    }
  } catch (error) {
    console.error("Dashboard init error:", error);
    utils.showError("Failed to load dashboard data");
  }
}

function updateStat(elementId, value) {
  const el = document.getElementById(elementId);
  if (el) el.textContent = value;
}

function createStimulusRow(stimulus) {
  const row = document.createElement("tr");
  row.innerHTML = `
        <td><strong>${stimulus.id}</strong></td>
        <td><span class="badge badge-${stimulus.status}">${
    stimulus.status
  }</span></td>
        <td>${utils.truncateText(stimulus.text.speech_text, 50) || "-"}</td>
        <td>${utils.formatDuration(stimulus.duration_ms)}</td>
        <td>${utils.formatDate(stimulus.created_at)}</td>
        <td class="table-actions">
            ${
              stimulus.audio_url
                ? `<button class="btn btn-sm btn-secondary" onclick="playAudio('${stimulus.audio_url}')">▶ Play</button>`
                : ""
            }
            <a href="/generator?id=${
              stimulus.id
            }" class="btn btn-sm btn-secondary">Edit</a>
        </td>
    `;
  return row;
}

// ========== LIBRARY ==========

async function initLibrary() {
  const container = document.getElementById("library-container");
  const searchInput = document.getElementById("library-search");
  const statusFilter = document.getElementById("status-filter");

  let allStimuli = [];

  async function loadStimuli() {
    try {
      container.innerHTML =
        '<div class="loading"><div class="spinner"></div><span class="loading-text">Loading...</span></div>';

      const data = await api.stimuli.list();
      allStimuli = data.stimuli || [];
      renderStimuli(allStimuli);
    } catch (error) {
      console.error("Failed to load stimuli:", error);
      container.innerHTML =
        '<div class="empty-state"><p>Failed to load stimuli</p></div>';
    }
  }

  function renderStimuli(stimuli) {
    if (stimuli.length === 0) {
      container.innerHTML = `
                <div class="empty-state">
                    <h3>No stimuli found</h3>
                    <p>Create your first stimulus in the Generator</p>
                    <a href="/generator" class="btn btn-primary">Go to Generator</a>
                </div>
            `;
      return;
    }

    container.innerHTML = "";
    const grid = document.createElement("div");
    grid.className = "library-grid";

    stimuli.forEach((stimulus) => {
      grid.appendChild(createLibraryCard(stimulus));
    });

    container.appendChild(grid);
  }

  function createLibraryCard(stimulus) {
    const card = document.createElement("div");
    card.className = "library-item";
    card.innerHTML = `
            <div class="library-item-header">
                <span class="library-item-title">${stimulus.id}</span>
                <span class="badge badge-${stimulus.status}">${
      stimulus.status
    }</span>
            </div>
            <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.75rem;">
                ${
                  utils.truncateText(stimulus.text.speech_text, 100) ||
                  "No text"
                }
            </p>
            ${
              stimulus.audio_url
                ? `
                <div class="audio-player">
                    <audio controls src="${stimulus.audio_url}"></audio>
                </div>
            `
                : ""
            }
            <div class="library-item-meta">
                <span>Duration: ${utils.formatDuration(
                  stimulus.duration_ms
                )}</span> •
                <span>${utils.formatDate(stimulus.created_at)}</span>
            </div>
            <div style="margin-top: 0.75rem; display: flex; gap: 0.5rem;">
                <a href="/generator?id=${
                  stimulus.id
                }" class="btn btn-sm btn-secondary">Edit</a>
                <button class="btn btn-sm btn-secondary" onclick="duplicateStimulus('${
                  stimulus.id
                }')">Duplicate</button>
                <button class="btn btn-sm btn-danger" onclick="deleteStimulus('${
                  stimulus.id
                }')">Delete</button>
            </div>
        `;
    return card;
  }

  function filterStimuli() {
    const search = searchInput?.value.toLowerCase() || "";
    const status = statusFilter?.value || "";

    let filtered = allStimuli;

    if (search) {
      filtered = filtered.filter(
        (s) =>
          s.id.toLowerCase().includes(search) ||
          (s.text.speech_text &&
            s.text.speech_text.toLowerCase().includes(search))
      );
    }

    if (status) {
      filtered = filtered.filter((s) => s.status === status);
    }

    renderStimuli(filtered);
  }

  // Event listeners
  if (searchInput) {
    searchInput.addEventListener("input", utils.debounce(filterStimuli, 300));
  }
  if (statusFilter) {
    statusFilter.addEventListener("change", filterStimuli);
  }

  // Export buttons
  document.getElementById("export-csv")?.addEventListener("click", () => {
    window.location.href = api.export.csv();
  });

  document.getElementById("export-json")?.addEventListener("click", () => {
    window.location.href = api.export.json();
  });

  // Load initial data
  loadStimuli();
}

// Global functions for library actions
window.duplicateStimulus = async function (stimulusId) {
  try {
    const result = await api.stimuli.duplicate(stimulusId);
    utils.showSuccess(`Duplicated as ${result.new_id}`);
    window.location.reload();
  } catch (error) {
    utils.showError("Failed to duplicate: " + error.message);
  }
};

window.deleteStimulus = async function (stimulusId) {
  if (!confirm(`Delete stimulus ${stimulusId}? This cannot be undone.`)) return;

  try {
    await api.stimuli.delete(stimulusId);
    utils.showSuccess("Stimulus deleted");
    window.location.reload();
  } catch (error) {
    utils.showError("Failed to delete: " + error.message);
  }
};

// ========== SETTINGS ==========

async function initSettings() {
  // Load current settings status
  try {
    const [voicesData, modelsData] = await Promise.all([
      api.voices.list().catch(() => ({ total: 0 })),
      api.llm.models().catch(() => ({ models: [] })),
    ]);

    // Update status indicators
    const elevenLabsStatus = document.getElementById("elevenlabs-status");
    const llmStatus = document.getElementById("llm-status");

    if (elevenLabsStatus) {
      if (voicesData.total > 0) {
        elevenLabsStatus.innerHTML = `<span class="badge badge-generated">Connected (${voicesData.total} voices)</span>`;
      } else {
        elevenLabsStatus.innerHTML =
          '<span class="badge badge-failed">Not connected</span>';
      }
    }

    if (llmStatus) {
      if (modelsData.models.length > 0) {
        const providers = [
          ...new Set(modelsData.models.map((m) => m.provider)),
        ];
        llmStatus.innerHTML = `<span class="badge badge-generated">Connected (${providers.join(
          ", "
        )})</span>`;
      } else {
        llmStatus.innerHTML =
          '<span class="badge badge-failed">Not connected</span>';
      }
    }
  } catch (error) {
    console.error("Settings init error:", error);
  }

  // Preload prosody button
  document
    .getElementById("preload-prosody")
    ?.addEventListener("click", async () => {
      const btn = document.getElementById("preload-prosody");
      utils.setLoading(btn, true, "Preloading...");
      try {
        const result = await api.prosody.preload();
        utils.showSuccess(
          `Preloaded ${result.total_references} prosody profiles`
        );
      } catch (error) {
        utils.showError("Failed to preload: " + error.message);
      } finally {
        utils.setLoading(btn, false);
      }
    });
}

// ========== GLOBAL AUDIO PLAYER ==========

let globalAudio = null;

window.playAudio = function (url) {
  if (globalAudio) {
    globalAudio.pause();
  }
  globalAudio = new Audio(url);
  globalAudio.play();
};

window.stopAudio = function () {
  if (globalAudio) {
    globalAudio.pause();
    globalAudio = null;
  }
};
