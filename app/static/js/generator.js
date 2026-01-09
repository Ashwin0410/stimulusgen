/**
 * Generator page functionality
 */

let currentStimulusId = null;
let isEditing = false;
let currentTargetWords = null; // Store calculated target words from music
let currentMusicDuration = null; // Store music duration in ms

// =============================================================================
// TTS TIMING CONFIGURATION
// =============================================================================
// Production-tested value: 102 WPM (1.7 words per second)
// This accounts for [pause] tokens, audio tags, natural pauses, and emotional delivery.
//
// SAFETY BUFFER: 1.0 (100% - no reduction)
// Speech fills the ENTIRE music duration. User controls any delay via Speech Entry.
// Crossfade is handled by the audio mixer, not word count calculation.
// =============================================================================
const BASE_TTS_WPM = 102; // Production-tested: matches Journey app
const TTS_SAFETY_BUFFER = 1.0; // 100% = no reduction, speech fills entire music duration

async function initGenerator() {
  // Check if editing existing stimulus
  const editId = utils.getUrlParam("id");
  if (editId) {
    isEditing = true;
    currentStimulusId = editId;
    await loadExistingStimulus(editId);
  } else {
    // Get next available ID
    try {
      const result = await api.stimuli.nextId();
      currentStimulusId = result.next_id;
      document.getElementById("stimulus-id").value = currentStimulusId;
    } catch (error) {
      console.error("Failed to get next ID:", error);
      currentStimulusId = "STIM_001";
      document.getElementById("stimulus-id").value = currentStimulusId;
    }
  }

  // Load dropdown data
  await Promise.all([
    loadVoices(),
    loadMusic(),
    loadLLMOptions(),
    loadProsodyReferences(),
    loadTemplates(),
  ]);

  // Initialize sliders
  initAllSliders();

  // Event listeners
  setupEventListeners();

  // Update word count on text change
  updateWordCount();
}

async function loadExistingStimulus(stimulusId) {
  try {
    const stimulus = await api.stimuli.get(stimulusId);

    // Set form values
    document.getElementById("stimulus-id").value = stimulus.id;
    document.getElementById("stimulus-id").disabled = true;

    // Music
    document.getElementById("music-track").value = stimulus.music.track || "";
    document.getElementById("music-volume").value = stimulus.music.volume_db;
    document.getElementById("music-entry").value =
      stimulus.music.speech_entry_ms;
    document.getElementById("music-crossfade").value =
      stimulus.music.crossfade_ms;

    // Voice - set these BEFORE calculating target words
    document.getElementById("voice-model").value = stimulus.voice.model;
    setTimeout(() => {
      document.getElementById("voice-id").value = stimulus.voice.voice_id;
    }, 500); // Wait for voices to load
    document.getElementById("voice-stability").value = stimulus.voice.stability;
    document.getElementById("voice-similarity").value =
      stimulus.voice.similarity_boost;
    document.getElementById("voice-style").value =
      stimulus.voice.style_exaggeration;
    document.getElementById("voice-speed").value = stimulus.voice.speed;
    document.getElementById("voice-speaker-boost").checked =
      stimulus.voice.speaker_boost;

    // Text
    document.getElementById("speech-text").value =
      stimulus.text.speech_text || "";
    document.getElementById("text-source").value = stimulus.text.source;

    // Load target_words if exists
    if (stimulus.text.target_words) {
      currentTargetWords = stimulus.text.target_words;
      const targetWordsInput = document.getElementById("target-words");
      if (targetWordsInput) {
        targetWordsInput.value = stimulus.text.target_words;
      }
    }

    // Mix
    document.getElementById("mix-reverb").value = stimulus.mix.reverb_mix;
    document.getElementById("mix-reverb-decay").value =
      stimulus.mix.reverb_decay;
    document.getElementById("mix-compression").value =
      stimulus.mix.compression_ratio;
    document.getElementById("mix-deesser").value =
      stimulus.mix.deesser_threshold;
    document.getElementById("mix-eq-low").value = stimulus.mix.eq_low_cut;
    document.getElementById("mix-eq-high").value = stimulus.mix.eq_high_cut;
    document.getElementById("mix-pitch").value = stimulus.mix.pitch_shift;
    document.getElementById("mix-normalization").value =
      stimulus.mix.normalization_lufs;

    // Prosody
    document.getElementById("prosody-reference").value =
      stimulus.prosody.reference;
    document.getElementById("prosody-intensity").value =
      stimulus.prosody.intensity;

    // Update slider displays
    updateAllSliderDisplays();
    updateWordCount();

    // If music track exists, fetch its duration AFTER voice speed is set
    if (stimulus.music.track) {
      await onMusicTrackChange(stimulus.music.track);
    }

    // Show existing audio if available (no auto-play for loaded stimuli)
    if (stimulus.audio_url) {
      showAudioPreview(stimulus.audio_url, false);
    }

    utils.showInfo(`Loaded stimulus ${stimulusId}`);
  } catch (error) {
    utils.showError("Failed to load stimulus: " + error.message);
    console.error(error);
  }
}

