# Toto – Spor Toto Hibrit Entropi Analizörü

Spor Toto bültenindeki maçlar için **Dixon-Coles** skor modeli ile bahis piyasası olasılıklarını (Shin yöntemiyle marjı temizlenmiş) birleştiren ve entropiye göre kupon stratejisi öneren web uygulaması.

> **18+ · Sorumlu oyun:** Bu proje yalnızca istatistiksel bilgi amaçlıdır. Tahminler garanti değildir; bahis veya yatırım tavsiyesi değildir. Resmi bülten ve sonuçlar için [sportoto.gov.tr](https://www.sportoto.gov.tr) esas alınmalıdır.

## Nasıl çalışır?
1. **Model olasılığı:** Takım hücum/savunma güçlerinden beklenen goller (xG) ve Dixon-Coles düzeltmeli Poisson skor matrisi.
2. **Piyasa olasılığı:** 1/X/2 oranlarından Shin yöntemiyle marj temizleme.
3. **Hibrit:** Sezon ilerledikçe model ağırlığı %30 → %85'e çıkar.
4. **Strateji:** Entropi < 1.25 veya en yüksek olasılık > %58 → **BANKO**; ≤ 1.48 → **ÇİFTE ŞANS**; aksi halde **KAPAT (1X2)**.

## Yapı
```
api/index.py      FastAPI uygulaması (Vercel serverless)
public/           Statik arayüz
tests/            pytest testleri
```

## Yerel çalıştırma
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn api.index:app --reload   # http://localhost:8000/api/analiz?hafta=5
pytest -q && ruff check .
```

## API
| Uç nokta | Açıklama |
|---|---|
| `GET /api/health` | Sağlık kontrolü |
| `GET /api/analiz?hafta=1..38` | Bülten analizi |

## Dağıtım
Vercel'e bağlayın; `vercel.json` `/api/*` isteklerini Python fonksiyonuna, diğerlerini `public/`'e yönlendirir.

## Lisans
Henüz lisans belirlenmedi (tüm hakları saklıdır).

## CI (GitHub Actions)
İş akışı dosyaları `ci-workflows/` klasöründedir. Bağlı uygulamanın `workflows` yetkisi olmadığı için otomatik eklenemedi; etkinleştirmek için:
```bash
mkdir -p .github/workflows && git mv ci-workflows/*.yml .github/workflows/
```
