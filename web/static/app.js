/**
 * LinkedIn Network Analyzer — Frontend Logic
 *
 * Handles drag-and-drop / click-to-upload, file validation,
 * form submission to POST /analyze, KPI rendering with count-up
 * animation, and ZIP download via token.
 */

(function () {
  'use strict';

  // ── DOM References ──────────────────────────────────────────
  const uploadZone      = document.getElementById('upload-zone');
  const fileInput       = document.getElementById('file-input');
  const uploadIcon      = document.getElementById('upload-icon');
  const uploadText      = document.getElementById('upload-text');
  const uploadHint      = document.getElementById('upload-hint');
  const filtersToggle   = document.getElementById('filters-toggle');
  const filtersPanel    = document.getElementById('filters-panel');
  const btnAnalyze      = document.getElementById('btn-analyze');
  const btnAnalyzeText  = document.getElementById('btn-analyze-text');
  const errorMessage    = document.getElementById('error-message');
  const processingOverlay = document.getElementById('processing-overlay');
  const uploadCard      = document.getElementById('upload-card');
  const resultsSection  = document.getElementById('results-section');
  const kpiGrid         = document.getElementById('kpi-grid');
  const btnDownloadZip  = document.getElementById('btn-download-zip');
  const btnNewUpload    = document.getElementById('btn-new-upload');
  const instructionsToggle = document.getElementById('instructions-toggle');
  const instructionsBody   = document.getElementById('instructions-body');

  // ── State ───────────────────────────────────────────────────
  let selectedFile = null;
  let downloadUrl  = null;
  let zipBase64    = null;

  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

  // ── Upload Zone — Drag & Drop ───────────────────────────────
  uploadZone.addEventListener('click', () => fileInput.click());

  uploadZone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInput.click();
    }
  });

  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.stopPropagation();
    uploadZone.classList.add('dragover');
  });

  uploadZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    e.stopPropagation();
    uploadZone.classList.remove('dragover');
  });

  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    uploadZone.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelection(files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleFileSelection(fileInput.files[0]);
    }
  });

  // ── File Selection Handler ──────────────────────────────────
  function handleFileSelection(file) {
    hideError();

    // Validate extension
    if (!file.name.toLowerCase().endsWith('.csv')) {
      showError('Please select a <strong>.csv</strong> file. Other file types are not supported.');
      resetUploadZone();
      return;
    }

    // Validate size
    if (file.size > MAX_FILE_SIZE) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      showError(`File is too large (<strong>${sizeMB} MB</strong>). Maximum allowed size is 10 MB.`);
      resetUploadZone();
      return;
    }

    // Validate non-empty
    if (file.size === 0) {
      showError('The selected file is empty.');
      resetUploadZone();
      return;
    }

    selectedFile = file;

    // Update UI
    uploadZone.classList.add('has-file');
    uploadIcon.textContent = '✅';
    uploadText.innerHTML = `<strong>${escapeHtml(file.name)}</strong>`;
    const sizeMB = (file.size / 1024).toFixed(0);
    uploadHint.textContent = `${sizeMB} KB — Click to change file`;
    btnAnalyze.disabled = false;
  }

  function resetUploadZone() {
    selectedFile = null;
    fileInput.value = '';
    uploadZone.classList.remove('has-file');
    uploadIcon.textContent = '☁️';
    uploadText.innerHTML = '<strong>Click to browse</strong> or drag &amp; drop your CSV file here';
    uploadHint.textContent = 'Accepts .csv files up to 10 MB';
    btnAnalyze.disabled = true;
  }

  // ── Advanced Filters Toggle ─────────────────────────────────
  filtersToggle.addEventListener('click', () => {
    const isOpen = filtersPanel.classList.toggle('open');
    filtersToggle.classList.toggle('open', isOpen);
    filtersToggle.setAttribute('aria-expanded', isOpen);
    filtersPanel.setAttribute('aria-hidden', !isOpen);
  });

  // ── Instructions Accordion ──────────────────────────────────
  instructionsToggle.addEventListener('click', () => {
    const isOpen = instructionsBody.classList.toggle('open');
    instructionsToggle.classList.toggle('open', isOpen);
    instructionsToggle.setAttribute('aria-expanded', isOpen);
    instructionsBody.setAttribute('aria-hidden', !isOpen);
  });

  // ── Analyze Button ──────────────────────────────────────────
  btnAnalyze.addEventListener('click', () => {
    if (!selectedFile) return;
    submitAnalysis();
  });

  // ── Submit Analysis ─────────────────────────────────────────
  async function submitAnalysis() {
    hideError();
    setProcessingState(true);

    const formData = new FormData();
    formData.append('file', selectedFile);

    // Collect optional filters
    const role            = document.getElementById('filter-role').value;
    const company         = document.getElementById('filter-company').value.trim();
    const companyContains = document.getElementById('filter-company-contains').value.trim();
    const search          = document.getElementById('filter-search').value.trim();
    const location        = document.getElementById('filter-location').value.trim();

    if (role)            formData.append('role', role);
    if (company)         formData.append('company', company);
    if (companyContains) formData.append('company_contains', companyContains);
    if (search)          formData.append('search', search);
    if (location)        formData.append('location', location);

    try {
      const response = await fetch('/analyze', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        const detail = data.detail || 'An unexpected error occurred.';
        showError(detail);
        setProcessingState(false);
        return;
      }

      // Success — render results
      downloadUrl = data.download_url;
      zipBase64   = data.zip_base64 || null;
      renderResults(data.summary);
      setProcessingState(false);
      showResults();

    } catch (err) {
      console.error('Analysis request failed:', err);
      showError(
        'Unable to reach the server. Please check your connection and try again.'
      );
      setProcessingState(false);
    }
  }

  // ── Render KPI Results ──────────────────────────────────────
  function renderResults(summary) {
    kpiGrid.innerHTML = '';

    const kpis = [
      {
        key: 'total_connections',
        label: 'Total Connections',
        icon: '👥',
        featured: true,
      },
      {
        key: 'senior_contacts',
        label: 'Senior Contacts',
        icon: '⭐',
        featured: true,
      },
      { key: 'founders',      label: 'Founders',       icon: '🚀' },
      { key: 'c-suite',       label: 'C-Suite',        icon: '👔' },
      { key: 'directors',     label: 'Directors',      icon: '📋' },
      { key: 'entrepreneurs', label: 'Entrepreneurs',  icon: '💡' },
      {
        key: 'average_seniority_score',
        label: 'Avg Score',
        icon: '📈',
      },
      {
        key: 'contacts_with_email',
        label: 'With Email',
        icon: '✉️',
      },
    ];

    kpis.forEach((kpi) => {
      let value = summary[kpi.key];
      if (value === undefined || value === null) {
        // Try alternate key styles
        const altKey = kpi.key.replace(/-/g, '_');
        value = summary[altKey];
      }
      if (value === undefined || value === null) value = 0;

      const card = document.createElement('div');
      card.className = 'kpi-card' + (kpi.featured ? ' featured' : '');

      const valEl = document.createElement('div');
      valEl.className = 'kpi-card__value';
      valEl.textContent = '0';

      const labelEl = document.createElement('div');
      labelEl.className = 'kpi-card__label';
      labelEl.textContent = `${kpi.icon} ${kpi.label}`;

      card.appendChild(valEl);
      card.appendChild(labelEl);
      kpiGrid.appendChild(card);

      // Count-up animation
      animateValue(valEl, 0, value, 800);
    });
  }

  // ── Count-Up Animation ──────────────────────────────────────
  function animateValue(el, start, end, duration) {
    if (typeof end !== 'number' || isNaN(end)) {
      el.textContent = end;
      return;
    }

    const isFloat = !Number.isInteger(end);
    const range = end - start;
    const startTime = performance.now();

    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = start + range * eased;

      if (isFloat) {
        el.textContent = current.toFixed(1);
      } else {
        el.textContent = Math.round(current).toLocaleString();
      }

      if (progress < 1) {
        requestAnimationFrame(update);
      }
    }

    requestAnimationFrame(update);
  }

  // ── UI State Helpers ────────────────────────────────────────
  function setProcessingState(isProcessing) {
    if (isProcessing) {
      uploadCard.style.display = 'none';
      resultsSection.classList.remove('visible');
      processingOverlay.classList.add('visible');
    } else {
      processingOverlay.classList.remove('visible');
    }
  }

  function showResults() {
    uploadCard.style.display = 'none';
    resultsSection.classList.add('visible');
  }

  function showError(html) {
    errorMessage.innerHTML = html;
    errorMessage.classList.add('visible');
  }

  function hideError() {
    errorMessage.classList.remove('visible');
    errorMessage.innerHTML = '';
  }

  // ── Download Handler ────────────────────────────────────────
  btnDownloadZip.addEventListener('click', () => {
    if (zipBase64) {
      try {
        const binaryString = atob(zipBase64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: 'application/zip' });
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = 'linkedin_network_analysis.zip';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(blobUrl), 1500);
        return;
      } catch (e) {
        console.warn('Direct blob download failed, falling back to downloadUrl:', e);
      }
    }

    if (!downloadUrl) return;

    // Create a temporary link and click it
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = 'linkedin_network_analysis.zip';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  });

  // ── New Upload Handler ──────────────────────────────────────
  btnNewUpload.addEventListener('click', () => {
    resetUploadZone();
    hideError();
    downloadUrl = null;
    zipBase64 = null;
    resultsSection.classList.remove('visible');
    uploadCard.style.display = '';
    kpiGrid.innerHTML = '';
  });

  // ── Utility ─────────────────────────────────────────────────
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

})();