async function loadVoices() {
  try {
    const data = await api.voices.list();
    const select = document.getElementById("voice-id");

    select.innerHTML = '<option value="">Select a voice...</option>';

    data.voices.forEach((voice) => {
      const option = document.createElement("option");
      option.value = voice.voice_id;
      option.textContent = voice.is_favorite ? `⭐ ${voice.name}` : voice.name;
      select.appendChild(option);
    });

    // Set default voice
    if (data.default_voice_id && !isEditing) {
      select.value = data.default_voice_id;
    }
  } catch (error) {
    console.error("Failed to load voices:", error);
    utils.showError("Failed to load voices. Check your ElevenLabs API key.");
  }
}

async function loadMusic() {
  try {
    const data = await api.music.list();
    const select = document.getElementById("music-track");

    // Store current selection to restore after reload
    const currentValue = select.value;

    select.innerHTML = '<option value="">No music (voice only)</option>';

    // Group by folder
    Object.entries(data.folders).forEach(([folder, tracks]) => {
      const optgroup = document.createElement("optgroup");
      optgroup.label = folder;

      tracks.forEach((track) => {
        const option = document.createElement("option");
        option.value = track.path;
        option.textContent = track.name;
        optgroup.appendChild(option);
      });

      select.appendChild(optgroup);
    });

    // Restore previous selection if it exists
    if (currentValue) {
      select.value = currentValue;
    }
  } catch (error) {
    console.error("Failed to load music:", error);
  }
}

async function loadLLMOptions() {
  try {
    const [modelsData, stylesData, templatesData] = await Promise.all([
      api.llm.models(),
      api.llm.styles(),
      api.llm.templates(),
    ]);

    // Models
    const modelSelect = document.getElementById("llm-model");
    if (modelSelect) {
      modelSelect.innerHTML = "";
      modelsData.models.forEach((model) => {
        const option = document.createElement("option");
        option.value = model.id;
        option.textContent = `${model.name} (${model.provider})`;
        modelSelect.appendChild(option);
      });
    }

    // Styles
    const styleSelect = document.getElementById("llm-style");
    if (styleSelect) {
      styleSelect.innerHTML = "";
      stylesData.styles.forEach((style) => {
        const option = document.createElement("option");
        option.value = style.id;
        option.textContent = `${style.name} - ${style.description}`;
        styleSelect.appendChild(option);
      });
    }

    // Templates
    const templateSelect = document.getElementById("llm-template");
    if (templateSelect) {
      templateSelect.innerHTML = "";
      templatesData.templates.forEach((template) => {
        const option = document.createElement("option");
        option.value = template.id;
        option.textContent = `${template.name} - ${template.description}`;
        templateSelect.appendChild(option);
      });
    }
  } catch (error) {
    console.error("Failed to load LLM options:", error);
  }
}

async function loadProsodyReferences() {
  try {
    const data = await api.prosody.references();
    const select = document.getElementById("prosody-reference");

    select.innerHTML = "";
    data.references.forEach((ref) => {
      const option = document.createElement("option");
      option.value = ref.id;
      option.textContent = `${ref.name} - ${ref.description}`;
      select.appendChild(option);
    });
  } catch (error) {
    console.error("Failed to load prosody references:", error);
  }
}

async function loadTemplates() {
  try {
    const data = await api.templates.list();
    const select = document.getElementById("template-select");

    if (!select) return;

    select.innerHTML = '<option value="">Load a template...</option>';

    // Default templates
    const defaultGroup = document.createElement("optgroup");
    defaultGroup.label = "Default Templates";
    data.default_templates.forEach((template) => {
      const option = document.createElement("option");
      option.value = `default:${template.id}`;
      option.textContent = `${template.name} - ${template.description}`;
      defaultGroup.appendChild(option);
    });
    select.appendChild(defaultGroup);

    // Custom templates
    if (data.custom_templates.length > 0) {
      const customGroup = document.createElement("optgroup");
      customGroup.label = "Custom Templates";
      data.custom_templates.forEach((template) => {
        const option = document.createElement("option");
        option.value = `custom:${template.id}`;
        option.textContent = template.name;
        customGroup.appendChild(option);
      });
      select.appendChild(customGroup);
    }
  } catch (error) {
    console.error("Failed to load templates:", error);
  }
}

