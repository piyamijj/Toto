# Toto – Spor Toto Hibrit Entropi Analizörü

Spor Toto bültenindeki maçlar için **gerçek tarihsel veriyle eğitilmiş Dixon-Coles** skor modelini, bahis piyasası olasılıklarıyla (Shin yöntemiyle marjı temizlenmiş) birleştiren ve entropiye göre kupon stratejisi öneren web uygulaması.

> **18+ · Sorumlu oyun:** Bu proje yalnızca istatistiksel bilgi amaçlıdır. Tahminler garanti değildir; bahis veya yatırım tavsiyesi değildir. Resmi bülten ve sonuçlar için [sportoto.gov.tr](https://www.sportoto.gov.tr) esas alınmalıdır.

## Nasıl çalışır?
1. **Model:** Süper Lig maç sonuçlarından (son 4 sezon, zaman ağırlıklı) her takım için hücum (α) ve savunma (β) gücü, ev sahibi avantajı (γ) ve Dixon-Coles düşük skor düzeltmesi (ρ) maksimum olabilirlikle kestirilir.
2. **Piyasa:** 1/X/2 oranlarından Shin yöntemiyle marj temizlenir.
3. **Hibrit:** Sezon ilerledikçe model ağırlığı %30 → %85. Oran yoksa yalnız model kullanılır.
4. **Strateji:** Entropi < 1.25 veya en yüksek olasılık > %58 → **BANKO**; ≤ 1.48 → **ÇİFTE ŞANS**; aksi halde **KAPAT (1X2)**.

## Veri kaynakları
| Veri | Kaynak | Anahtar | Maliyet (yaklaşık, sitede doğrulayın) |
|---|---|---|---|
| Spor Toto bülteni | **Resmi API yok.** sportoto.gov.tr'deki bülten haftalık olarak `data/bulten.json`'a girilir (örnek: `data/bulten.example.json`). Site kazınmaz. | – | Ücretsiz |
| Süper Lig fikstürü (bülten dosyası yoksa) | [API-Football](https://www.api-football.com) (api-sports.io, lisanslı) | `API_FOOTBALL_KEY` | Ücretsiz plan 100 istek/gün; ücretli planlar aylık ~19$'dan |
| 1X2 oranları | [The Odds API](https://the-odds-api.com) (lisanslı) | `ODDS_API_KEY` | Starter ücretsiz 500 kredi/ay; 20K kredi planı ücretli |
| Eğitim verisi (geçmiş sonuçlar) | [football-data.co.uk](https://www.football-data.co.uk/turkeym.php) sezon CSV'leri | – | Ücretsiz |

Anahtarlar **yalnızca ortam değişkeninden** okunur; `.env.example` dosyasını kopyalayın, Vercel'de *Project Settings → Environment Variables* altına girin. `.env` git'e eklenmez.

## Yapı
```
api/index.py            FastAPI uygulaması (Vercel serverless)
toto/model.py           Dixon-Coles, Shin, hibrit model, eğitim
toto/strategy.py        Kupon stratejisi
toto/data/              Bülten, fikstür, oran ve tarihsel veri kaynakları
toto/teams.py           Kaynaklar arası takım adı eşleştirme
scripts/train.py        Model eğitimi → data/model_params.json
public/                 Arayüz
tests/                  pytest
ci-workflows/           GitHub Actions dosyaları (aşağıya bakın)
```

## Kurulum ve eğitim
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # anahtarları girin
python scripts/train.py         # data/model_params.json üretir (commit edin)
uvicorn api.index:app --reload  # http://localhost:8000
pytest -q && ruff check .
```
Model eğitilmeden `/api/analiz` 503 döner.

## API
| Uç nokta | Açıklama |
|---|---|
| `GET /api/health` | Sağlık, model ve veri kaynağı durumu |
| `GET /api/analiz?hafta=1..38` | Bülten analizi |

## CI (GitHub Actions)
`ci-workflows/` içindeki dosyalar (`ci.yml` test, `train.yml` eğitim) GitHub bağlantısının `workflows` yetkisi olmadığı için otomatik eklenemedi. Etkinleştirmek için:
```bash
mkdir -p .github/workflows && git mv ci-workflows/*.yml .github/workflows/
```

## Lisans
Henüz lisans belirlenmedi (tüm hakları saklıdır). Veri sağlayıcıların kullanım koşulları geçerlidir.
