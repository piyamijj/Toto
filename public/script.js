document.getElementById('analizBtn').addEventListener('click', async () => {
    const week = document.getElementById('haftaInput').value;
    const tableBody = document.getElementById('matchTableBody');
    tableBody.innerHTML = `<tr><td colspan="8" class="p-6 text-center text-gray-400">Yapay zeka modeli hesaplıyor...</td></tr>`;

    try {
        const response = await fetch(`/api/analiz?hafta=${week}`);
        const data = await response.json();

        tableBody.innerHTML = '';
        data.maclar.forEach(m => {
            const row = `
                <tr class="hover:bg-gray-750 transition">
                    <td class="p-4 font-bold text-gray-400">${m.no}</td>
                    <td class="p-4 font-medium">${m.mac}</td>
                    <td class="p-4 text-blue-400">${m.xg}</td>
                    <td class="p-4 text-gray-300">${m.p1}</td>
                    <td class="p-4 text-gray-300">${m.px}</td>
                    <td class="p-4 text-gray-300">${m.p2}</td>
                    <td class="p-4 text-yellow-400 font-bold text-center bg-gray-800/50">${m.oneri}</td>
                    <td class="p-4 font-semibold text-sm ${m.strateji.includes('BANKO') ? 'text-green-400' : m.strateji.includes('ÇİFTE') ? 'text-orange-400' : 'text-red-400'}">${m.strateji}</td>
                </tr>
            `;
            tableBody.insertAdjacentHTML('beforeend', row);
        });

        document.getElementById('totalColumns').innerText = data.toplam_kolon;
    } catch (error) {
        tableBody.innerHTML = `<tr><td colspan="8" class="p-6 text-center text-red-500">Hata oluştu! Lütfen tekrar deneyin.</td></tr>`;
    }
});