function initAllSliders() {
  // Music sliders
  utils.initSlider("music-volume", {
    min: -20,
    max: 0,
    step: 0.5,
    value: -6,
    unit: " dB",
    decimals: 1,
  });
  utils.initSlider("music-entry", {
    min: 0,
    max: 10000,
    step: 100,
    value: 0,
    unit: " ms",
  });
  utils.initSlider("music-crossfade", {
    min: 0,
    max: 5000,
    step: 100,
    value: 2000,
    unit: " ms",
  });

  // Voice sliders
  utils.initSlider("voice-stability", {
    min: 0,
    max: 1,
    step: 0.05,
    value: 0.5,
    decimals: 2,
  });
  utils.initSlider("voice-similarity", {
    min: 0,
    max: 1,
    step: 0.05,
    value: 0.75,
    decimals: 2,
  });
  utils.initSlider("voice-style", {
    min: 0,
    max: 1,
    step: 0.05,
    value: 0,
    decimals: 2,
  });
  utils.initSlider("voice-speed", {
    min: 0.5,
    max: 2,
    step: 0.05,
    value: 1.0,
    unit: "x",
    decimals: 2,
  });

  // Mix sliders
  utils.initSlider("mix-reverb", {
    min: 0,
    max: 100,
    step: 1,
    value: 25,
    unit: "%",
  });
  utils.initSlider("mix-reverb-decay", {
    min: 0.3,
    max: 5,
    step: 0.1,
    value: 1.5,
    unit: "s",
    decimals: 1,
  });
  utils.initSlider("mix-compression", {
    min: 1,
    max: 10,
    step: 0.5,
    value: 2,
    unit: ":1",
    decimals: 1,
  });
  utils.initSlider("mix-deesser", {
    min: -20,
    max: 0,
    step: 1,
    value: -6,
    unit: " dB",
  });
  utils.initSlider("mix-eq-low", {
    min: 20,
    max: 200,
    step: 10,
    value: 80,
    unit: " Hz",
  });
  utils.initSlider("mix-eq-high", {
    min: 5000,
    max: 20000,
    step: 500,
    value: 12000,
    unit: " Hz",
  });
  utils.initSlider("mix-pitch", {
    min: -12,
    max: 12,
    step: 1,
    value: 0,
    unit: " st",
  });
  utils.initSlider("mix-normalization", {
    min: -24,
    max: -12,
    step: 0.5,
    value: -16,
    unit: " LUFS",
    decimals: 1,
  });

  // Prosody sliders
  utils.initSlider("prosody-intensity", {
    min: 0,
    max: 1,
    step: 0.05,
    value: 0,
    decimals: 2,
  });

  // LLM sliders
  utils.initSlider("llm-temperature", {
    min: 0,
    max: 2,
    step: 0.1,
    value: 0.7,
    decimals: 1,
  });
}

function updateAllSliderDisplays() {
  document.querySelectorAll(".slider-input").forEach((slider) => {
    const valueDisplay = document.getElementById(`${slider.id}-value`);
    if (valueDisplay) {
      valueDisplay.textContent = slider.value;
    }
  });
}

function setupEventListeners() {
  // Text source toggle
  document.getElementById("text-source")?.addEventListener("change", (e) => {
    const llmPanel = document.getElementById("llm-panel");
    if (llmPanel) {
      llmPanel.style.display = e.target.value === "llm" ? "block" : "none";
    }
  });

  // Generate text button
  document
    .getElementById("generate-text-btn")
    ?.addEventListener("click", generateText);

  // Generate audio button
  document
    .getElementById("generate-btn")
    ?.addEventListener("click", generateAudio);

  // Save stimulus button
  document.getElementById("save-btn")?.addEventListener("click", saveStimulus);

  // Template select
  document
    .getElementById("template-select")
    ?.addEventListener("change", loadTemplate);

  // Save as template button
  document
    .getElementById("save-template-btn")
    ?.addEventListener("click", saveAsTemplate);

  // Speech text change
  document
    .getElementById("speech-text")
    ?.addEventListener("input", utils.debounce(updateWordCount, 300));

  // Stimulus ID change
  document.getElementById("stimulus-id")?.addEventListener("change", (e) => {
    currentStimulusId = e.target.value;
  });

  // Music track change - fetch duration and calculate target words
  document
    .getElementById("music-track")
    ?.addEventListener("change", async (e) => {
      await onMusicTrackChange(e.target.value);
    });

  // Voice speed change - recalculate target words
  document.getElementById("voice-speed")?.addEventListener("input", () => {
    recalculateTargetWords();
    updateWordCount();
  });

  // Speech entry change - recalculate target words
  document.getElementById("music-entry")?.addEventListener("input", () => {
    recalculateTargetWords();
  });

  // Crossfade change - NO LONGER affects word count, but keep listener for UI updates
  document.getElementById("music-crossfade")?.addEventListener("input", () => {
    // Crossfade is handled by the mixer, not word count
    // No need to recalculate target words
  });

  // Manual target words input change
  document.getElementById("target-words")?.addEventListener("input", (e) => {
    const value = parseInt(e.target.value);
    if (value && value > 0) {
      currentTargetWords = value;
      updateTargetWordsDisplay();
      updateWordCount();
    }
  });

  // Auto-calculate button click
  document
    .getElementById("auto-calc-words-btn")
    ?.addEventListener("click", async () => {
      const musicPath = document.getElementById("music-track")?.value;
      if (musicPath) {
        await onMusicTrackChange(musicPath);
        utils.showSuccess(`Target words set to ${currentTargetWords}`);
      } else {
        utils.showError("Please select a music track first");
      }
    });

  // NEW: Music upload button click - triggers hidden file input
  document
    .getElementById("upload-music-btn")
    ?.addEventListener("click", () => {
      document.getElementById("music-upload-input")?.click();
    });

  // NEW: Music file input change - handles the actual upload
  document
    .getElementById("music-upload-input")
    ?.addEventListener("change", handleMusicUpload);
}

