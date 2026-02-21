
const imageInput = document.getElementById('imageInput');
const preview = document.getElementById('preview');
const submitBtn = document.getElementById('submitBtn');
const output = document.getElementById('output');
const langToggle = document.getElementById('langToggle');

// Preview uploaded image
imageInput.addEventListener('change', () => {
  const file = imageInput.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    preview.src = e.target.result;
    preview.style.display = 'block';
  };
  reader.readAsDataURL(file);
});

// Submit for processing
submitBtn.addEventListener('click', async () => {
  const files = imageInput.files;
  if (!files.length) {
    output.innerHTML = '<div class="error">Please select an image.</div>';
    return;
  }
  submitBtn.disabled = true;
  output.textContent = 'Processing...';

  const formData = new FormData();
  Array.from(files).forEach(file => formData.append('images', file));
  formData.append('language', langToggle.value);

  try {
    const res = await fetch('/process', { method: 'POST', body: formData });
    let data = await res.json();
    renderResults(data);
  } catch (err) {
    output.innerHTML = `<div class="error">Error: ${String(err)}</div>`;
  } finally {
    submitBtn.disabled = false;
  }
});

// Render results into HTML cards
function renderResults(results) {
  if (!Array.isArray(results) || !results.length) {
    output.innerHTML = '<div class="error">No results.</div>';
    return;
  }

  const lang = langToggle.value;
  const labels = {
    uses: lang === 'kn' ? 'ಉಪಯೋಗಗಳು' : 'Uses',
    sideEffects: lang === 'kn' ? 'ಅಡ್ಡ ಪರಿಣಾಮಗಳು' : 'Side Effects',
    expiry: lang === 'kn' ? 'ಮುಕ್ತಾಯ ದಿನಾಂಕ' : 'Expiry',
    alternates: lang === 'kn' ? 'ಪರ್ಯಾಯಗಳು' : 'Alternates'
  };

  output.innerHTML = results.map(r => {
    const name = r.extracted_name || 'Unknown';
    const expiry = r.expiry || 'Not found';
    const meds = r.medicines || [];
    if (!meds.length) {
  return `
    <div class="card">
      <div class="error">
        ${lang === 'kn'
          ? 'ಔಷಧಿ ಪತ್ತೆಯಾಗಿಲ್ಲ'
          : 'No medicine detected'}
      </div>
    </div>
  `;
}


    return meds.map(m => `
      <div class="card">
        <div class="result-name">${m.name}</div>
        <div class="result-expiry">${labels.expiry}: ${expiry}</div>

        <div class="uses-title">${labels.uses}</div>
        <div class="full-text">${Array.isArray(m.uses_summary) ? m.uses_summary.join('<br>') : m.uses_summary}</div>

        <div class="se-title">${labels.sideEffects}</div>
        <div class="full-text">${Array.isArray(m.side_effects_summary) ? m.side_effects_summary.join('<br>') : m.side_effects_summary}</div>

        ${Array.isArray(m.alternates) && m.alternates.length
          ? `<h4>${labels.alternates}</h4><ul>${m.alternates.map(a => `<li>${a}</li>`).join('')}</ul>`
          : ''}
      </div>
    `).join('');
  }).join('');
}