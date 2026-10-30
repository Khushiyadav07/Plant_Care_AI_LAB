const $ = s => document.querySelector(s);
function analyze(img, cv) {
  const W = Math.min(360, img.naturalWidth), H = Math.round(img.naturalHeight * W / img.naturalWidth);
  const c = document.createElement('canvas'); c.width = W; c.height = H;
  const x = c.getContext('2d', { willReadFrequently: true }); x.drawImage(img, 0, 0, W, H);
  const p = x.getImageData(0, 0, W, H).data, o = cv.getContext('2d'); cv.width = W; cv.height = H;
  const ov = o.createImageData(W, H), q = ov.data; let n = [0, 0, 0, 0];
  for (let i = 0; i < p.length; i += 4) {
    const r = p[i] / 255, g = p[i + 1] / 255, b = p[i + 2] / 255, mx = Math.max(r, g, b), d = mx - Math.min(r, g, b);
    if (mx < .12 || d / mx < .18) continue;                      // shadows, white, grey backgrounds
    const h = 60 * (mx === r ? ((g - b) / d + 6) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4);
    const k = h >= 75 && h <= 170 ? 1 : h >= 42 && h < 75 ? 2 : (h < 42 || h >= 345) ? (mx < .7 ? 3 : 2) : 0;
    if (!k) continue; n[k]++;
    const col = k === 1 ? [90, 255, 150, 30] : k === 2 ? [255, 184, 77, 160] : [255, 87, 70, 190];
    q[i] = col[0]; q[i + 1] = col[1]; q[i + 2] = col[2]; q[i + 3] = col[3];
  }
  o.putImageData(ov, 0, 0);
  const t = n[1] + n[2] + n[3]; if (t < 200) return null;
  const f = v => Math.round(v / t * 1000) / 10;
  return { green: f(n[1]), yellow: f(n[2]), brown: f(n[3]) };
}
const bars = v => [['Healthy green', v.green, 'g'], ['Yellowing', v.yellow, 'y'], ['Browning / lesions', v.brown, 'b']]
  .map(([l, n, c]) => `<div class="vbar ${c}"><span>${l}</span><div><i style="width:${n}%"></i></div><b>${n}%</b></div>`).join('');

const inp = $('#leaf_image');
if (inp && $('#pimg')) inp.addEventListener('change', () => {
  const f = inp.files[0]; if (!f) return; const im = $('#pimg'), box = $('#scanbox');
  im.onload = () => {
    box.classList.remove('done'); box.classList.add('show', 'scan'); $('#vitals').innerHTML = '';
    const v = analyze(im, $('#pmap'));
    if (v) { $('#f-g').value = v.green; $('#f-y').value = v.yellow; $('#f-b').value = v.brown; }
    else { $('#f-g').value = ''; $('#f-y').value = ''; $('#f-b').value = ''; }
    setTimeout(() => {
      box.classList.remove('scan'); box.classList.add('done');
      if (v) $('#vitals').innerHTML = bars(v);
      else $('#vitals').innerHTML = '<p class="muted">Couldn’t read the colours. Try a plain background.</p>';
    }, 600);
  };
  im.src = URL.createObjectURL(f);
});
const lf = $('#leaf');
if (lf && $('#map')) {
  const run = () => analyze(lf, $('#map')); lf.complete && lf.naturalWidth ? run() : lf.addEventListener('load', run);
  $('#maptoggle').onchange = e => { $('#map').style.opacity = e.target.checked ? 1 : 0; };
}
document.querySelectorAll('[data-plan]').forEach(ol => {
  const k = 'plan-' + ol.dataset.plan; let s = {};
  try { s = JSON.parse(localStorage.getItem(k) || '{}'); } catch (e) {}
  ol.querySelectorAll('input').forEach((c, i) => { c.checked = !!s[i]; c.onchange = () => { s[i] = c.checked; try { localStorage.setItem(k, JSON.stringify(s)); } catch (e) {} }; });
});
// Optional legacy preview controls: guard them because most pages do not contain them.
const legacyInput = document.getElementById("imgInput");
const legacyPreview = document.getElementById("preview");
if (legacyInput && legacyPreview) {
  legacyInput.addEventListener("change", () => {
    const file = legacyInput.files && legacyInput.files[0];
    if (file) { legacyPreview.src = URL.createObjectURL(file); legacyPreview.style.display = "block"; }
  });
  if (legacyInput.form) legacyInput.form.addEventListener("submit", () => {
    const submitButton = document.getElementById("submitBtn");
    const spinner = document.getElementById("spinner");
    if (submitButton) submitButton.disabled = true;
    if (spinner) spinner.style.display = "block";
  });
}
let isSpeaking = false;

function toggleVoiceSpeech() {
    const textElement = document.getElementById('diagnosis-text');
    const titleElement = document.getElementById('plant-title');
    const btn = document.getElementById('speak-btn');

    if (!('speechSynthesis' in window)) {
        alert("Your browser does not support text-to-speech.");
        return;
    }

    if (isSpeaking) {
        window.speechSynthesis.cancel();
        isSpeaking = false;
        btn.innerHTML = "🔊 Listen to Advice";
        return;
    }

    const textToRead = (titleElement ? titleElement.innerText + ". " : "") + 
                       (textElement ? textElement.innerText : "");

    const utterance = new SpeechSynthesisUtterance(textToRead);
    utterance.rate = 0.95; // Natural speaking pace
    utterance.pitch = 1.0;

    utterance.onend = function () {
        isSpeaking = false;
        btn.innerHTML = "🔊 Listen to Advice";
    };

    utterance.onerror = function () {
        isSpeaking = false;
        btn.innerHTML = "🔊 Listen to Advice";
    };

    window.speechSynthesis.speak(utterance);
    isSpeaking = true;
    btn.innerHTML = "⏹ Stop Listening";
}