// NEW: Handle music file upload
async function handleMusicUpload(e) {
  const file = e.target.files?.[0];
  if (!file) return;

  // Validate file type
  const allowedTypes = [".mp3", ".wav", ".m4a", ".ogg", ".flac"];
  const ext = "." + file.name.split(".").pop().toLowerCase();
  if (!allowedTypes.includes(ext)) {
    utils.showError(
      `Invalid file type. Allowed: ${allowedTypes.join(", ")}`
    );
    e.target.value = ""; // Reset input
    return;
  }

  // Validate file size (max 50MB)
  const maxSize = 50 * 1024 * 1024;
  if (file.size > maxSize) {
    utils.showError("File too large. Maximum size is 50MB.");
    e.target.value = "";
    return;
  }

  const uploadBtn = document.getElementById("upload-music-btn");
  const originalText = uploadBtn?.textContent;
  
  try {
    if (uploadBtn) {
      uploadBtn.textContent = "Uploading...";
      uploadBtn.disabled = true;
    }

    utils.showInfo(`Uploading ${file.name}...`);

    // Upload the file
    const result = await api.music.upload(file);

    if (result.success) {
      // Reload music dropdown to show new track
      await loadMusic();

      // Select the newly uploaded track
      const select = document.getElementById("music-track");
      if (select && result.track?.path) {
        select.value = result.track.path;
        // Trigger change event to load duration
        await onMusicTrackChange(result.track.path);
      }

      // Show success with duration info
      let successMsg = `Uploaded: ${result.track.name}`;
      if (result.track.duration_formatted) {
        successMsg += ` (${result.track.duration_formatted})`;
      }
      utils.showSuccess(successMsg);
    } else {
      utils.showError("Upload failed");
    }
  } catch (error) {
    console.error("Music upload failed:", error);
    utils.showError("Upload failed: " + error.message);
  } finally {
    // Reset the file input so the same file can be uploaded again if needed
    e.target.value = "";
    
    if (uploadBtn) {
      uploadBtn.textContent = originalText || "📁 Upload";
      uploadBtn.disabled = false;
    }
  }
}

// Calculate target words accounting for voice speed and speech entry
// Speech fills 100% of available time (no artificial buffer)
function calculateTargetWordsFromDuration(durationMs) {
  if (!durationMs || durationMs <= 0) return null;

  // Get voice speed (default 1.0)
  const voiceSpeed = parseFloat(
    document.getElementById("voice-speed")?.value || 1.0
  );

  // Get speech entry delay (music plays before voice starts)
  const speechEntryMs = parseInt(
    document.getElementById("music-entry")?.value || 0
  );

  // Calculate effective duration for speech
  // Only subtract speech entry delay (user-controlled via UI)
  // Crossfade is handled by the audio mixer, not word count
  const effectiveDurationMs = durationMs - speechEntryMs;

  if (effectiveDurationMs <= 0) {
    console.warn("Effective duration is zero or negative");
    return null;
  }

  // Adjust WPM based on voice speed
  // Faster speed (>1.0) = more words per minute = more words fit
  // Slower speed (<1.0) = fewer words per minute = fewer words fit
  const adjustedWpm = BASE_TTS_WPM * voiceSpeed;

  // Calculate raw target words
  const effectiveDurationMinutes = effectiveDurationMs / 1000 / 60;
  let targetWords = Math.round(effectiveDurationMinutes * adjustedWpm);

  // Apply safety buffer (1.0 = 100% = no reduction, fills entire duration)
  targetWords = Math.round(targetWords * TTS_SAFETY_BUFFER);

  console.log(
    `Music: ${durationMs}ms, Entry: ${speechEntryMs}ms`
  );
  console.log(
    `Effective: ${effectiveDurationMs}ms, Speed: ${voiceSpeed}x, WPM: ${adjustedWpm}`
  );
  console.log(
    `Target words (100% fill): ${targetWords}`
  );

  return targetWords;
}

