const COLUMNS = ['no', 'mac', 'xg', 'p1', 'px', 'p2', 'oneri', 'strateji'];

function strategyClass(s) {
  if (s.includes('BANKO')) return 'text-green-400';
  if (s.includes('ÇİFTE')) return 'text-orange-400';
  return 'text-red-400';
}

function messageRow(tbody, text, cls) {
  tbody.replaceChildren();
  const tr = document.createElement('tr');
  const td = document.createElement('td');
  td.colSpan = COLUMNS.length;
  td.className = `p-6 text-center ${cls}`;
  td.textContent = text;
  tr.appendChild(td);
  tbody.appendChild(tr);
}

document.getElementById('analizBtn').addEventListener('click', async () => {
  const btn = document.getElementById('analizBtn');
  const week = Number(document.getElementById('haftaInput').value);
  const tbody = document.getElementById('matchTableBody');

  if (!Number.isInteger(week) || week < 1 || week > 38) {
    messageRow(tbody, 'Hafta 1 ile 38 arasında olmalı.', 'text-red-500');
    return;
  }

  btn.disabled = true;
  messageRow(tbody, 'Model hesaplıyor...', 'text-gray-400');
  try {
    const res = await fetch(`/api/analiz?hafta=${encodeURIComponent(week)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(typeof err.detail === 'string' ? err.detail : `Sunucu hatası (${res.status})`);
    }
    const data = await res.json();
    tbody.replaceChildren();
    for (const m of data.maclar) {
      const tr = document.createElement('tr');
      tr.className = 'hover:bg-gray-700 transition';
      for (const key of COLUMNS) {
        const td = document.createElement('td');
        td.className = 'p-4';
        if (key === 'oneri') td.className += ' text-yellow-400 font-bold text-center';
        if (key === 'strateji') td.className += ` font-semibold text-sm ${strategyClass(m.strateji)}`;
        td.textContent = m[key];
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    document.getElementById('totalColumns').textContent = data.toplam_kolon;
    const meta = data.model || {};
    document.getElementById('sourceInfo').textContent =
      `Bülten: ${data.veri_kaynagi} · Model: ${meta.n_matches ?? '?'} maçla eğitildi (${meta.ref_date ?? '-'})`;
  } catch (e) {
    messageRow(tbody, `Hata: ${e.message}`, 'text-red-500');
  } finally {
    btn.disabled = false;
  }
});