// Handle music track selection change
async function onMusicTrackChange(trackPath) {
  if (!trackPath) {
    // No music selected - clear target words
    currentTargetWords = null;
    currentMusicDuration = null;
    updateTargetWordsDisplay();
    updateMusicDurationDisplay();
    updateWordCount();
    return;
  }

  try {
    // Get current voice parameters for accurate calculation
    const voiceSpeed = parseFloat(
      document.getElementById("voice-speed")?.value || 1.0
    );
    const speechEntryMs = parseInt(
      document.getElementById("music-entry")?.value || 0
    );
    const crossfadeMs = parseInt(
      document.getElementById("music-crossfade")?.value || 2000
    );

    // Fetch duration from API with voice parameters for accurate calculation
    const data = await api.music.getDuration(
      trackPath,
      voiceSpeed,
      speechEntryMs,
      crossfadeMs
    );

    currentMusicDuration = data.duration_ms;

    // Use backend-calculated target words if available, otherwise calculate locally
    if (data.target_words) {
      currentTargetWords = data.target_words;
    } else {
      currentTargetWords = calculateTargetWordsFromDuration(currentMusicDuration);
    }

    // Update UI
    updateMusicDurationDisplay();
    updateTargetWordsDisplay();
    updateWordCount();

    // Auto-fill the target words input
    const targetWordsInput = document.getElementById("target-words");
    if (targetWordsInput && currentTargetWords) {
      targetWordsInput.value = currentTargetWords;
    }

    console.log(
      `Music selected: ${trackPath}, Duration: ${data.duration_formatted}, Target words: ${currentTargetWords}`
    );
  } catch (error) {
    console.error("Failed to get music duration:", error);
    currentMusicDuration = null;
    currentTargetWords = null;
    updateMusicDurationDisplay();
    updateTargetWordsDisplay();
    updateWordCount();
  }
}

// Recalculate target words when voice speed or speech entry changes
function recalculateTargetWords() {
  if (!currentMusicDuration) return;

  currentTargetWords = calculateTargetWordsFromDuration(currentMusicDuration);

  // Update the input field
  const targetWordsInput = document.getElementById("target-words");
  if (targetWordsInput && currentTargetWords) {
    targetWordsInput.value = currentTargetWords;
  }

  updateTargetWordsDisplay();
  updateWordCount();
}

// Update music duration display in UI
function updateMusicDurationDisplay() {
  const durationDisplay = document.getElementById("music-duration-display");
  if (durationDisplay) {
    if (currentMusicDuration) {
      const formatted = utils.formatDuration(currentMusicDuration);
      durationDisplay.textContent = `Duration: ${formatted}`;
      durationDisplay.style.display = "block";
    } else {
      durationDisplay.textContent = "";
      durationDisplay.style.display = "none";
    }
  }
}

// Update target words display in UI
function updateTargetWordsDisplay() {
  const targetDisplay = document.getElementById("target-words-display");
  const targetInfoBox = document.getElementById("target-words-info");

  if (currentTargetWords && currentMusicDuration) {
    const voiceSpeed = parseFloat(
      document.getElementById("voice-speed")?.value || 1.0
    );
    const speechEntryMs = parseInt(
      document.getElementById("music-entry")?.value || 0
    );

    // Estimate duration based on target words and speed
    const adjustedWpm = BASE_TTS_WPM * voiceSpeed;
    const estimatedMinutes = currentTargetWords / adjustedWpm;
    const estimatedMs = estimatedMinutes * 60 * 1000;

    let displayText = `<strong>${currentTargetWords} words</strong> (~${utils.formatDuration(
      estimatedMs
    )} speech)`;
    displayText += `<br><span style="font-size: 0.8rem;">`;
    displayText += `Music: ${utils.formatDuration(currentMusicDuration)}`;
    if (speechEntryMs > 0) {
      displayText += ` | Entry: ${(speechEntryMs / 1000).toFixed(1)}s`;
    }
    if (voiceSpeed !== 1.0) {
      displayText += ` | Speed: ${voiceSpeed}x`;
    }
    displayText += ` | Fill: 100%`;
    displayText += `</span>`;

    if (targetDisplay) {
      targetDisplay.innerHTML = displayText;
    }
    if (targetInfoBox) {
      targetInfoBox.style.display = "block";
    }
  } else if (currentTargetWords) {
    // Target words set manually without music
    const voiceSpeed = parseFloat(
      document.getElementById("voice-speed")?.value || 1.0
    );
    const adjustedWpm = BASE_TTS_WPM * voiceSpeed;
    const estimatedMinutes = currentTargetWords / adjustedWpm;
    const estimatedMs = estimatedMinutes * 60 * 1000;

    if (targetDisplay) {
      targetDisplay.innerHTML = `<strong>${currentTargetWords} words</strong> (~${utils.formatDuration(
        estimatedMs
      )})`;
    }
    if (targetInfoBox) {
      targetInfoBox.style.display = "block";
    }
  } else {
    if (targetDisplay) {
      targetDisplay.innerHTML = "";
    }
    if (targetInfoBox) {
      targetInfoBox.style.display = "none";
    }
  }
}

function updateWordCount() {
  const text = document.getElementById("speech-text")?.value || "";
  const wordCount = utils.countWords(text);

  // Get current voice speed to estimate duration
  const voiceSpeed = parseFloat(
    document.getElementById("voice-speed")?.value || 1.0
  );
  const adjustedWpm = BASE_TTS_WPM * voiceSpeed;
  const estimatedMinutes = wordCount / adjustedWpm;
  const estimatedMs = estimatedMinutes * 60 * 1000;

  const countDisplay = document.getElementById("word-count");
  if (countDisplay) {
    let displayText = `${wordCount} words • ~${utils.formatDuration(
      estimatedMs
    )}`;

    // Show comparison with target if set
    if (currentTargetWords) {
      const diff = wordCount - currentTargetWords;
      const diffStr = diff > 0 ? `+${diff}` : `${diff}`;
      const percentage = Math.round((wordCount / currentTargetWords) * 100);

      let status;
      // Tolerance: Allow ±5% of target
      const tolerance = Math.max(20, Math.round(currentTargetWords * 0.05));
      if (Math.abs(diff) <= tolerance) {
        status = "✅ Good!";
      } else if (diff > 0) {
        status = "⚠️ too long - speech may exceed music";
      } else {
        status = "⚠️ too short - may have silence at end";
      }

      displayText += ` | Target: ${currentTargetWords} (${diffStr}, ${percentage}%) ${status}`;
    }

    countDisplay.textContent = displayText;
  }
}

async function generateText() {
  const topic = document.getElementById("llm-topic")?.value;
  if (!topic) {
    utils.showError("Please enter a topic");
    return;
  }

  const btn = document.getElementById("generate-text-btn");
  utils.setLoading(btn, true, "Generating...");

  try {
    // Get target words from input or calculated value
    let targetWords = null;
    const targetWordsInput = document.getElementById("target-words");
    if (targetWordsInput && targetWordsInput.value) {
      targetWords = parseInt(targetWordsInput.value);
    } else if (currentTargetWords) {
      targetWords = currentTargetWords;
    }

    // Get custom prompt if provided
    const customPrompt = document.getElementById("llm-custom-prompt")?.value?.trim() || null;

    // Build the API request
    const requestData = {
      topic: topic,
      style: document.getElementById("llm-style")?.value || "default",
      template: document.getElementById("llm-template")?.value || "about_topic",
      model:
        document.getElementById("llm-model")?.value ||
        "claude-3-sonnet-20240229",
      temperature: parseFloat(
        document.getElementById("llm-temperature")?.value || 0.7
      ),
      max_tokens: 1500, // Increased to allow for longer texts
      target_words: targetWords,
    };

    // If custom prompt is provided, it replaces the template
    if (customPrompt) {
      requestData.custom_user_prompt = customPrompt;
    }

    const result = await api.llm.generate(requestData);

    document.getElementById("speech-text").value = result.text;
    updateWordCount();

    // Show generated vs target comparison
    const actualWords = result.actual_words || utils.countWords(result.text);
    let successMsg = `Generated ${actualWords} words`;
    if (result.target_words) {
      const diff = actualWords - result.target_words;
      const diffStr = diff >= 0 ? `+${diff}` : `${diff}`;
      successMsg += ` (target: ${result.target_words}, ${diffStr})`;
    }
    
    // Note if custom prompt was used
    if (customPrompt) {
      successMsg += " [custom prompt]";
    }
    
    // Show warning from backend if present
    if (result.word_count_warning) {
      utils.showWarning(result.word_count_warning);
    } else {
      utils.showSuccess(successMsg);
    }
  } catch (error) {
    utils.showError("Text generation failed: " + error.message);
  } finally {
    utils.setLoading(btn, false);
  }
}

function getFormData() {
  return {
    stimulus_id:
      document.getElementById("stimulus-id")?.value || currentStimulusId,
    speech_text: document.getElementById("speech-text")?.value || "",
    voice_id: document.getElementById("voice-id")?.value || "",
    voice_model:
      document.getElementById("voice-model")?.value || "eleven_multilingual_v2",
    voice_stability: parseFloat(
      document.getElementById("voice-stability")?.value || 0.5
    ),
    voice_similarity_boost: parseFloat(
      document.getElementById("voice-similarity")?.value || 0.75
    ),
    voice_style_exaggeration: parseFloat(
      document.getElementById("voice-style")?.value || 0
    ),
    voice_speaker_boost:
      document.getElementById("voice-speaker-boost")?.checked ?? true,
    voice_speed: parseFloat(
      document.getElementById("voice-speed")?.value || 1.0
    ),
    music_track: document.getElementById("music-track")?.value || null,
    music_volume_db: parseFloat(
      document.getElementById("music-volume")?.value || -6
    ),
    music_speech_entry_ms: parseInt(
      document.getElementById("music-entry")?.value || 0
    ),
    music_crossfade_ms: parseInt(
      document.getElementById("music-crossfade")?.value || 2000
    ),
    reverb_mix: parseFloat(document.getElementById("mix-reverb")?.value || 25),
    reverb_decay: parseFloat(
      document.getElementById("mix-reverb-decay")?.value || 1.5
    ),
    compression_ratio: parseFloat(
      document.getElementById("mix-compression")?.value || 2
    ),
    deesser_threshold: parseFloat(
      document.getElementById("mix-deesser")?.value || -6
    ),
    eq_low_cut: parseInt(document.getElementById("mix-eq-low")?.value || 80),
    eq_high_cut: parseInt(
      document.getElementById("mix-eq-high")?.value || 12000
    ),
    pitch_shift: parseInt(document.getElementById("mix-pitch")?.value || 0),
    normalization_lufs: parseFloat(
      document.getElementById("mix-normalization")?.value || -16
    ),
    prosody_reference:
      document.getElementById("prosody-reference")?.value || "none",
    prosody_intensity: parseFloat(
      document.getElementById("prosody-intensity")?.value || 0
    ),
    save_to_db: true,
  };
}

async function generateAudio() {
  const formData = getFormData();

  if (!formData.speech_text) {
    utils.showError("Please enter speech text");
    return;
  }

  if (!formData.voice_id) {
    utils.showError("Please select a voice");
    return;
  }

  const btn = document.getElementById("generate-btn");
  utils.setLoading(btn, true, "Generating...");

  // Show progress
  const progressContainer = document.getElementById("generation-progress");
  if (progressContainer) {
    progressContainer.style.display = "block";
    progressContainer.innerHTML = `
            <div class="progress-bar"><div class="progress-bar-fill" style="width: 0%"></div></div>
            <p style="margin-top: 0.5rem; font-size: 0.85rem; color: var(--text-secondary);">
                Synthesizing speech... This may take a minute.
            </p>
        `;
  }

  try {
    const result = await api.generate.direct(formData);

    if (result.status === "generated" && result.audio_url) {
      // Show audio preview with auto-play enabled
      showAudioPreview(result.audio_url, true);

      // Show duration comparison with music
      let successMsg = `Generated ${utils.formatDuration(
        result.duration_ms
      )} audio`;
      if (currentMusicDuration) {
        const diff = result.duration_ms - currentMusicDuration;
        const diffFormatted = utils.formatDuration(Math.abs(diff));
        // Allow 5 seconds tolerance for "matches"
        if (Math.abs(diff) < 5000) {
          successMsg += ` ✅ (matches music!)`;
        } else if (diff > 0) {
          successMsg += ` ⚠️ (+${diffFormatted} longer than music)`;
        } else {
          successMsg += ` ⚠️ (-${diffFormatted} shorter than music)`;
        }
      }
      utils.showSuccess(successMsg);

      // Update current stimulus ID
      currentStimulusId = result.stimulus_id;
      document.getElementById("stimulus-id").value = currentStimulusId;
      isEditing = true;
    } else if (result.status === "failed") {
      utils.showError(
        "Generation failed: " + (result.error || "Unknown error")
      );
    }
  } catch (error) {
    utils.showError("Generation failed: " + error.message);
  } finally {
    utils.setLoading(btn, false);
    if (progressContainer) {
      progressContainer.style.display = "none";
    }
  }
}

function showAudioPreview(audioUrl, autoPlay = false) {
  const container = document.getElementById("audio-preview");
  if (container) {
    container.innerHTML = `
            <div class="audio-player">
                <div class="audio-player-label">Generated Audio</div>
                <audio id="preview-audio" controls src="${audioUrl}" style="width: 100%;"></audio>
                <div style="margin-top: 0.5rem; display: flex; gap: 0.5rem;">
                    <a href="${audioUrl}" download class="btn btn-sm btn-secondary">Download MP3</a>
                    <button class="btn btn-sm btn-secondary" onclick="utils.copyToClipboard('${window.location.origin}${audioUrl}')">Copy URL</button>
                </div>
            </div>
        `;

    // Auto-play if requested (for fresh generations)
    if (autoPlay) {
      const audioElement = document.getElementById("preview-audio");
      if (audioElement) {
        audioElement.play().catch((err) => {
          // Browser may block auto-play without user interaction
          console.log("Auto-play prevented by browser:", err);
        });
      }
    }
  }
}

async function saveStimulus() {
  const formData = getFormData();

  // Get target words
  let targetWords = null;
  const targetWordsInput = document.getElementById("target-words");
  if (targetWordsInput && targetWordsInput.value) {
    targetWords = parseInt(targetWordsInput.value);
  } else if (currentTargetWords) {
    targetWords = currentTargetWords;
  }

  const stimulusData = {
    id: formData.stimulus_id,
    music: {
      track: formData.music_track || "",
      volume_db: formData.music_volume_db,
      speech_entry_ms: formData.music_speech_entry_ms,
      crossfade_ms: formData.music_crossfade_ms,
    },
    voice: {
      model: formData.voice_model,
      voice_id: formData.voice_id,
      stability: formData.voice_stability,
      similarity_boost: formData.voice_similarity_boost,
      style_exaggeration: formData.voice_style_exaggeration,
      speaker_boost: formData.voice_speaker_boost,
      speed: formData.voice_speed,
    },
    text: {
      source: document.getElementById("text-source")?.value || "manual",
      speech_text: formData.speech_text,
      target_words: targetWords,
    },
    mix: {
      reverb_mix: formData.reverb_mix,
      reverb_decay: formData.reverb_decay,
      compression_ratio: formData.compression_ratio,
      deesser_threshold: formData.deesser_threshold,
      eq_low_cut: formData.eq_low_cut,
      eq_high_cut: formData.eq_high_cut,
      pitch_shift: formData.pitch_shift,
      normalization_lufs: formData.normalization_lufs,
    },
    prosody: {
      reference: formData.prosody_reference,
      intensity: formData.prosody_intensity,
    },
  };

  try {
    if (isEditing) {
      await api.stimuli.update(formData.stimulus_id, stimulusData);
      utils.showSuccess("Stimulus updated");
    } else {
      await api.stimuli.create(stimulusData);
      utils.showSuccess("Stimulus saved");
      isEditing = true;
    }
  } catch (error) {
    utils.showError("Failed to save: " + error.message);
  }
}

async function loadTemplate(e) {
  const value = e.target.value;
  if (!value) return;

  const [type, templateId] = value.split(":");

  try {
    const result = await api.templates.get(templateId);
    const template = result.template;

    // Apply template values
    if (template.voice) {
      document.getElementById("voice-model").value =
        template.voice.model || "eleven_multilingual_v2";
      document.getElementById("voice-id").value = template.voice.voice_id || "";
      document.getElementById("voice-stability").value =
        template.voice.stability || 0.5;
      document.getElementById("voice-similarity").value =
        template.voice.similarity_boost || 0.75;
      document.getElementById("voice-style").value =
        template.voice.style_exaggeration || 0;
      document.getElementById("voice-speed").value =
        template.voice.speed || 1.0;
      document.getElementById("voice-speaker-boost").checked =
        template.voice.speaker_boost ?? true;
    }

    if (template.mix) {
      document.getElementById("mix-reverb").value =
        template.mix.reverb_mix || 25;
      document.getElementById("mix-reverb-decay").value =
        template.mix.reverb_decay || 1.5;
      document.getElementById("mix-compression").value =
        template.mix.compression_ratio || 2;
      document.getElementById("mix-deesser").value =
        template.mix.deesser_threshold || -6;
      document.getElementById("mix-eq-low").value =
        template.mix.eq_low_cut || 80;
      document.getElementById("mix-eq-high").value =
        template.mix.eq_high_cut || 12000;
      document.getElementById("mix-pitch").value =
        template.mix.pitch_shift || 0;
      document.getElementById("mix-normalization").value =
        template.mix.normalization_lufs || -16;
    }

    if (template.prosody) {
      document.getElementById("prosody-reference").value =
        template.prosody.reference || "none";
      document.getElementById("prosody-intensity").value =
        template.prosody.intensity || 0;
    }

    updateAllSliderDisplays();

    // Recalculate target words with new voice speed
    recalculateTargetWords();

    utils.showSuccess(`Loaded template: ${template.name || templateId}`);

    // Reset select
    e.target.value = "";
  } catch (error) {
    utils.showError("Failed to load template: " + error.message);
  }
}

async function saveAsTemplate() {
  const name = prompt("Enter template name:");
  if (!name) return;

  const formData = getFormData();

  const templateData = {
    name: name,
    music: {
      track: "",
      volume_db: formData.music_volume_db,
      speech_entry_ms: formData.music_speech_entry_ms,
      crossfade_ms: formData.music_crossfade_ms,
    },
    voice: {
      model: formData.voice_model,
      voice_id: formData.voice_id,
      stability: formData.voice_stability,
      similarity_boost: formData.voice_similarity_boost,
      style_exaggeration: formData.voice_style_exaggeration,
      speaker_boost: formData.voice_speaker_boost,
      speed: formData.voice_speed,
    },
    text: {
      source: document.getElementById("text-source")?.value || "manual",
    },
    mix: {
      reverb_mix: formData.reverb_mix,
      reverb_decay: formData.reverb_decay,
      compression_ratio: formData.compression_ratio,
      deesser_threshold: formData.deesser_threshold,
      eq_low_cut: formData.eq_low_cut,
      eq_high_cut: formData.eq_high_cut,
      pitch_shift: formData.pitch_shift,
      normalization_lufs: formData.normalization_lufs,
    },
    prosody: {
      reference: formData.prosody_reference,
      intensity: formData.prosody_intensity,
    },
  };

  try {
    const result = await api.templates.create(templateData);
    utils.showSuccess(`Template "${name}" saved`);
    await loadTemplates(); // Refresh template list
  } catch (error) {
    utils.showError("Failed to save template: " + error.message);
  }
}

// Make initGenerator globally available
window.initGenerator = initGenerator;
